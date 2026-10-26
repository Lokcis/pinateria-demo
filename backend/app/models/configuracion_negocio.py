"""Datos del negocio que van en la Politica de Tratamiento de Datos (Adendo v2, Fase A2; HU-07).

Antes vivian en variables del `.env`; ahora el administrador los edita desde la aplicacion
("Datos personales > Datos del negocio"), sin tocar el servidor.
"""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, SmallInteger, String, func

from app.core.database import Base


class ConfiguracionNegocio(Base):
    """Datos del responsable del tratamiento; una sola fila (id = 1).

    Todos los textos son opcionales en la base de datos (vacio = sin completar); la politica exige
    que esten completos los seis primeros para considerarse valida (ver `services/politica_datos.py`).

    Attributes:
        id: Siempre 1.
        nombre: Nombre o razon social del responsable.
        documento: NIT o cedula del responsable.
        direccion: Direccion y ciudad de la tienda.
        telefono: Telefono de la tienda.
        correo_datos: Correo al que los titulares envian sus consultas y reclamos.
        responsable_datos: Persona que atiende las solicitudes (opcional; por defecto, el negocio).
        politica_version: Version del texto de la politica (por defecto "1.0").
        politica_fecha: Fecha desde la que rige la politica (texto, ej. "12-10-2026").
        actualizado_por: Administrador que lo modifico por ultima vez.
        actualizado_en: Fecha de la ultima modificacion.
    """

    __tablename__ = "configuracion_negocio"
    __table_args__ = (CheckConstraint("id = 1", name="configuracion_negocio_id_check"),)

    id = Column(SmallInteger, primary_key=True, default=1, server_default="1")
    nombre = Column(String(150), nullable=False, default="", server_default="")
    documento = Column(String(40), nullable=False, default="", server_default="")
    direccion = Column(String(200), nullable=False, default="", server_default="")
    telefono = Column(String(40), nullable=False, default="", server_default="")
    correo_datos = Column(String(120), nullable=False, default="", server_default="")
    responsable_datos = Column(String(150), nullable=False, default="", server_default="")
    politica_version = Column(String(20), nullable=False, default="1.0", server_default="1.0")
    politica_fecha = Column(String(40), nullable=False, default="", server_default="")
    actualizado_por = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
