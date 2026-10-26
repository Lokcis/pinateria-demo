"""Router de clientes: registro con autorizacion de datos, busqueda, ficha y descuento propio (HU-07, RF-025, RF-029 a RF-034).

Vendedores y administradores registran, buscan y editan clientes; solo el
administrador asigna el descuento propio. Las solicitudes de los titulares
(Habeas Data) las atiende solo el administrador (router `solicitudes_titular`).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.cliente import Cliente, OrigenRegistro
from app.models.usuario import RolUsuario, Usuario
from app.models.venta import Venta
from app.schemas.cliente import (
    ClienteCrearIn,
    ClienteEditarIn,
    ClienteFichaOut,
    ClienteListadoOut,
    ClienteOut,
    DescuentoClienteIn,
    PoliticaOut,
    VentaClienteOut,
)
from app.schemas.venta import PagoOut
from app.services.politica_datos import cargar_datos_negocio, construir_politica, version_vigente

router = APIRouter(
    prefix="/clientes",
    tags=["clientes"],
    dependencies=[Depends(requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR))],
)

_MSG_DOCUMENTO_REPETIDO = "Ya existe un cliente con ese documento."
_MSG_ANONIMIZADO = "El cliente fue anonimizado y sus datos ya no se pueden modificar."


def _escapar_like(fragmento: str) -> str:
    """Escapa los comodines de LIKE para buscar el texto literal."""
    return fragmento.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _obtener_o_404(db: Session, cliente_id: int) -> Cliente:
    """Busca un cliente por id o lanza 404.

    Args:
        db: Sesion de base de datos.
        cliente_id: Id del cliente.

    Returns:
        Cliente: El cliente encontrado.

    Raises:
        HTTPException: 404 si no existe.
    """
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El cliente con id={cliente_id} no existe.")
    return cliente


def _validar_documento_libre(db: Session, documento: str | None, excluir_id: int | None = None) -> None:
    """Verifica que el documento no lo tenga otro cliente.

    Args:
        db: Sesion de base de datos.
        documento: Documento a validar; None siempre es valido.
        excluir_id: Cliente que se esta editando, si aplica.

    Raises:
        HTTPException: 409 si el documento ya existe.
    """
    if documento is None:
        return
    consulta = db.query(Cliente.id).filter(Cliente.documento == documento)
    if excluir_id is not None:
        consulta = consulta.filter(Cliente.id != excluir_id)
    if consulta.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_DOCUMENTO_REPETIDO)


def _limites_de_fecha(desde: date | None, hasta: date | None) -> tuple[datetime | None, datetime | None]:
    """Convierte un rango de dias (hora del negocio) en limites [inicio, fin) de timestamp."""
    zona = ZoneInfo(settings.zona_horaria)
    inicio = datetime.combine(desde, time.min, tzinfo=zona) if desde else None
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=zona) if hasta else None
    return inicio, fin


@router.get("/politica", response_model=PoliticaOut)
def politica_vigente(db: Session = Depends(get_db)) -> dict:
    """Devuelve la politica de tratamiento de datos vigente: aviso, casillas de autorizacion y texto completo.

    El POS la muestra antes de guardar a un cliente; la version devuelta es la que queda como evidencia.

    Args:
        db: Sesion de base de datos inyectada.

    Returns:
        PoliticaOut: Ver `services/politica_datos.py`.
    """
    return construir_politica(cargar_datos_negocio(db))


@router.get("", response_model=list[ClienteListadoOut])
def listar_clientes(
    q: str | None = Query(None, min_length=1, description="Nombre (parcial), documento o telefono."),
    activo: bool | None = Query(None, description="Filtra por clientes dados de alta o de baja."),
    solo_utilizables: bool = Query(False, description="Solo clientes que pueden asociarse a una venta nueva."),
    acepta_publicidad: bool | None = Query(None, description="Filtra por quienes autorizaron (o no) recibir promociones."),
    total_min: Decimal | None = Query(None, ge=0, description="Total comprado minimo."),
    total_max: Decimal | None = Query(None, ge=0, description="Total comprado maximo."),
    desde: date | None = Query(None, description="Solo compras desde este dia (hora del negocio)."),
    hasta: date | None = Query(None, description="Solo compras hasta este dia, inclusive."),
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ClienteListadoOut]:
    """Busca y lista clientes con su resumen de compras (RF-030, RF-032, RF-033).

    Si se indica un rango de fechas, el resumen cuenta solo las compras de ese
    rango y se omiten los clientes que no compraron en el. Los rangos de total
    comprado se aplican sobre ese mismo resumen.

    Args:
        q: Fragmento del nombre, o parte del documento o del telefono.
        activo: Filtro por estado.
        solo_utilizables: Excluye desactivados, revocados y anonimizados.
        acepta_publicidad: True para ver solo a quienes autorizaron recibir promociones.
        total_min: Total comprado minimo.
        total_max: Total comprado maximo.
        desde: Primer dia de compras a considerar.
        hasta: Ultimo dia de compras a considerar.
        limite: Maximo de clientes a devolver.
        db: Sesion de base de datos inyectada.

    Returns:
        list[ClienteListadoOut]: Clientes ordenados por nombre.

    Raises:
        HTTPException: 422 si los rangos estan invertidos.
    """
    if total_min is not None and total_max is not None and total_min > total_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El total mínimo no puede superar al máximo."
        )
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La fecha inicial no puede ser posterior a la final."
        )

    inicio, fin = _limites_de_fecha(desde, hasta)
    compras = db.query(
        Venta.cliente_id.label("cliente_id"),
        func.count(Venta.id).label("numero_ventas"),
        func.coalesce(func.sum(Venta.total), 0).label("total_comprado"),
        func.max(Venta.fecha).label("ultima_compra"),
    ).filter(Venta.cliente_id.isnot(None))
    if inicio is not None:
        compras = compras.filter(Venta.fecha >= inicio)
    if fin is not None:
        compras = compras.filter(Venta.fecha < fin)
    resumen = compras.group_by(Venta.cliente_id).subquery()

    numero = func.coalesce(resumen.c.numero_ventas, 0)
    total = func.coalesce(resumen.c.total_comprado, 0)
    consulta = db.query(Cliente, numero, total, resumen.c.ultima_compra).outerjoin(
        resumen, resumen.c.cliente_id == Cliente.id
    )

    if q is not None:
        q = q.strip()
        fragmento = _escapar_like(q)
        consulta = consulta.filter(
            Cliente.nombre.ilike(f"%{fragmento}%", escape="\\")
            | Cliente.documento.ilike(f"{fragmento}%", escape="\\")
            | Cliente.telefono.ilike(f"%{fragmento}%", escape="\\")
        )
    if activo is not None:
        consulta = consulta.filter(Cliente.activo == activo)
    if acepta_publicidad is not None:
        consulta = consulta.filter(Cliente.acepta_publicidad == acepta_publicidad)
    if solo_utilizables:
        consulta = consulta.filter(
            Cliente.activo.is_(True), Cliente.autorizacion_revocada_en.is_(None), Cliente.anonimizado_en.is_(None)
        )
    if inicio is not None or fin is not None:
        consulta = consulta.filter(resumen.c.cliente_id.isnot(None))
    if total_min is not None:
        consulta = consulta.filter(total >= total_min)
    if total_max is not None:
        consulta = consulta.filter(total <= total_max)

    filas = consulta.order_by(Cliente.nombre, Cliente.id).limit(limite).all()
    return [
        ClienteListadoOut(
            **ClienteOut.model_validate(cliente).model_dump(),
            numero_ventas=n,
            total_comprado=t,
            ultima_compra=ultima,
        )
        for cliente, n, t, ultima in filas
    ]


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    payload: ClienteCrearIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)),
) -> Cliente:
    """Registra un cliente con la evidencia de su autorizacion de datos (RF-029, RF-034).

    La fecha, la version de la politica vigente y el empleado que recogio la
    autorizacion los pone el servidor. El cliente nace sin descuento propio.

    Args:
        payload: Datos del cliente y su autorizacion.
        db: Sesion de base de datos inyectada.
        usuario_actual: Empleado que registra al cliente.

    Returns:
        ClienteOut: El cliente creado.

    Raises:
        HTTPException: 409 si el documento ya existe.
    """
    _validar_documento_libre(db, payload.documento)
    ahora = datetime.now(ZoneInfo("UTC"))
    cliente = Cliente(
        nombre=payload.nombre,
        documento=payload.documento,
        telefono=payload.telefono,
        email=payload.email,
        autorizacion_fecha=ahora,
        autorizacion_medio=payload.autorizacion_medio,
        autorizacion_version=version_vigente(cargar_datos_negocio(db)),
        acepta_publicidad=payload.acepta_publicidad,
        publicidad_fecha=ahora if payload.acepta_publicidad else None,
        origen_registro=OrigenRegistro.EMPLEADO,
        autorizacion_registrada_por=usuario_actual.id,
    )
    db.add(cliente)
    try:
        db.commit()
    except IntegrityError as exc:  # carrera con otro registro del mismo documento
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_DOCUMENTO_REPETIDO) from exc
    db.refresh(cliente)
    return cliente


@router.get("/{cliente_id}", response_model=ClienteFichaOut)
def obtener_ficha(cliente_id: int, db: Session = Depends(get_db)) -> ClienteFichaOut:
    """Devuelve la ficha del cliente: datos, total comprado e historial de ventas (RF-032).

    Args:
        cliente_id: Id del cliente.
        db: Sesion de base de datos inyectada.

    Returns:
        ClienteFichaOut: Datos, resumen (vista `vw_clientes_resumen`) y ventas.

    Raises:
        HTTPException: 404 si no existe.
    """
    cliente = _obtener_o_404(db, cliente_id)
    fila = db.execute(
        text(
            "SELECT numero_ventas, total_comprado, ultima_compra "
            "FROM vw_clientes_resumen WHERE cliente_id = :id"
        ),
        {"id": cliente_id},
    ).one()
    ventas = (
        db.query(Venta)
        .options(joinedload(Venta.usuario), joinedload(Venta.pagos))
        .filter(Venta.cliente_id == cliente_id)
        .order_by(Venta.fecha.desc(), Venta.id.desc())
        .all()
    )
    return ClienteFichaOut(
        **ClienteOut.model_validate(cliente).model_dump(),
        autorizacion_recogida_por=cliente.registrada_por.nombre if cliente.registrada_por else None,
        numero_ventas=fila.numero_ventas,
        total_comprado=fila.total_comprado,
        ultima_compra=fila.ultima_compra,
        ventas=[
            VentaClienteOut(
                id=v.id,
                fecha=v.fecha,
                total=v.total,
                vendedor=v.usuario.nombre,
                pagos=[PagoOut.model_validate(p) for p in v.pagos],
            )
            for v in ventas
        ],
    )


@router.patch("/{cliente_id}", response_model=ClienteOut)
def editar_cliente(cliente_id: int, payload: ClienteEditarIn, db: Session = Depends(get_db)) -> Cliente:
    """Edita los datos de un cliente o lo da de baja/alta; solo se cambian los campos presentes (RF-030).

    El descuento propio se asigna aparte (`PUT /clientes/{id}/descuento`, solo administrador).

    Args:
        cliente_id: Cliente a editar.
        payload: Campos a actualizar.
        db: Sesion de base de datos inyectada.

    Returns:
        ClienteOut: El cliente actualizado.

    Raises:
        HTTPException: 404 si no existe; 409 si esta anonimizado o el documento ya existe;
            422 si se manda nombre o estado nulos.
    """
    cliente = _obtener_o_404(db, cliente_id)
    if cliente.anonimizado_en is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_ANONIMIZADO)
    datos = payload.model_dump(exclude_unset=True)
    for campo in ("nombre", "activo"):
        if campo in datos and datos[campo] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"El campo '{campo}' no puede quedar vacío."
            )
    if "documento" in datos:
        _validar_documento_libre(db, datos["documento"], excluir_id=cliente.id)
    publicidad = datos.pop("acepta_publicidad", None)
    if publicidad is not None and publicidad != cliente.acepta_publicidad:
        if publicidad and not cliente.utilizable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se pueden activar las promociones de un cliente desactivado o con la autorización revocada.",
            )
        cliente.acepta_publicidad = publicidad
        cliente.publicidad_fecha = datetime.now(ZoneInfo("UTC"))
    for campo, valor in datos.items():
        setattr(cliente, campo, valor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_DOCUMENTO_REPETIDO) from exc
    db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}/descuento", response_model=ClienteOut)
def asignar_descuento(
    cliente_id: int,
    payload: DescuentoClienteIn,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Cliente:
    """Asigna o quita el descuento propio de un cliente; solo el administrador (RF-025).

    Args:
        cliente_id: Cliente al que se le asigna.
        payload: Tipo y valor del descuento; ambos vacios lo quitan.
        db: Sesion de base de datos inyectada.

    Returns:
        ClienteOut: El cliente con su descuento.

    Raises:
        HTTPException: 404 si no existe; 409 si esta anonimizado.
    """
    cliente = _obtener_o_404(db, cliente_id)
    if cliente.anonimizado_en is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_ANONIMIZADO)
    cliente.descuento_tipo = payload.tipo
    cliente.descuento_valor = payload.valor
    db.commit()
    db.refresh(cliente)
    return cliente
