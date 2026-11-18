"""Reglas del módulo Gastos (D-24, ADR-051).

- Idempotente por `uuid`: la cola offline puede reenviar; reenviar no duplica.
- Un gasto es un hecho: no se rechaza aunque deje la caja en negativo (la Caja lo avisa).
- Anular un gasto mal anotado lo borra: no movió stock ni deuda, solo la caja.
- El pago de un pedido (`compra.pagada`) se vuelve un gasto del puesto, una sola vez por pedido.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fechas import dia_peruano, momento_de_operacion, rango_utc_del_dia

from .models import AmbitoGasto, CategoriaGasto, Gasto, MedioDePago
from .schemas import GastoEntrada

CERO = Decimal("0.00")


def registrar(sesion: Session, datos: GastoEntrada) -> tuple[Gasto, bool]:
    """Anota un gasto. Devuelve (gasto, es_nuevo)."""
    existente = sesion.scalar(select(Gasto).where(Gasto.uuid == datos.uuid))
    if existente is not None:
        return existente, False
    gasto = Gasto(
        uuid=datos.uuid,
        monto=datos.monto,
        medio=datos.medio,
        ambito=datos.ambito,
        categoria=datos.categoria,
        descripcion=datos.descripcion or None,
        creado_en=momento_de_operacion(datos.ocurrido_en),
    )
    sesion.add(gasto)
    sesion.commit()
    return gasto, True


def anular(sesion: Session, uuid: str) -> None:
    """Borra un gasto mal anotado. Anular dos veces no hace nada."""
    gasto = sesion.scalar(select(Gasto).where(Gasto.uuid == uuid))
    if gasto is not None:
        sesion.delete(gasto)
        sesion.commit()


def del_dia(sesion: Session, dia: date) -> list[Gasto]:
    desde, hasta = rango_utc_del_dia(dia)
    return list(
        sesion.scalars(
            select(Gasto).where(Gasto.creado_en >= desde, Gasto.creado_en < hasta).order_by(Gasto.creado_en)
        )
    )


def total_por_medio(sesion: Session, dia: date) -> dict[str, Decimal]:
    """Lo que salió ese día, por medio de pago. Lo usa la Caja (sin importar este módulo)."""
    desde, hasta = rango_utc_del_dia(dia)
    filas = sesion.execute(
        select(Gasto.medio, func.coalesce(func.sum(Gasto.monto), 0))
        .where(Gasto.creado_en >= desde, Gasto.creado_en < hasta)
        .group_by(Gasto.medio)
    ).all()
    totales = {medio.value: CERO for medio in MedioDePago}
    for medio, monto in filas:
        totales[MedioDePago(medio).value] = Decimal(monto)
    return totales


def al_pagar_pedido(sesion: Session, datos: dict) -> list[str] | None:
    """Suscriptor de "compra.pagada": lo pagado al proveedor sale de la caja.

    `datos`: orden_uuid, proveedor, monto (Decimal), medio ("efectivo" | "yape_plin"), ocurrido_en.
    Sin medio (una versión anterior de la app cerraba sin preguntar) no se anota nada.
    """
    if not datos.get("medio") or not datos.get("monto") or Decimal(datos["monto"]) <= 0:
        return None
    if sesion.scalar(select(Gasto.id).where(Gasto.orden_compra_uuid == datos["orden_uuid"])):
        return None
    sesion.add(
        Gasto(
            monto=Decimal(datos["monto"]),
            medio=MedioDePago(datos["medio"]),
            ambito=AmbitoGasto.PUESTO,
            categoria=CategoriaGasto.PROVEEDOR,
            descripcion=f"Pedido de {datos.get('proveedor') or 'proveedor'}"[:120],
            orden_compra_uuid=datos["orden_uuid"],
            creado_en=momento_de_operacion(datos.get("ocurrido_en")),
        )
    )
    return None


def hoy() -> date:
    return dia_peruano()
