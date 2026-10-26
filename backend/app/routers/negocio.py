"""Datos del negocio para la Politica de Tratamiento de Datos, solo Administrador (HU-07).

El administrador los edita en la aplicacion ("Datos personales > Datos del negocio"); con ellos el
backend arma el aviso de privacidad y la politica que ven el POS y el formulario publico de autorregistro.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.configuracion_negocio import ConfiguracionNegocio
from app.models.usuario import RolUsuario, Usuario
from app.schemas.proveedor import _validar_email
from app.services.politica_datos import DatosNegocio, cargar_datos_negocio, datos_completos, faltantes, version_vigente

router = APIRouter(
    prefix="/negocio",
    tags=["negocio"],
    dependencies=[Depends(requerir_roles(RolUsuario.ADMINISTRADOR))],
)


class NegocioIn(BaseModel):
    """Datos del negocio que se guardan (`PUT /negocio`). Un texto vacio deja el dato sin completar.

    Attributes:
        nombre: Nombre o razon social.
        documento: NIT o cedula.
        direccion: Direccion y ciudad.
        telefono: Telefono de la tienda.
        correo_datos: Correo para consultas y reclamos de datos personales.
        responsable_datos: Persona que atiende las solicitudes (opcional).
        politica_version: Version del texto de la politica.
        politica_fecha: Fecha desde la que rige (texto, ej. "12-10-2026").
    """

    nombre: str = Field(default="", max_length=150)
    documento: str = Field(default="", max_length=40)
    direccion: str = Field(default="", max_length=200)
    telefono: str = Field(default="", max_length=40)
    correo_datos: str = Field(default="", max_length=120)
    responsable_datos: str = Field(default="", max_length=150)
    politica_version: str = Field(default="1.0", max_length=20)
    politica_fecha: str = Field(default="", max_length=40)

    @field_validator("*", mode="before")
    @classmethod
    def _recortar(cls, valor):
        """Recorta espacios de todos los textos."""
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("correo_datos")
    @classmethod
    def _correo_valido(cls, valor: str) -> str:
        """Un correo vacio es valido (dato sin completar); si hay uno, debe tener formato de correo."""
        return _validar_email(valor) if valor else ""


class NegocioOut(BaseModel):
    """Datos del negocio guardados y su estado.

    Attributes:
        nombre: Nombre o razon social.
        documento: NIT o cedula.
        direccion: Direccion y ciudad.
        telefono: Telefono de la tienda.
        correo_datos: Correo para solicitudes de datos.
        responsable_datos: Persona que atiende las solicitudes.
        politica_version: Version configurada del texto.
        politica_fecha: Fecha desde la que rige.
        version_vigente: Version que se guarda como evidencia ("borrador" si faltan datos).
        datos_completos: Si estan los datos que exige la politica.
        faltantes: Datos sin completar.
        actualizado_en: Ultimo cambio, o None si nunca se guardaron.
    """

    model_config = ConfigDict(from_attributes=True)

    nombre: str
    documento: str
    direccion: str
    telefono: str
    correo_datos: str
    responsable_datos: str
    politica_version: str
    politica_fecha: str
    version_vigente: str
    datos_completos: bool
    faltantes: list[str]
    actualizado_en: datetime | None


def _a_salida(db: Session, datos: DatosNegocio) -> NegocioOut:
    """Arma la respuesta con los datos guardados y su estado."""
    fila = db.get(ConfiguracionNegocio, 1)
    return NegocioOut(
        nombre=datos.nombre,
        documento=datos.documento,
        direccion=datos.direccion,
        telefono=datos.telefono,
        correo_datos=datos.correo_datos,
        responsable_datos=datos.responsable_datos,
        politica_version=datos.politica_version,
        politica_fecha=datos.politica_fecha,
        version_vigente=version_vigente(datos),
        datos_completos=datos_completos(datos),
        faltantes=faltantes(datos),
        actualizado_en=fila.actualizado_en if fila else None,
    )


@router.get("", response_model=NegocioOut)
def consultar_negocio(db: Session = Depends(get_db)) -> NegocioOut:
    """Devuelve los datos del negocio guardados y lo que falta para publicar la politica.

    Args:
        db: Sesion de base de datos inyectada.

    Returns:
        NegocioOut: Datos y estado.
    """
    return _a_salida(db, cargar_datos_negocio(db))


@router.put("", response_model=NegocioOut)
def guardar_negocio(
    payload: NegocioIn,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> NegocioOut:
    """Guarda los datos del negocio (reemplaza los anteriores).

    Desde ese momento el aviso y la politica que ven el POS y el autorregistro usan estos datos, y las
    autorizaciones nuevas quedan con la version configurada (o "borrador" si aun falta algun dato).

    Args:
        payload: Datos del negocio.
        db: Sesion de base de datos inyectada.
        administrador: Administrador que los guarda.

    Returns:
        NegocioOut: Datos y estado actualizados.
    """
    fila = db.get(ConfiguracionNegocio, 1)
    if fila is None:
        fila = ConfiguracionNegocio(id=1)
        db.add(fila)
    for campo, valor in payload.model_dump().items():
        setattr(fila, campo, valor or ("1.0" if campo == "politica_version" else ""))
    fila.actualizado_por = administrador.id
    db.commit()
    return _a_salida(db, cargar_datos_negocio(db))
