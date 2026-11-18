"""Esquemas del módulo Análisis (Fase 7). Montos como string decimal (ADR-033)."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Periodo = Literal["semana", "mes", "mes_pasado"]


class DiaDelPeriodo(BaseModel):
    dia: date
    vendido: Decimal
    gastado: Decimal  # gastos del puesto + de la casa + pagos a proveedores


class GananciaPorProducto(BaseModel):
    nombre: str
    vendido: Decimal
    # Estimado: lo vendido menos la cantidad × el costo de la última compra (D-22)
    ganancia_estimada: Decimal


class AnalisisDelPeriodo(BaseModel):
    periodo: Periodo
    desde: date
    hasta: date
    # Lo cobrado en ventas (como "Vendiste hoy", pero de todo el período)
    vendido: Decimal
    ventas: int
    pagado_a_proveedores: Decimal
    gastos_del_puesto: Decimal
    gastos_de_la_casa: Decimal
    # vendido − proveedores − gastos del puesto: lo que dejó el negocio
    resultado_del_negocio: Decimal
    # resultado del negocio − gastos de la casa: lo que quedó libre
    libre: Decimal
    fiados_por_cobrar: Decimal
    por_dia: list[DiaDelPeriodo]
    mejores_productos: list[GananciaPorProducto]
    # Partes que no se pudieron calcular: el análisis las dice con palabras
    no_disponibles: list[str] = []
