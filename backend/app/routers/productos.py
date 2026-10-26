"""Router de productos: busqueda hibrida (HU-01) y catalogo/inventario (RF-006 a RF-009)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.ajuste_inventario import AjusteInventario
from app.models.categoria import Categoria
from app.models.producto import Producto, TipoProducto
from app.models.producto_componente import ProductoComponente
from app.models.usuario import RolUsuario, Usuario
from app.schemas.producto import (
    AjusteInventarioIn,
    AjusteInventarioOut,
    CatalogoOut,
    ComponenteIn,
    ProductoCrearIn,
    ProductoEditarIn,
    ProductoOut,
    StockMinimoIn,
    UsadoEnOut,
)
from app.services.exceptions import (
    CicloComposicionError,
    InventarioError,
    ProductoNoEncontradoError,
    SignoAjusteInvalidoError,
)
from app.services.inventario import aplicar_ajuste_inventario, validar_sin_ciclos

router = APIRouter(prefix="/productos", tags=["productos"])

LIMITE_RESULTADOS_BUSQUEDA = 20
TAMANO_PAGINA_MAXIMO = 100


@router.get("/buscar", response_model=list[ProductoOut])
def buscar_productos(
    q: str = Query(..., min_length=1, description="Codigo de barras, nombre o categoria a buscar."),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> list[Producto]:
    """Busca productos por codigo de barras exacto, con fallback a nombre/categoria por trigramas.

    Estrategia (HU-01, criterios de aceptacion):
        1. Intenta un match exacto contra `productos.codigo_barras`
           (soporta el escaneo instantaneo del lector fisico via el
           indice unico parcial `ux_productos_codigo_barras`); si hay
           match, se agrega al carrito de inmediato sin busqueda parcial.
        2. Si no hay match exacto, cae a busqueda parcial por similitud
           de trigramas (`pg_trgm`) sobre `productos.nombre` **o**
           `categorias.nombre` ("coincidencias parciales por nombre o
           categoria", HU-01), para el tecleo manual en el POS.

    Args:
        q: Termino de busqueda: puede ser un codigo de barras completo,
            texto parcial del nombre del producto, o de su categoria.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado (VENDEDOR o ADMINISTRADOR);
            sin token responde 401 y con otro rol 403, como `GET /productos`.

    Returns:
        list[Producto]: Lista de productos activos que coinciden. Con
        match exacto por codigo de barras, contiene a lo sumo un
        elemento. Con fallback por nombre/categoria, hasta
        `LIMITE_RESULTADOS_BUSQUEDA` resultados ordenados por la mejor
        similitud (nombre o categoria) descendente.
    """
    producto_exacto = (
        db.query(Producto)
        .options(joinedload(Producto.categoria))
        .filter(Producto.codigo_barras == q, Producto.activo.is_(True))
        .one_or_none()
    )
    if producto_exacto is not None:
        return [producto_exacto]

    similitud_nombre = func.similarity(Producto.nombre, q)
    similitud_categoria = func.similarity(Categoria.nombre, q)

    # `%` de pg_trgm compara contra el texto completo (umbral 0.3), asi que un
    # fragmento como "glo" no encuentra "Globo metalizado estrella 18 pulgadas".
    # El ILIKE cubre la busqueda parcial y usa el indice GIN trigram.
    fragmento = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    return (
        db.query(Producto)
        .join(Categoria, Producto.categoria_id == Categoria.id)
        .filter(Producto.activo.is_(True))
        .filter(
            or_(
                Producto.nombre.ilike(fragmento, escape="\\"),
                Categoria.nombre.ilike(fragmento, escape="\\"),
                Producto.nombre.op("%")(q),
                Categoria.nombre.op("%")(q),
            )
        )
        .order_by(func.greatest(similitud_nombre, similitud_categoria).desc())
        .limit(LIMITE_RESULTADOS_BUSQUEDA)
        .all()
    )


def _validar_categoria_existe(db: Session, categoria_id: int) -> None:
    """Verifica que exista una categoria con ese id, o lanza 404.

    Args:
        db: Sesion de base de datos inyectada.
        categoria_id: Id de categoria a validar.

    Raises:
        HTTPException: 404 si no existe una categoria con ese id.
    """
    if db.query(Categoria.id).filter(Categoria.id == categoria_id).one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La categoria con id={categoria_id} no existe.",
        )


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    payload: ProductoCrearIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Producto:
    """Da de alta un producto nuevo en el catalogo (HU-02, RF-016).

    `codigo_barras` es opcional (HU-02: anchetas, mermas o mercancia
    artesanal sin etiqueta de fabrica); `nombre`, `precio_venta`,
    `categoria_id` y `stock_inicial` son obligatorios y los valida
    Pydantic (`ProductoCrearIn`) antes de llegar aqui.

    Args:
        payload: Datos del producto a crear.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol ADMINISTRADOR.

    Returns:
        ProductoOut: El producto recien creado, ya visible para
        `/productos/buscar` y `/productos` (HU-02, tercer criterio).

    Raises:
        HTTPException: 404 si `categoria_id` no existe; 409 si
            `codigo_barras` ya esta en uso por otro producto.
    """
    _validar_categoria_existe(db, payload.categoria_id)

    producto = Producto(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        categoria_id=payload.categoria_id,
        codigo_barras=payload.codigo_barras,
        tipo=payload.tipo,
        precio_venta=payload.precio_venta,
        stock_actual=payload.stock_inicial,
        stock_minimo=payload.stock_minimo,
    )
    db.add(producto)
    try:
        db.flush()
        _reemplazar_receta(db, producto, payload.componentes)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto activo con el codigo de barras {payload.codigo_barras!r}.",
        ) from exc
    except HTTPException:
        db.rollback()
        raise

    db.refresh(producto)
    return producto


@router.patch("/{producto_id}", response_model=ProductoOut)
def editar_producto(
    producto_id: int,
    payload: ProductoEditarIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Producto:
    """Edita los atributos generales de un producto existente (RF-016).

    No toca `stock_actual` ni `stock_minimo`: para eso estan
    `/productos/{id}/ajustes` y `/productos/{id}/stock-minimo`, que
    dejan registro de por que cambio el stock.

    Args:
        producto_id: Identificador del producto a editar.
        payload: Campos a actualizar (los ausentes no se tocan).
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol ADMINISTRADOR.

    Returns:
        ProductoOut: El producto ya actualizado.

    Raises:
        HTTPException: 404 si el producto (o la nueva `categoria_id`,
            si se envia) no existe; 409 si el nuevo `codigo_barras` ya
            esta en uso por otro producto.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).one_or_none()
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto con id={producto_id} no existe.",
        )

    datos = payload.model_dump(exclude_unset=True)
    if "categoria_id" in datos:
        _validar_categoria_existe(db, datos["categoria_id"])

    componentes = payload.componentes
    datos.pop("componentes", None)
    for campo, valor in datos.items():
        setattr(producto, campo, valor)

    try:
        if componentes is not None:
            _reemplazar_receta(db, producto, componentes)
        elif producto.tipo == TipoProducto.UNIDAD and producto.componentes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un producto de tipo unidad no puede tener componentes: quita primero su receta.",
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto activo con el codigo de barras {datos.get('codigo_barras')!r}.",
        ) from exc
    except HTTPException:
        db.rollback()
        raise

    db.refresh(producto)
    return producto


def _reemplazar_receta(db: Session, producto: Producto, componentes: list[ComponenteIn]) -> None:
    """Reemplaza la receta completa de un producto compuesto (paquete o ancheta).

    Valida que el producto no sea de tipo unidad, que no haya componentes
    repetidos, que cada componente exista y este activo, y que la receta
    no cree ciclos (directos ni indirectos). No hace commit: el llamador
    decide y, ante `HTTPException`, debe hacer rollback.

    Args:
        db: Sesion de base de datos inyectada.
        producto: Producto (ya persistido con id) cuya receta se reemplaza.
        componentes: Nueva receta; una lista vacia la deja sin componentes.

    Raises:
        HTTPException: 422 si es tipo unidad con componentes o hay
            componentes repetidos; 404 si un componente no existe; 409 si
            un componente esta inactivo o la receta crearia un ciclo.
    """
    if componentes and producto.tipo == TipoProducto.UNIDAD:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo los productos de tipo paquete o ancheta pueden tener componentes.",
        )
    ids = [c.producto_id for c in componentes]
    if len(ids) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un mismo producto no puede repetirse en la receta: suma sus cantidades en una sola linea.",
        )

    producto.componentes.clear()
    db.flush()

    for linea in componentes:
        componente = db.query(Producto).filter(Producto.id == linea.producto_id).one_or_none()
        if componente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El componente con id={linea.producto_id} no existe.",
            )
        if not componente.activo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El componente {componente.nombre!r} esta desactivado: reactivalo antes de usarlo en una receta.",
            )
        try:
            validar_sin_ciclos(db, producto.id, componente.id)
        except CicloComposicionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        producto.componentes.append(
            ProductoComponente(producto_componente_id=componente.id, cantidad=linea.cantidad)
        )
    db.flush()


def _cambiar_activo(db: Session, producto_id: int, activo: bool) -> Producto:
    """Activa o desactiva un producto (RF-016).

    Args:
        db: Sesion de base de datos inyectada.
        producto_id: Identificador del producto.
        activo: Nuevo valor de `activo`.

    Returns:
        Producto: El producto ya actualizado.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).one_or_none()
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto con id={producto_id} no existe.",
        )

    producto.activo = activo
    db.commit()
    db.refresh(producto)
    return producto


@router.get("/{producto_id}/usado-en", response_model=list[UsadoEnOut])
def productos_que_lo_usan(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> list[UsadoEnOut]:
    """Lista los productos compuestos (paquetes/anchetas) que llevan este producto en su receta.

    Sirve para avisar, antes de desactivar un producto, que sigue siendo
    componente de otros: desactivarlo no lo saca de las recetas y su stock
    se sigue descontando al armar esos compuestos.

    Args:
        producto_id: Identificador del producto consultado.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol ADMINISTRADOR.

    Returns:
        list[UsadoEnOut]: Compuestos que lo usan, ordenados por nombre.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    if db.query(Producto.id).filter(Producto.id == producto_id).one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto con id={producto_id} no existe.",
        )
    compuestos = (
        db.query(Producto)
        .join(ProductoComponente, ProductoComponente.producto_padre_id == Producto.id)
        .filter(ProductoComponente.producto_componente_id == producto_id)
        .order_by(Producto.nombre)
        .all()
    )
    return [UsadoEnOut(id=c.id, nombre=c.nombre, tipo=c.tipo, activo=c.activo) for c in compuestos]


@router.patch("/{producto_id}/desactivar", response_model=ProductoOut)
def desactivar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Producto:
    """Desactiva un producto: deja de aparecer en el POS y en el catalogo por defecto (RF-016).

    Args:
        producto_id: Identificador del producto a desactivar.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol ADMINISTRADOR.

    Returns:
        ProductoOut: El producto ya desactivado.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    return _cambiar_activo(db, producto_id, activo=False)


@router.patch("/{producto_id}/reactivar", response_model=ProductoOut)
def reactivar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Producto:
    """Reactiva un producto previamente desactivado (contraparte simetrica de RF-016).

    Args:
        producto_id: Identificador del producto a reactivar.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol ADMINISTRADOR.

    Returns:
        ProductoOut: El producto ya reactivado.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    return _cambiar_activo(db, producto_id, activo=True)


@router.get("", response_model=CatalogoOut)
def listar_catalogo(
    q: str | None = Query(None, min_length=1, description="Filtro opcional por nombre de producto."),
    categoria_id: int | None = Query(None, description="Filtro opcional por categoria."),
    activo: bool | None = Query(True, description="Filtro por estado del producto. None trae ambos."),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(20, ge=1, le=TAMANO_PAGINA_MAXIMO),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> CatalogoOut:
    """Lista el catalogo de productos con filtro y paginacion (RF-006).

    A diferencia de `/productos/buscar` (pensado para el POS, HU-01),
    este endpoint es para pantallas de consulta de inventario: no hace
    matching por similitud, permite filtrar por categoria y estado, y
    devuelve el total de resultados para paginar en el frontend.

    Args:
        q: Filtro opcional por fragmento del nombre (ILIKE).
        categoria_id: Filtro opcional por categoria.
        activo: Filtro por estado del producto (por defecto, solo
            activos). `None` trae tanto activos como inactivos.
        pagina: Numero de pagina (base 1).
        tamano_pagina: Cantidad de resultados por pagina.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado (VENDEDOR o ADMINISTRADOR).

    Returns:
        CatalogoOut: Total de resultados y la pagina solicitada,
        ordenada por nombre.
    """
    consulta = db.query(Producto).options(
        joinedload(Producto.categoria),
        selectinload(Producto.componentes).joinedload(ProductoComponente.producto_componente),
    )
    if activo is not None:
        consulta = consulta.filter(Producto.activo.is_(activo))
    if categoria_id is not None:
        consulta = consulta.filter(Producto.categoria_id == categoria_id)
    if q is not None:
        consulta = consulta.filter(Producto.nombre.ilike(f"%{q}%"))

    total = consulta.count()
    productos = (
        consulta.order_by(Producto.nombre)
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )
    return CatalogoOut(total=total, productos=productos)


@router.patch("/{producto_id}/stock-minimo", response_model=ProductoOut)
def actualizar_stock_minimo(
    producto_id: int,
    payload: StockMinimoIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Producto:
    """Actualiza el stock minimo de un producto (RF-007).

    Args:
        producto_id: Identificador del producto a actualizar.
        payload: Nuevo valor de `stock_minimo`.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado con rol ADMINISTRADOR.

    Returns:
        Producto: El producto con su `stock_minimo` actualizado.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).one_or_none()
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto con id={producto_id} no existe.",
        )

    producto.stock_minimo = payload.stock_minimo
    db.commit()
    db.refresh(producto)
    return producto


@router.post("/{producto_id}/ajustes", response_model=AjusteInventarioOut, status_code=status.HTTP_201_CREATED)
def registrar_ajuste(
    producto_id: int,
    payload: AjusteInventarioIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> AjusteInventario:
    """Registra un ajuste manual de inventario, con motivo obligatorio (RF-009).

    Args:
        producto_id: Identificador del producto a ajustar.
        payload: Tipo, cantidad con signo y motivo del ajuste.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado (VENDEDOR o ADMINISTRADOR),
            registrado como autor del ajuste.

    Returns:
        AjusteInventarioOut: El ajuste registrado.

    Raises:
        HTTPException: 404 si el producto no existe; 400 si el signo
            de `cantidad` no corresponde al `tipo` dado; 409 si el
            ajuste dejaria el stock en negativo.
    """
    try:
        ajuste = aplicar_ajuste_inventario(
            db,
            producto_id=producto_id,
            usuario_id=usuario_actual.id,
            tipo=payload.tipo,
            cantidad=payload.cantidad,
            motivo=payload.motivo,
        )
        db.commit()
        db.refresh(ajuste)
        return ajuste
    except ProductoNoEncontradoError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SignoAjusteInvalidoError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InventarioError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{producto_id}/ajustes", response_model=list[AjusteInventarioOut])
def listar_ajustes(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> list[AjusteInventario]:
    """Lista el historial de ajustes manuales de un producto, del mas reciente al mas antiguo (RF-009).

    Args:
        producto_id: Identificador del producto.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado (VENDEDOR o ADMINISTRADOR).

    Returns:
        list[AjusteInventarioOut]: Los ajustes del producto.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    if db.query(Producto.id).filter(Producto.id == producto_id).one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto con id={producto_id} no existe.",
        )

    return (
        db.query(AjusteInventario)
        .filter(AjusteInventario.producto_id == producto_id)
        .order_by(AjusteInventario.fecha.desc(), AjusteInventario.id.desc())
        .all()
    )
