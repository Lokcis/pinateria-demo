"""Texto vigente de la Politica de Tratamiento de Datos Personales y del aviso de privacidad (Ley 1581 de 2012).

Es la unica fuente de esos textos: el POS (alta de clientes) y la pagina publica de autorregistro los
piden al backend, asi lo que el cliente lee es siempre lo que quedo registrado como version vigente.
Los datos del negocio (responsable, NIT, canal de solicitudes) los edita el administrador en la aplicacion
y se guardan en `configuracion_negocio`; no estan en el codigo. El texto es el aprobado por el propietario
el 12-10-2026 (docs/08).
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.configuracion_negocio import ConfiguracionNegocio

VERSION_BORRADOR = "borrador"
PENDIENTE = "[pendiente]"


@dataclass(frozen=True)
class DatosNegocio:
    """Datos del responsable del tratamiento, tal como los guardo el administrador.

    Attributes:
        nombre: Nombre o razon social.
        documento: NIT o cedula.
        direccion: Direccion y ciudad.
        telefono: Telefono de la tienda.
        correo_datos: Correo para consultas y reclamos.
        responsable_datos: Persona que atiende las solicitudes (opcional).
        politica_version: Version del texto de la politica.
        politica_fecha: Fecha desde la que rige.
    """

    nombre: str = ""
    documento: str = ""
    direccion: str = ""
    telefono: str = ""
    correo_datos: str = ""
    responsable_datos: str = ""
    politica_version: str = "1.0"
    politica_fecha: str = ""


def cargar_datos_negocio(db: Session) -> DatosNegocio:
    """Lee los datos del negocio guardados; sin fila (nunca se guardaron), todo queda sin completar.

    Args:
        db: Sesion de base de datos.

    Returns:
        DatosNegocio: Los datos vigentes.
    """
    fila = db.get(ConfiguracionNegocio, 1)
    if fila is None:
        return DatosNegocio()
    return DatosNegocio(
        nombre=fila.nombre,
        documento=fila.documento,
        direccion=fila.direccion,
        telefono=fila.telefono,
        correo_datos=fila.correo_datos,
        responsable_datos=fila.responsable_datos,
        politica_version=fila.politica_version,
        politica_fecha=fila.politica_fecha,
    )


def faltantes(datos: DatosNegocio) -> list[str]:
    """Lista los datos del negocio que faltan para que la politica sea valida.

    Args:
        datos: Datos del negocio.

    Returns:
        list[str]: Nombres (legibles) de los datos sin completar.
    """
    requeridos = {
        "Nombre del negocio": datos.nombre,
        "NIT o cédula": datos.documento,
        "Dirección": datos.direccion,
        "Teléfono": datos.telefono,
        "Correo para solicitudes de datos": datos.correo_datos,
        "Fecha desde la que rige la política": datos.politica_fecha,
    }
    return [nombre for nombre, valor in requeridos.items() if not valor.strip()]


def datos_completos(datos: DatosNegocio) -> bool:
    """Indica si estan todos los datos del negocio que exige la politica."""
    return not faltantes(datos)


def version_vigente(datos: DatosNegocio) -> str:
    """Version de la politica que se guarda como evidencia en cada autorizacion.

    Si faltan datos del negocio, el texto que se mostro tenia huecos: la evidencia queda
    como "borrador" y no como una version oficial.

    Args:
        datos: Datos del negocio.

    Returns:
        str: La version configurada cuando los datos estan completos; si no, "borrador".
    """
    return (datos.politica_version.strip() or "1.0") if datos_completos(datos) else VERSION_BORRADOR


def _dato(valor: str) -> str:
    """Valor de configuracion listo para insertar en un texto; marca lo que falta."""
    return valor.strip() or PENDIENTE


def construir_politica(datos: DatosNegocio) -> dict[str, Any]:
    """Arma el aviso de privacidad, las casillas de autorizacion y la politica completa.

    Args:
        datos: Datos del negocio que se insertan en los textos.

    Returns:
        dict: `version`, `datos_completos`, `faltantes`, `aviso` (texto corto), `texto_autorizacion`
        (casilla obligatoria), `texto_promociones` (casilla aparte, opcional) y `secciones`
        (lista de `{titulo, parrafos, items}` de la politica completa).
    """
    nombre = _dato(datos.nombre)
    documento = _dato(datos.documento)
    direccion = _dato(datos.direccion)
    telefono = _dato(datos.telefono)
    correo = _dato(datos.correo_datos)
    responsable = datos.responsable_datos.strip() or nombre
    fecha = _dato(datos.politica_fecha)

    aviso = (
        f"{nombre} (NIT/cédula {documento}) usará tus datos (nombre y, si los das, documento, teléfono y correo) "
        "solo para identificarte, asociar tus compras, aplicarte descuentos y consultar tu historial. "
        "No los vendemos ni los compartimos con terceros para publicidad. Los datos opcionales no son "
        "necesarios para comprar. Puedes conocer, actualizar, rectificar o suprimir tus datos, o revocar "
        f"tu autorización, escribiendo a {correo} o preguntando en la tienda. Puedes consultar la Política de "
        "Tratamiento de Datos completa más abajo o en la tienda."
    )

    secciones: list[dict[str, Any]] = [
        {
            "titulo": "1. Responsable del tratamiento",
            "parrafos": [
                f"{nombre}, identificado con {documento}, con domicilio en {direccion}, teléfono {telefono} "
                f"y correo {correo} (en adelante, \"la Tienda\"). Persona que atiende las solicitudes: {responsable}.",
            ],
            "items": [],
        },
        {
            "titulo": "2. Alcance y marco legal",
            "parrafos": [
                "Esta política aplica a los datos personales de los clientes que la Tienda registra en su sistema "
                "de ventas. Se expide en cumplimiento del artículo 15 de la Constitución Política, la Ley 1581 de "
                "2012 y el Decreto 1074 de 2015 (que compila el Decreto 1377 de 2013).",
            ],
            "items": [],
        },
        {
            "titulo": "3. Datos que se recolectan",
            "parrafos": [
                "La Tienda no recolecta datos sensibles (salud, origen étnico, orientación política o sexual, datos "
                "biométricos, entre otros) y no registra datos de menores de edad. Los datos marcados como "
                "opcionales no son necesarios para comprar: el cliente puede comprar sin registrarse.",
            ],
            "items": [
                "Nombre.",
                "Documento de identidad (opcional).",
                "Teléfono (opcional).",
                "Correo electrónico (opcional).",
                "El historial de compras que la Tienda registra al venderle (productos, fechas, valores y formas de pago).",
            ],
        },
        {
            "titulo": "4. Finalidades",
            "parrafos": [
                "Los datos se usan únicamente para:",
            ],
            "items": [
                "Identificar al cliente y asociarle sus compras.",
                "Aplicarle el descuento o beneficio que le corresponda como cliente registrado.",
                "Consultar su historial de compras para atenderlo mejor.",
                "Atender sus consultas, reclamos y solicitudes sobre sus datos.",
                "Cumplir obligaciones legales, contables y tributarias de la Tienda.",
                "Solo si el cliente lo autoriza marcando la casilla aparte: enviarle promociones y novedades de la "
                "Tienda. Puede retirar esta autorización en cualquier momento, sin que afecte sus compras ni sus descuentos.",
            ],
        },
        {
            "titulo": "5. Lo que la Tienda no hace",
            "parrafos": [
                "La Tienda no vende, alquila ni comparte los datos con terceros para fines comerciales, y no los usa "
                "para enviar publicidad si el cliente no dio la autorización aparte para promociones.",
            ],
            "items": [],
        },
        {
            "titulo": "6. Autorización",
            "parrafos": [
                "El tratamiento requiere la autorización previa, expresa e informada del titular. La Tienda la solicita "
                "al registrar al cliente, por escrito, de forma verbal o electrónica, y conserva la prueba: fecha, "
                "medio por el que se dio, versión de esta política que se le informó y empleado que la recogió. "
                "No se registra a nadie que no la dé.",
            ],
            "items": [],
        },
        {
            "titulo": "7. Derechos del titular",
            "parrafos": ["El titular de los datos tiene derecho a:"],
            "items": [
                "Conocer, actualizar y rectificar sus datos.",
                "Pedir prueba de la autorización que dio.",
                "Ser informado, si lo solicita, del uso que se ha dado a sus datos.",
                "Presentar quejas ante la Superintendencia de Industria y Comercio (SIC) por infracciones a la ley, "
                "una vez agotado el trámite de consulta o reclamo ante la Tienda.",
                "Revocar la autorización y pedir la supresión de sus datos, siempre que no exista un deber legal o "
                "contractual de conservarlos.",
                "Acceder de forma gratuita a sus datos personales.",
            ],
        },
        {
            "titulo": "8. Cómo ejercer los derechos",
            "parrafos": [
                f"Mediante solicitud dirigida a {responsable}, por correo a {correo}, por teléfono ({telefono}) o en la "
                f"tienda ({direccion}). La Tienda responde:",
            ],
            "items": [
                "Consultas: en máximo 10 días hábiles desde el recibo. Si no es posible, se informa el motivo y la "
                "nueva fecha, que no puede pasar de 5 días hábiles más.",
                "Reclamos (actualizar, rectificar, suprimir o revocar): en máximo 15 días hábiles desde el recibo. "
                "Si no es posible, se informa el motivo y la nueva fecha, que no puede pasar de 8 días hábiles más.",
            ],
        },
        {
            "titulo": "9. Supresión de datos",
            "parrafos": [
                "Cuando el titular pide la supresión, la Tienda reemplaza su nombre por \"Cliente anonimizado\" y borra "
                "su documento, teléfono, correo y descuento. Las ventas ya hechas se conservan como registro contable, "
                "pero sin ningún dato que identifique a la persona. La supresión puede negarse, con explicación, si la "
                "ley obliga a conservar la información.",
            ],
            "items": [],
        },
        {
            "titulo": "10. Conservación",
            "parrafos": [
                "Los datos se conservan mientras el cliente siga registrado y el tiempo adicional que exijan las normas "
                "contables y tributarias. Pasado ese tiempo, o cuando el titular lo pida y proceda, se suprimen o "
                "anonimizan. Las copias de seguridad del sistema se conservan 14 días y se sobrescriben solas.",
            ],
            "items": [],
        },
        {
            "titulo": "11. Seguridad",
            "parrafos": [
                "El sistema exige usuario y contraseña, separa lo que puede ver cada rol (el vendedor registra y consulta "
                "clientes; solo el administrador atiende solicitudes y asigna descuentos), cifra las contraseñas, "
                "transmite la información por conexión segura (HTTPS) y guarda copias de seguridad en una carpeta "
                "restringida. El personal que accede a los datos está obligado a mantenerlos confidenciales.",
            ],
            "items": [],
        },
        {
            "titulo": "12. Encargados y terceros",
            "parrafos": [
                "La Tienda usa servicios tecnológicos para operar el sistema: un servidor propio, la persona que lo "
                "administra y el servicio de red de Cloudflare, que lleva el tráfico entre el navegador y el servidor y "
                "tiene infraestructura fuera de Colombia. Estos terceros actúan como encargados del tratamiento: solo "
                "procesan los datos siguiendo las instrucciones de la Tienda y bajo deber de confidencialidad. Fuera de "
                "ellos, los datos solo se entregan a autoridades que los pidan con base legal.",
            ],
            "items": [],
        },
        {
            "titulo": "13. Vigencia y cambios",
            "parrafos": [
                f"Esta política (versión {version_vigente(datos)}) rige desde {fecha}. Si cambia de forma sustancial —por "
                "ejemplo, una nueva finalidad— la Tienda lo informará a los titulares antes de aplicarla y pedirá una "
                "nueva autorización cuando la ley lo exija. Cada versión queda identificada y el sistema guarda con "
                "cada cliente la versión que aceptó.",
            ],
            "items": [],
        },
    ]

    return {
        "version": version_vigente(datos),
        "datos_completos": datos_completos(datos),
        "faltantes": faltantes(datos),
        "aviso": aviso,
        "texto_autorizacion": "He leído este aviso y autorizo el tratamiento de mis datos personales conforme a la Política de Tratamiento de Datos.",
        "texto_promociones": "Además, autorizo que me envíen promociones y novedades de la tienda (opcional; puedo retirar esta autorización cuando quiera).",
        "texto_autorizacion_empleado": "El cliente leyó o escuchó este aviso y autoriza el tratamiento de sus datos personales.",
        "texto_promociones_empleado": "El cliente además autoriza que le envíen promociones y novedades de la tienda (opcional).",
        "secciones": secciones,
    }
