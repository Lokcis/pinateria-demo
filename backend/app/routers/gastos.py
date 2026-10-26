"""Router de gastos y categorias de gasto (Adendo v3, Fase G1: RF-059 a RF-066, RF-075, HU-12).

Permisos (docs/12, seccion 4): el administrador ve e ingresa todo; el propietario solo consulta; el vendedor solo
ingresa y ve, edita y anula unicamente lo que registro el mismo. El filtro por duenio y la ocultacion de las
compras viven en `services/gastos.py` (el servidor, nunca la pantalla); aqui se valida el rol de cada ruta.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.usuario import RolUsuario, Usuario
from app.models.venta import MetodoPago
from app.schemas.gasto import (
    AnularGastoIn,
    CategoriaGastoIn,
    CategoriaGastoOut,
    CategoriaGastoPatch,
    EstadoGasto,
    GastoIn,
    GastoOut,
    GastoPatch,
    OrigenGasto,
    ResumenGastosOut,
)
from app.services import gastos as servicio
from app.services.exceptions import (
    CategoriaGastoNoEncontradaError,
    GastoConflictoError,
    GastoInvalidoError,
    GastoNoEncontradoError,
    GastoSinPermisoError,
)
from app.services.rangos import rango_de_fechas

router = APIRouter(tags=["gastos"])

TAMANO_PAGINA_MAXIMO = 200

_todos = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.VENDEDOR, RolUsuario.PROPIETARIO)
_escritura = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.VENDEDOR)
_consulta_del_negocio = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.PROPIETARIO)
_solo_administrador = requerir_roles(RolUsuario.ADMINISTRADOR)

_ESTADO_HTTP = {
    GastoNoEncontradoError: status.HTTP_404_NOT_FOUND,
    CategoriaGastoNoEncontradaError: status.HTTP_404_NOT_FOUND,
    GastoInvalidoError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    GastoSinPermisoError: status.HTTP_403_FORBIDDEN,
    GastoConflictoError: status.HTTP_409_CONFLICT,
}


@contextmanager
def _errores_de_dominio(db: Session) -> Iterator[None]:
    """Revierte la transaccion y traduce los errores de dominio de gastos a su codigo HTTP.

    Args:
        db: Sesion cuya transaccion se revierte ante un error.

    Raises:
        HTTPException: 404 (no existe o no es suyo), 403 (operacion sin permiso), 409 (conflicto) o 422 (datos).
    """
    try:
        yield
    except tuple(_ESTADO_HTTP) as exc:
        db.rollback()
        raise HTTPException(status_code=_ESTADO_HTTP[type(exc)], detail=str(exc)) from exc


def _filtros(
    desde: date | None,
    hasta: date | None,
    categoria_id: int | None,
    metodo_pago: MetodoPago | None,
    estado: EstadoGasto | None,
    origen: OrigenGasto | None,
) -> servicio.FiltrosGastos:
    """Valida el rango (ver `rango_de_fechas`) y arma los filtros de la lista."""
    desde, hasta, _, _ = rango_de_fechas(desde, hasta)
    return servicio.FiltrosGastos(
        desde=desde, hasta=hasta, categoria_id=categoria_id, metodo_pago=metodo_pago, estado=estado, origen=origen
    )


# --- Categorias -----------------------------------------------------------------------------------------------


@router.get("/categorias-gasto", response_model=list[CategoriaGastoOut])
def listar_categorias_gasto(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_todos),
):
    """Lista las categorias de gasto (RF-060). El vendedor solo ve las activas, que son las que puede elegir.

    Args:
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador, vendedor o propietario.

    Returns:
        list[CategoriaGastoOut]: Las categorias, por nombre.
    """
    return servicio.listar_categorias(db, solo_activas=usuario_actual.rol == RolUsuario.VENDEDOR)


@router.post("/categorias-gasto", response_model=CategoriaGastoOut, status_code=status.HTTP_201_CREATED)
def crear_categoria_gasto(
    payload: CategoriaGastoIn,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_administrador),
):
    """Crea una categoria de gasto. Solo administrador.

    Args:
        payload: Nombre de la categoria.
        db: Sesion de base de datos inyectada.
        _usuario: Administrador autenticado.

    Returns:
        CategoriaGastoOut: La categoria creada.

    Raises:
        HTTPException: 409 si ya existe una con ese nombre.
    """
    with _errores_de_dominio(db):
        categoria = servicio.crear_categoria(db, payload.nombre)
    db.commit()
    return categoria


@router.patch("/categorias-gasto/{categoria_id}", response_model=CategoriaGastoOut)
def modificar_categoria_gasto(
    categoria_id: int,
    payload: CategoriaGastoPatch,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_administrador),
):
    """Renombra, activa o desactiva una categoria. Solo administrador; la de sistema no se toca.

    Args:
        categoria_id: Categoria a modificar.
        payload: Nombre nuevo y/o estado nuevo.
        db: Sesion de base de datos inyectada.
        _usuario: Administrador autenticado.

    Returns:
        CategoriaGastoOut: La categoria actualizada.

    Raises:
        HTTPException: 404 si no existe; 409 si es de sistema o el nombre ya existe.
    """
    with _errores_de_dominio(db):
        categoria = servicio.modificar_categoria(db, categoria_id, payload.nombre, payload.activa)
    db.commit()
    return categoria


# --- Gastos ---------------------------------------------------------------------------------------------------


@router.get("/gastos", response_model=list[GastoOut])
def listar_gastos(
    desde: date | None = Query(None, description="Primer dia (inclusivo). Por defecto, hasta."),
    hasta: date | None = Query(None, description="Ultimo dia (inclusivo). Por defecto, hoy."),
    categoria_id: int | None = Query(None),
    metodo_pago: MetodoPago | None = Query(None),
    estado: EstadoGasto | None = Query(None, description="vigente o anulado; sin valor, ambos."),
    origen: OrigenGasto | None = Query(None, description="gasto o compra; sin valor, ambos."),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(50, ge=1, le=TAMANO_PAGINA_MAXIMO),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_todos),
):
    """Lista los gastos del rango, de lo mas reciente a lo mas antiguo (RF-059, RF-063, RF-065).

    El administrador y el propietario reciben tambien las compras ya recibidas; el vendedor, solo SUS gastos.

    Args:
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango (no futuro).
        categoria_id: Solo esta categoria.
        metodo_pago: Solo esta forma de pago.
        estado: vigente / anulado.
        origen: gasto / compra.
        pagina: Numero de pagina (base 1).
        tamano_pagina: Tamano de pagina.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado.

    Returns:
        list[GastoOut]: Las filas de la pagina.

    Raises:
        HTTPException: 422 si el rango es invalido.
    """
    filtros = _filtros(desde, hasta, categoria_id, metodo_pago, estado, origen)
    return servicio.consultar_gastos(
        db, usuario_actual, filtros, limite=tamano_pagina, desplazamiento=(pagina - 1) * tamano_pagina
    )


@router.get("/gastos/resumen", response_model=ResumenGastosOut)
def resumen_gastos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    categoria_id: int | None = Query(None),
    metodo_pago: MetodoPago | None = Query(None),
    origen: OrigenGasto | None = Query(None),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_consulta_del_negocio),
):
    """Totales vigentes del rango por categoria y por forma de pago, incluidas las compras (RF-066).

    Administrador y propietario; el vendedor recibe 403 (no ve totales del negocio).

    Args:
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango (no futuro).
        categoria_id: Solo esta categoria.
        metodo_pago: Solo esta forma de pago.
        origen: gasto / compra.
        db: Sesion de base de datos inyectada.
        _usuario: Administrador o propietario.

    Returns:
        ResumenGastosOut: Los totales.
    """
    return servicio.resumen_de_gastos(db, _filtros(desde, hasta, categoria_id, metodo_pago, None, origen))


@router.get("/gastos/exportar")
def exportar_gastos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    categoria_id: int | None = Query(None),
    metodo_pago: MetodoPago | None = Query(None),
    origen: OrigenGasto | None = Query(None),
    incluir_anulados: bool = Query(False, description="Por defecto los anulados no se exportan."),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_consulta_del_negocio),
) -> Response:
    """Descarga un CSV (abre en Excel) del rango y los filtros, una fila por gasto o compra (RF-066).

    Args:
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango (no futuro).
        categoria_id: Solo esta categoria.
        metodo_pago: Solo esta forma de pago.
        origen: gasto / compra.
        incluir_anulados: Si es True, tambien salen los anulados (marcados como tales).
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o propietario.

    Returns:
        Response: El archivo CSV (UTF-8 con BOM, separado por punto y coma).
    """
    estado = None if incluir_anulados else EstadoGasto.VIGENTE
    filtros = _filtros(desde, hasta, categoria_id, metodo_pago, estado, origen)
    contenido = servicio.exportar_gastos_csv(db, usuario_actual, filtros)
    nombre = f"gastos_{filtros.desde.isoformat()}_a_{filtros.hasta.isoformat()}.csv"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/gastos", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def registrar_gasto(
    payload: GastoIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_escritura),
):
    """Registra un gasto (RF-059). Administrador y vendedor; el propietario recibe 403.

    El vendedor siempre registra con la fecha de hoy; el administrador puede elegir una anterior.

    Args:
        payload: Datos del gasto.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o vendedor, registrado como autor.

    Returns:
        GastoOut: El gasto creado.

    Raises:
        HTTPException: 404 si la categoria no existe; 403 si un vendedor manda otra fecha; 422 si los datos
            no cumplen las reglas (monto, plataforma, categoria desactivada, fecha futura).
    """
    with _errores_de_dominio(db):
        gasto = servicio.crear_gasto(db, usuario_actual, payload)
    db.commit()
    return servicio.obtener_gasto(db, usuario_actual, gasto.id)


@router.get("/gastos/{gasto_id}", response_model=GastoOut)
def obtener_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_todos),
):
    """Devuelve un gasto. Un vendedor recibe 404 si no es suyo.

    Args:
        gasto_id: Id del gasto.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado.

    Returns:
        GastoOut: El gasto.

    Raises:
        HTTPException: 404 si no existe o, para un vendedor, no es suyo.
    """
    with _errores_de_dominio(db):
        return servicio.obtener_gasto(db, usuario_actual, gasto_id)


@router.patch("/gastos/{gasto_id}", response_model=GastoOut)
def editar_gasto(
    gasto_id: int,
    payload: GastoPatch,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_escritura),
):
    """Edita un gasto vigente (RF-061). Administrador (cualquiera) o vendedor (solo los suyos).

    Args:
        gasto_id: Gasto a editar.
        payload: Campos a cambiar.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o vendedor.

    Returns:
        GastoOut: El gasto editado.

    Raises:
        HTTPException: 404 si no existe o es de otra persona (vendedor); 403 si un vendedor cambia la fecha;
            409 si esta anulado; 422 si los datos no cumplen las reglas.
    """
    with _errores_de_dominio(db):
        servicio.editar_gasto(db, usuario_actual, gasto_id, payload)
    db.commit()
    return servicio.obtener_gasto(db, usuario_actual, gasto_id)


@router.post("/gastos/{gasto_id}/anular", response_model=GastoOut)
def anular_gasto(
    gasto_id: int,
    payload: AnularGastoIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_escritura),
):
    """Anula un gasto vigente con su motivo (RF-062). Administrador (cualquiera) o vendedor (solo los suyos).

    El gasto no se borra: sigue en la lista, tachado, y deja de sumar en los totales.

    Args:
        gasto_id: Gasto a anular.
        payload: Motivo de la anulacion.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o vendedor.

    Returns:
        GastoOut: El gasto anulado.

    Raises:
        HTTPException: 404 si no existe o es de otra persona (vendedor); 409 si ya estaba anulado.
    """
    with _errores_de_dominio(db):
        servicio.anular_gasto(db, usuario_actual, gasto_id, payload.motivo)
    db.commit()
    return servicio.obtener_gasto(db, usuario_actual, gasto_id)
