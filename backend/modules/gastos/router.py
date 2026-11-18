"""Router del módulo Gastos (D-24, ADR-051).

Importar este router suscribe Gastos al evento `compra.pagada`: desde ese momento, pagar un
pedido en Compras lo anota como gasto del puesto. Si este módulo no carga, Compras sigue
cerrando pedidos igual (solo que la caja no lo descuenta).
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

import eventos
from database import obtener_sesion, obtener_sesion_escritura

from . import servicio
from .models import AmbitoGasto
from .schemas import GastoEntrada, GastoSalida, GastosDelDia, TotalesPorMedio

router = APIRouter(prefix="/api/gastos", tags=["gastos"])

eventos.suscribir("compra.pagada", "gastos.pago_de_pedido", servicio.al_pagar_pedido)


@router.post("", response_model=GastoSalida)
def registrar(datos: GastoEntrada, respuesta: Response, sesion: Session = Depends(obtener_sesion_escritura)):
    """Anota un gasto. Reenviar el mismo uuid devuelve el mismo gasto (200 en vez de 201)."""
    gasto, es_nuevo = servicio.registrar(sesion, datos)
    respuesta.status_code = status.HTTP_201_CREATED if es_nuevo else status.HTTP_200_OK
    return gasto


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
def anular(uuid: str, sesion: Session = Depends(obtener_sesion_escritura)) -> None:
    """Borra un gasto mal anotado (idempotente)."""
    servicio.anular(sesion, uuid)


@router.get("", response_model=GastosDelDia)
def del_dia(dia: date | None = Query(default=None), sesion: Session = Depends(obtener_sesion)):
    """Los gastos de un día peruano (hoy si no se indica), con totales por medio y por ámbito."""
    dia = dia or servicio.hoy()
    gastos = servicio.del_dia(sesion, dia)
    totales = servicio.total_por_medio(sesion, dia)
    return GastosDelDia(
        dia=dia,
        gastos=gastos,
        total=TotalesPorMedio(**totales),
        del_puesto=sum((g.monto for g in gastos if g.ambito == AmbitoGasto.PUESTO), Decimal("0.00")),
        del_hogar=sum((g.monto for g in gastos if g.ambito == AmbitoGasto.HOGAR), Decimal("0.00")),
    )
