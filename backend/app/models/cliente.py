"""Modelos de clientes y Habeas Data (Adendo v2, Fase A2).

Contienen datos personales y se disenaron para cumplir la Ley 1581 de 2012:
no se crea un cliente sin la evidencia de su autorizacion, la revocatoria
bloquea su uso en ventas nuevas y la supresion anonimiza el registro sin
perder las ventas (docs/03-diseno-base-de-datos.md, secciones 7.5 a 7.8).
"""

import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.descuento import _enum_tipo_descuento


class MedioAutorizacion(str, enum.Enum):
    """Medio por el que el titular autorizo el tratamiento de sus datos.

    Attributes:
        ESCRITO: Firma en papel.
        ELECTRONICO: Aceptacion en pantalla o por el enlace de autorregistro.
        VERBAL: Autorizacion de palabra, recogida por un empleado.
    """

    ESCRITO = "escrito"
    ELECTRONICO = "electronico"
    VERBAL = "verbal"


class OrigenRegistro(str, enum.Enum):
    """Quien registro al cliente.

    Attributes:
        EMPLEADO: Un empleado desde el sistema.
        AUTOREGISTRO: El propio cliente desde el enlace publico.
    """

    EMPLEADO = "empleado"
    AUTOREGISTRO = "autoregistro"


class TipoSolicitudTitular(str, enum.Enum):
    """Tipo de solicitud de un titular de datos.

    Attributes:
        CONSULTA: Conocer los datos que se tienen (plazo de consulta).
        ACTUALIZACION: Actualizar o rectificar datos (reclamo).
        SUPRESION: Suprimir los datos (reclamo).
        REVOCATORIA: Revocar la autorizacion (reclamo).
    """

    CONSULTA = "consulta"
    ACTUALIZACION = "actualizacion"
    SUPRESION = "supresion"
    REVOCATORIA = "revocatoria"


class EstadoSolicitudTitular(str, enum.Enum):
    """Estado de una solicitud de titular.

    Attributes:
        RECIBIDA: Registrada, sin atender.
        EN_TRAMITE: En proceso.
        RESUELTA: Atendida y respondida.
        RECHAZADA: Negada con una respuesta motivada.
    """

    RECIBIDA = "recibida"
    EN_TRAMITE = "en_tramite"
    RESUELTA = "resuelta"
    RECHAZADA = "rechazada"


def _valores(enum_cls: type[enum.Enum]) -> list[str]:
    """Valores de un Enum de Python, para que SQLAlchemy use los textos y no los nombres."""
    return [m.value for m in enum_cls]


class Cliente(Base):
    """Cliente de la tienda, con la evidencia de su autorizacion de datos (RF-025, RF-029 a RF-035).

    Attributes:
        id: Identificador unico autoincremental.
        nombre: Nombre del cliente.
        documento: Documento de identidad, unico cuando existe.
        telefono: Solo digitos (7 a 15).
        email: Correo electronico.
        descuento_tipo: Tipo del descuento propio (lo asigna el administrador).
        descuento_valor: Valor del descuento propio.
        activo: Baja logica: un cliente con ventas nunca se borra.
        acepta_publicidad: Autorizacion APARTE para recibir promociones (casilla
            separada, desmarcada por defecto). Sin ella no se le ofrece nada.
        publicidad_fecha: Cuando se dio o se retiro esa autorizacion por ultima vez.
        autorizacion_fecha: Cuando autorizo el tratamiento de sus datos.
        autorizacion_medio: escrito / electronico / verbal.
        autorizacion_version: Version de la politica de datos que acepto.
        origen_registro: empleado / autoregistro.
        autorizacion_registrada_por: Empleado que recogio la autorizacion
            (obligatorio si el origen es `empleado`, vacio si es autorregistro).
        autorizacion_revocada_en: Cuando revoco la autorizacion, si lo hizo.
        anonimizado_en: Cuando se atendio una supresion.
        creado_en: Fecha de creacion.
        actualizado_en: Fecha de la ultima modificacion.
    """

    __tablename__ = "clientes"
    __table_args__ = (
        CheckConstraint(
            "(origen_registro = 'empleado') = (autorizacion_registrada_por IS NOT NULL)",
            name="ck_cliente_registrador",
        ),
        CheckConstraint("(descuento_tipo IS NULL) = (descuento_valor IS NULL)", name="ck_cliente_descuento_completo"),
        CheckConstraint(
            "descuento_valor IS NULL OR (descuento_valor > 0 "
            "AND (descuento_tipo <> 'porcentaje' OR descuento_valor <= 100))",
            name="ck_cliente_descuento_valor",
        ),
        Index("ux_clientes_documento", "documento", unique=True, postgresql_where=text("documento IS NOT NULL")),
        Index("ix_clientes_telefono", "telefono"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    documento = Column(String(30), nullable=True)
    telefono = Column(String(15), nullable=True)
    email = Column(String(120), nullable=True)
    descuento_tipo = Column(_enum_tipo_descuento(), nullable=True)
    descuento_valor = Column(Numeric(10, 2), nullable=True)
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    acepta_publicidad = Column(Boolean, nullable=False, default=False, server_default="false")
    publicidad_fecha = Column(DateTime(timezone=True), nullable=True)
    autorizacion_fecha = Column(DateTime(timezone=True), nullable=False)
    autorizacion_medio = Column(
        Enum(MedioAutorizacion, name="medio_autorizacion", values_callable=_valores), nullable=False
    )
    autorizacion_version = Column(String(20), nullable=False)
    origen_registro = Column(
        Enum(OrigenRegistro, name="origen_registro", values_callable=_valores),
        nullable=False,
        default=OrigenRegistro.EMPLEADO,
        server_default=OrigenRegistro.EMPLEADO.value,
    )
    autorizacion_registrada_por = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    autorizacion_revocada_en = Column(DateTime(timezone=True), nullable=True)
    anonimizado_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    ventas = relationship("Venta", back_populates="cliente")
    solicitudes = relationship("SolicitudTitular", back_populates="cliente")
    registrada_por = relationship("Usuario", foreign_keys=[autorizacion_registrada_por])

    @property
    def utilizable(self) -> bool:
        """Indica si el cliente puede asociarse a una venta nueva.

        Un cliente desactivado, con la autorizacion revocada o anonimizado
        no puede usarse (RF-031, RF-035).
        """
        return bool(self.activo) and self.autorizacion_revocada_en is None and self.anonimizado_en is None

    def __repr__(self) -> str:
        """Retorna una representacion legible del cliente (sin datos personales) para logs/debug."""
        return f"<Cliente id={self.id} activo={self.activo}>"


class EnlaceAutoregistro(Base):
    """Enlace publico de autorregistro; una sola fila (id = 1) (RF-046, RF-048).

    La tabla existe desde la migracion 0005, pero el formulario publico se
    construye cuando este lista la politica de tratamiento de datos.

    Attributes:
        id: Siempre 1.
        token: Codigo aleatorio del enlace; al regenerarlo, el anterior deja de servir.
        activo: Si esta apagado, el formulario responde que no esta disponible.
        actualizado_por: Administrador que lo genero o modifico por ultima vez.
        actualizado_en: Fecha del ultimo cambio.
    """

    __tablename__ = "enlace_autoregistro"
    __table_args__ = (CheckConstraint("id = 1", name="enlace_autoregistro_id_check"),)

    id = Column(SmallInteger, primary_key=True, default=1, server_default="1")
    token = Column(String(64), nullable=False, unique=True)
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    actualizado_por = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SolicitudTitular(Base):
    """Consulta o reclamo de un titular de datos (RF-035).

    Attributes:
        id: Identificador unico autoincremental.
        cliente_id: Titular que presenta la solicitud.
        tipo: consulta / actualizacion / supresion / revocatoria.
        descripcion: Detalle de lo solicitado.
        estado: recibida / en_tramite / resuelta / rechazada.
        recibida_en: Fecha de recepcion.
        fecha_limite: Fecha maxima de respuesta segun el plazo legal.
        resuelta_en: Fecha de la respuesta.
        atendida_por: Administrador que respondio.
        respuesta: Resumen de la respuesta dada al titular.
    """

    __tablename__ = "solicitudes_titular"
    __table_args__ = (
        Index("ix_solicitudes_cliente", "cliente_id"),
        Index("ix_solicitudes_estado", "estado"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    tipo = Column(Enum(TipoSolicitudTitular, name="tipo_solicitud_titular", values_callable=_valores), nullable=False)
    descripcion = Column(String(500), nullable=True)
    estado = Column(
        Enum(EstadoSolicitudTitular, name="estado_solicitud_titular", values_callable=_valores),
        nullable=False,
        default=EstadoSolicitudTitular.RECIBIDA,
        server_default=EstadoSolicitudTitular.RECIBIDA.value,
    )
    recibida_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    fecha_limite = Column(Date, nullable=False)
    resuelta_en = Column(DateTime(timezone=True), nullable=True)
    atendida_por = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    respuesta = Column(String(500), nullable=True)

    cliente = relationship("Cliente", back_populates="solicitudes")
    atendida_por_usuario = relationship("Usuario", foreign_keys=[atendida_por])

    def __repr__(self) -> str:
        """Retorna una representacion legible de la solicitud para logs/debug."""
        return f"<SolicitudTitular id={self.id} tipo={self.tipo} estado={self.estado}>"
