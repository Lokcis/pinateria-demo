"""Router de ventas: creacion transaccional de una venta (HU-01; Adendo v2: HU-05, HU-06, HU-07 y HU-08; Fase 9)."""

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.cliente import Cliente
from app.models.descuento import DescuentoGeneral, OrigenDescuento, TipoDescuento, TopeDescuento
from app.models.detalle_venta import DetalleVenta
from app.models.pago_venta import PagoVenta
from app.models.producto import Producto
from app.models.usuario import RolUsuario, Usuario
from app.models.venta import MetodoPago, Venta
from app.schemas.venta import (
    DescuentoIn,
    DetalleHistorialOut,
    HistorialDiaOut,
    PagoOut,
    VendedorOut,
    VentaHistorialOut,
    VentaIn,
    VentaOut,
)
from app.services.calculo_venta import (
    calcular_monto_descuento,
    calcular_totales,
    prorratear_descuento,
    validar_pagos,
    validar_topes,
)
from app.services.exceptions import InventarioError
from app.services.inventario import consumir_stock

router = APIRouter(prefix="/ventas", tags=["ventas"])

_MSG_GENERAL_CAMBIO = (
    "El descuento general cambió mientras se hacía la venta. Revise el descuento y confirme de nuevo."
)

# Margen de reloj para la hora de una venta sin conexion: el PC de la tienda puede ir unos minutos adelantado.
_TOLERANCIA_RELOJ = timedelta(minutes=5)


@router.get("/hoy", response_model=HistorialDiaOut)
def historial_de_hoy(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> HistorialDiaOut:
    """Devuelve las ventas de hoy con su resumen (RF-018).

    "Hoy" se calcula en la zona horaria del negocio (`ZONA_HORARIA`, por
    defecto America/Bogota), no en UTC: una venta a las 8 pm en Bogota ya
    es "manana" en UTC pero sigue siendo del dia de la tienda.

    Un VENDEDOR ve las ventas que quedaron a su nombre y las que registro el
    a nombre de otra persona (Venta.registrada_por_id); un ADMINISTRADOR ve las de
    todos los vendedores. El total por metodo suma el monto de cada pago,
    asi una venta con pagos mixtos aporta a cada metodo lo que se pago con
    el (Adendo v2, RF-041).

    Args:
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado (VENDEDOR o ADMINISTRADOR).

    Returns:
        HistorialDiaOut: Resumen del dia y sus ventas, de la mas reciente
        a la mas antigua.
    """
    zona = ZoneInfo(settings.zona_horaria)
    hoy = datetime.now(zona).date()
    inicio = datetime.combine(hoy, time.min, tzinfo=zona)
    fin = inicio + timedelta(days=1)

    consulta = (
        db.query(Venta)
        .options(
            joinedload(Venta.detalles).joinedload(DetalleVenta.producto),
            joinedload(Venta.usuario),
            joinedload(Venta.registrada_por),
            joinedload(Venta.cliente),
            joinedload(Venta.pagos),
        )
        .filter(Venta.fecha >= inicio, Venta.fecha < fin)
    )
    if usuario_actual.rol == RolUsuario.VENDEDOR:
        consulta = consulta.filter(or_(Venta.usuario_id == usuario_actual.id, Venta.registrada_por_id == usuario_actual.id))
    ventas_orm = consulta.order_by(Venta.fecha.desc(), Venta.id.desc()).all()

    total_por_metodo: dict[MetodoPago, Decimal] = {}
    for venta in ventas_orm:
        for pago in venta.pagos:
            total_por_metodo[pago.metodo_pago] = total_por_metodo.get(pago.metodo_pago, Decimal("0")) + pago.monto

    return HistorialDiaOut(
        fecha=hoy,
        cantidad_ventas=len(ventas_orm),
        total_vendido=sum((venta.total for venta in ventas_orm), Decimal("0")),
        total_por_metodo=total_por_metodo,
        ventas=[
            VentaHistorialOut(
                id=venta.id,
                fecha=venta.fecha,
                subtotal=venta.subtotal,
                descuento_origen=venta.descuento_origen,
                descuento_tipo=venta.descuento_tipo,
                descuento_valor=venta.descuento_valor,
                descuento_monto=venta.descuento_monto,
                ajuste_redondeo=venta.ajuste_redondeo,
                total=venta.total,
                vendedor=venta.usuario.nombre,
                registrada_por=(
                    venta.registrada_por.nombre
                    if venta.registrada_por_id not in (None, venta.usuario_id)
                    else None
                ),
                cliente=venta.cliente.nombre if venta.cliente else None,
                sin_conexion=venta.sin_conexion,
                detalles=[
                    DetalleHistorialOut(
                        producto_id=d.producto_id,
                        nombre_producto=d.producto.nombre,
                        cantidad=d.cantidad,
                        precio_unitario=d.precio_unitario,
                        subtotal=d.subtotal,
                    )
                    for d in venta.detalles
                ],
                pagos=[PagoOut.model_validate(p) for p in venta.pagos],
            )
            for venta in ventas_orm
        ],
    )


@router.get("/vendedores", response_model=list[VendedorOut])
def listar_vendedores(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)),
) -> list[Usuario]:
    """Lista quienes pueden figurar como vendedor de una venta (HU-08, RF-036).

    Son los vendedores y administradores activos; el propietario y los usuarios
    inactivos no aparecen.

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (VENDEDOR o ADMINISTRADOR).

    Returns:
        list[VendedorOut]: Usuarios elegibles, ordenados por nombre.
    """
    return (
        db.query(Usuario)
        .filter(Usuario.activo.is_(True), Usuario.rol.in_((RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)))
        .order_by(Usuario.nombre)
        .all()
    )


def _resolver_vendedor(db: Session, vendedor_id: int | None, usuario_actual: Usuario) -> Usuario:
    """Determina quien realiza la venta: el elegido en el POS o, por defecto, el usuario de la sesion (RF-036).

    Args:
        db: Sesion de base de datos.
        vendedor_id: Vendedor elegido en el desplegable, o None.
        usuario_actual: Usuario autenticado.

    Returns:
        Usuario: El vendedor al que se asigna la venta.

    Raises:
        HTTPException: 422 si no existe, esta inactivo o es propietario.
    """
    if vendedor_id is None or vendedor_id == usuario_actual.id:
        return usuario_actual
    vendedor = db.get(Usuario, vendedor_id)
    if vendedor is None or not vendedor.activo or vendedor.rol not in (RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El vendedor elegido no es válido: debe ser un vendedor o administrador activo.",
        )
    return vendedor


def _resolver_cliente(db: Session, cliente_id: int | None) -> Cliente | None:
    """Valida el cliente asociado a la venta (RF-031).

    Args:
        db: Sesion de base de datos.
        cliente_id: Cliente elegido, o None.

    Returns:
        Cliente | None: El cliente, o None si la venta no tiene.

    Raises:
        HTTPException: 404 si no existe; 422 si esta desactivado, revoco su
            autorizacion o fue anonimizado.
    """
    if cliente_id is None:
        return None
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El cliente con id={cliente_id} no existe.")
    if not cliente.utilizable:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El cliente no se puede asociar a la venta: está desactivado o retiró su autorización de datos.",
        )
    return cliente


def _resolver_descuento(
    db: Session,
    descuento: DescuentoIn,
    subtotal: Decimal,
    usuario: Usuario,
    cliente: Cliente | None,
    sin_conexion: bool = False,
) -> tuple[OrigenDescuento, TipoDescuento | None, Decimal | None, Decimal]:
    """Valida el descuento elegido contra la configuracion y calcula su monto (RF-026 a RF-028, RF-042).

    Args:
        db: Sesion de base de datos.
        descuento: Descuento enviado por el POS.
        subtotal: Subtotal de la venta.
        usuario: Quien registra la venta (los topes no aplican al administrador).
        cliente: Cliente asociado a la venta, o None.
        sin_conexion: True si la venta se hizo sin conexion (Fase 9): el descuento general se respeta
            tal como lo vio el cliente (`tipo` y `valor` del payload) aunque ya no este activo o haya cambiado.

    Returns:
        tuple: (origen, tipo, valor, monto en pesos).

    Raises:
        HTTPException: 409 si se pidio el descuento general y ya no esta activo;
            422 si el descuento no es valido o supera los topes.
    """
    general = db.get(DescuentoGeneral, 1)
    general_activo = general is not None and general.activo

    try:
        if descuento.origen == OrigenDescuento.CLIENTE:
            if cliente is None or cliente.descuento_tipo is None:
                raise ValueError("La venta no tiene un cliente con descuento propio.")
            # Como el general: un descuento en pesos mayor que el subtotal se limita al subtotal.
            if cliente.descuento_tipo == TipoDescuento.MONTO:
                monto = min(cliente.descuento_valor, subtotal)
            else:
                monto = calcular_monto_descuento(subtotal, cliente.descuento_tipo, cliente.descuento_valor)
            return OrigenDescuento.CLIENTE, cliente.descuento_tipo, cliente.descuento_valor, monto

        # El descuento general es opcional: se vende sin descuento aunque este activo.
        if descuento.origen == OrigenDescuento.NINGUNO:
            return OrigenDescuento.NINGUNO, None, None, Decimal("0")

        if descuento.origen == OrigenDescuento.GENERAL:
            if sin_conexion:
                # El POS aplico el general que tenia guardado: se respeta lo que pago el cliente.
                if descuento.tipo is None or descuento.valor is None:
                    raise ValueError("Una venta sin conexión con descuento general debe traer su tipo y su valor.")
                tipo_general, valor_general = descuento.tipo, descuento.valor
            else:
                if not general_activo:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_GENERAL_CAMBIO)
                tipo_general, valor_general = general.tipo, general.valor
            # Un descuento general en pesos mayor que el subtotal se limita al subtotal.
            if tipo_general == TipoDescuento.MONTO:
                monto = min(valor_general, subtotal)
            else:
                monto = calcular_monto_descuento(subtotal, tipo_general, valor_general)
            return OrigenDescuento.GENERAL, tipo_general, valor_general, monto

        # Manual: cambiado (tipo y valor) o quitado (ambos vacios).
        if (descuento.tipo is None) != (descuento.valor is None):
            raise ValueError("Indique el tipo y el valor del descuento, o quítelo.")
        if descuento.tipo is None:
            return OrigenDescuento.MANUAL, None, None, Decimal("0")

        monto = calcular_monto_descuento(subtotal, descuento.tipo, descuento.valor)
        if usuario.rol != RolUsuario.ADMINISTRADOR:
            topes = db.get(TopeDescuento, 1)
            if topes is not None:
                validar_topes(subtotal, monto, topes.tope_porcentaje, topes.tope_monto)
        return OrigenDescuento.MANUAL, descuento.tipo, descuento.valor, monto
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def _buscar_por_uuid(db: Session, uuid_cliente: UUID | None) -> Venta | None:
    """Busca la venta ya registrada con ese identificador del POS (Fase 9: envio idempotente).

    Args:
        db: Sesion de base de datos.
        uuid_cliente: Identificador que envio el POS, o None.

    Returns:
        Venta | None: La venta existente, o None si no hay ninguna (o no se envio identificador).
    """
    if uuid_cliente is None:
        return None
    return db.query(Venta).filter(Venta.uuid_cliente == uuid_cliente).one_or_none()


def _validar_fecha_sin_conexion(fecha: datetime) -> datetime:
    """Valida la hora que el POS dice que tuvo una venta hecha sin conexion (Fase 9).

    Args:
        fecha: Hora de la venta enviada por el POS.

    Returns:
        datetime: La misma fecha, con zona horaria.

    Raises:
        HTTPException: 422 si no trae zona horaria, es futura (mas alla de la tolerancia de reloj)
            o es mas antigua que `ventas_sin_conexion_dias_max`.
    """
    if fecha.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha de la venta sin conexión debe traer zona horaria.",
        )
    ahora = datetime.now(timezone.utc)
    if fecha > ahora + _TOLERANCIA_RELOJ:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha de la venta está en el futuro: revise la hora del equipo de la tienda.",
        )
    dias = settings.ventas_sin_conexion_dias_max
    if fecha < ahora - timedelta(days=dias):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La venta tiene más de {dias} días sin enviarse: pídale al administrador que la registre a mano.",
        )
    return fecha


@router.post("", response_model=VentaOut, status_code=status.HTTP_201_CREATED)
def crear_venta(
    payload: VentaIn,
    response: Response,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> Venta:
    """Registra una venta completa: lineas, descuento, pagos y descuento de stock.

    Toda la operacion ocurre en una unica transaccion SQL:
        1. Por cada linea del payload, bloquea el producto
           (`SELECT ... FOR UPDATE`, dentro de `consumir_stock`) y
           descuenta su stock (propio o, si falta, via composicion BOM
           recursiva). Congela `precio_unitario` y copia `costo_unitario`.
        2. Calcula subtotal -> descuento -> redondeo a $50 -> total
           (Adendo v2, HU-06) y reparte el descuento entre las lineas.
        3. Valida que la suma de los pagos sea igual al total y calcula las
           vueltas de los pagos en efectivo (Adendo v2, HU-05).
        4. La venta queda a nombre del vendedor elegido (HU-08) y del cliente
           asociado, si lo hay (HU-07).
        5. Si CUALQUIER paso falla, se hace rollback de toda la
           transaccion: no se permiten ventas parciales ni dejar stock en
           negativo.

    Fase 9 (modo sin conexion): si el POS envia `uuid_cliente`, el envio es idempotente: reenviar una
    venta que ya se registro (se perdio la respuesta, o salio de la cola sin conexion) devuelve la
    existente con 200 y NO vuelve a descontar stock. Una venta con `sin_conexion` conserva la hora
    en que se hizo y los precios y el descuento general que vio el cliente.

    Args:
        payload: Lineas, pagos, descuento, cliente y vendedor de la venta.
        response: Respuesta HTTP, para devolver 200 (y no 201) ante un reenvio.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol VENDEDOR o
            ADMINISTRADOR (inyectado por RBAC).

    Returns:
        Venta: La venta creada, con sus lineas y sus pagos.

    Raises:
        HTTPException: 404 si algun `producto_id` no existe; 400 si
            algun producto no esta activo; 409 si no hay stock suficiente
            o si el descuento general cambio; 422 si el descuento, los
            pagos, el cliente, el vendedor o la fecha de una venta sin conexion no son validos.
    """
    existente = _buscar_por_uuid(db, payload.uuid_cliente)
    if existente is not None:
        response.status_code = status.HTTP_200_OK
        return existente

    subtotal = Decimal("0")
    detalles_orm: list[DetalleVenta] = []
    sin_conexion = payload.sin_conexion is not None

    try:
        fecha_venta = _validar_fecha_sin_conexion(payload.sin_conexion.fecha) if sin_conexion else None
        vendedor = _resolver_vendedor(db, payload.vendedor_id, usuario_actual)
        cliente = _resolver_cliente(db, payload.cliente_id)

        for linea in payload.detalles:
            producto = (
                db.query(Producto)
                .filter(Producto.id == linea.producto_id)
                .with_for_update()
                .one_or_none()
            )
            if producto is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El producto con id={linea.producto_id} no existe.",
                )
            if not producto.activo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El producto con id={linea.producto_id} no esta activo.",
                )

            # Sin conexion se respeta el precio que vio el cliente; si no, siempre el vigente del catalogo.
            precio_unitario = (
                linea.precio_unitario if sin_conexion and linea.precio_unitario is not None else producto.precio_venta
            )
            subtotal_linea = precio_unitario * linea.cantidad

            consumir_stock(db, linea.producto_id, linea.cantidad)

            detalles_orm.append(
                DetalleVenta(
                    producto_id=linea.producto_id,
                    cantidad=linea.cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal_linea,
                    costo_unitario=producto.costo_unitario,
                )
            )
            subtotal += subtotal_linea

        origen, tipo, valor, monto_descuento = _resolver_descuento(
            db, payload.descuento, subtotal, usuario_actual, cliente, sin_conexion
        )
        # El total cobrado siempre es multiplo de 50 (la moneda minima en circulacion);
        # los subtotales de cada linea conservan el valor exacto.
        totales = calcular_totales(subtotal, monto_descuento)

        for detalle, parte in zip(
            detalles_orm, prorratear_descuento([d.subtotal for d in detalles_orm], totales.descuento_monto)
        ):
            detalle.descuento_prorrateado = parte

        try:
            pagos = validar_pagos(
                [(p.metodo_pago, p.plataforma, p.monto, p.monto_recibido) for p in payload.pagos],
                totales.total,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        venta = Venta(
            usuario_id=vendedor.id,
            registrada_por_id=usuario_actual.id,
            cliente_id=cliente.id if cliente else None,
            uuid_cliente=payload.uuid_cliente,
            sin_conexion=sin_conexion,
            sincronizada_en=datetime.now(timezone.utc) if sin_conexion else None,
            subtotal=totales.subtotal,
            descuento_origen=origen,
            descuento_tipo=tipo,
            descuento_valor=valor,
            descuento_monto=totales.descuento_monto,
            ajuste_redondeo=totales.ajuste_redondeo,
            total=totales.total,
            detalles=detalles_orm,
            pagos=[
                PagoVenta(
                    metodo_pago=p.metodo_pago,
                    plataforma=p.plataforma,
                    monto=p.monto,
                    monto_recibido=p.monto_recibido,
                    vueltas=p.vueltas,
                )
                for p in pagos
            ],
        )
        if fecha_venta is not None:
            venta.fecha = fecha_venta
        db.add(venta)
        db.commit()
        db.refresh(venta)
        return venta

    except IntegrityError:
        db.rollback()
        # Dos envios simultaneos de la misma venta: el indice unico deja pasar uno solo.
        existente = _buscar_por_uuid(db, payload.uuid_cliente)
        if existente is None:
            raise
        response.status_code = status.HTTP_200_OK
        return existente
    except InventarioError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
