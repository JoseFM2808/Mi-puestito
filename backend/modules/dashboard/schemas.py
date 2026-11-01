"""Contrato del resumen del Dashboard / Caja Diaria.

El frontend lo consume a través de `frontend/src/api/contrato.ts` (ADR-033):
montos como string decimal, nombres en snake_case.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class OrdenActivaResumen(BaseModel):
    uuid: str
    nombre: str
    tipo: str  # "orden_activa" | "fiado"
    monto: Decimal
    deuda_cliente: Decimal | None = None


class PedidoPorLlegar(BaseModel):
    uuid: str
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
    # Módulos que no pudieron leerse: su parte sale en cero y se avisa
    secciones_no_disponibles: list[str] = []
