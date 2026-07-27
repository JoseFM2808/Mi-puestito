"""Contrato del resumen del Dashboard / Caja Diaria.

Espejo tipado de lo que consume el frontend
(frontend/src/modules/dashboard/datos-ficticios.ts).
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class OrdenActivaResumen(BaseModel):
    id: int
    nombre: str
    tipo: str  # "orden_activa" | "fiado"
    monto: Decimal
    deuda_cliente: Decimal | None = None


class PedidoPorLlegar(BaseModel):
    id: int
    proveedor: str
    fecha_estimada: date
    monto: Decimal


class ResumenDashboard(BaseModel):
    ventas_hoy: Decimal
    ventas_cerradas: int
    proyeccion_manana: Decimal
    motivo_proyeccion: str
    ordenes_activas: list[OrdenActivaResumen]
    fiados_por_cobrar: Decimal
    clientes_con_fiado: int
    ventas_rapidas_pendientes: int
    pedidos_por_llegar: list[PedidoPorLlegar]
