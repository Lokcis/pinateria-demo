"""Reglas de Habeas Data: plazos de las solicitudes y anonimizacion (Ley 1581 de 2012; RF-035).

Plazos legales (HU-07): las consultas se responden en 10 dias habiles y los
reclamos (actualizacion, supresion y revocatoria) en 15 dias habiles. La ley
permite prorrogarlos (5 y 8 dias habiles); la fecha limite que se guarda es
la del plazo base, que es la mas estricta.
"""

from datetime import date, datetime, timedelta

from app.models.cliente import Cliente, TipoSolicitudTitular

DIAS_HABILES_CONSULTA = 10
DIAS_HABILES_RECLAMO = 15

NOMBRE_ANONIMIZADO = "Cliente anonimizado"


def sumar_dias_habiles(inicio: date, dias: int) -> date:
    """Suma `dias` dias habiles (lunes a viernes) a una fecha.

    No descuenta los festivos: la fecha resultante nunca es posterior a la
    legal, asi que el sistema avisa siempre a tiempo o antes.

    Args:
        inicio: Fecha de partida (no cuenta como dia del plazo).
        dias: Numero de dias habiles a sumar.

    Returns:
        date: La fecha del ultimo dia del plazo.
    """
    fecha = inicio
    restantes = dias
    while restantes > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            restantes -= 1
    return fecha


def fecha_limite_solicitud(tipo: TipoSolicitudTitular, recibida: date) -> date:
    """Calcula la fecha maxima de respuesta segun el tipo de solicitud.

    Args:
        tipo: Tipo de solicitud del titular.
        recibida: Dia en que se recibio.

    Returns:
        date: 10 dias habiles para consultas; 15 para los demas reclamos.
    """
    dias = DIAS_HABILES_CONSULTA if tipo == TipoSolicitudTitular.CONSULTA else DIAS_HABILES_RECLAMO
    return sumar_dias_habiles(recibida, dias)


def revocar_autorizacion(cliente: Cliente, ahora: datetime) -> None:
    """Marca revocada la autorizacion del cliente (queda sin uso en ventas nuevas ni en promociones).

    Args:
        cliente: Cliente que revoca.
        ahora: Momento de la revocatoria.
    """
    if cliente.autorizacion_revocada_en is None:
        cliente.autorizacion_revocada_en = ahora
    if cliente.acepta_publicidad:
        cliente.acepta_publicidad = False
        cliente.publicidad_fecha = ahora


def anonimizar_cliente(cliente: Cliente, ahora: datetime) -> None:
    """Atiende una supresion: borra los datos personales y conserva las ventas.

    Reemplaza el nombre, pone en NULL documento, telefono, correo y descuento
    propio, desactiva al cliente y registra la fecha. La supresion implica
    tambien la revocatoria de la autorizacion. Borra ademas la descripcion libre
    de todas sus solicitudes, que podria contener datos personales (decision del
    13-10-2026); el tipo, las fechas y la respuesta de cada solicitud se conservan.

    Args:
        cliente: Cliente a anonimizar.
        ahora: Momento de la supresion.
    """
    cliente.nombre = NOMBRE_ANONIMIZADO
    cliente.documento = None
    cliente.telefono = None
    cliente.email = None
    cliente.descuento_tipo = None
    cliente.descuento_valor = None
    cliente.activo = False
    cliente.anonimizado_en = ahora
    for solicitud in cliente.solicitudes:
        solicitud.descripcion = None
    revocar_autorizacion(cliente, ahora)
    cliente.publicidad_fecha = None
