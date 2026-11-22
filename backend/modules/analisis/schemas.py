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


class GananciaPorCategoria(BaseModel):
    """La misma cuenta que por producto, sumada por categoría ("Sin categoría" si no tiene)."""

    categoria: str
    vendido: Decimal
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
    por_categoria: list[GananciaPorCategoria] = []
    # Partes que no se pudieron calcular: el análisis las dice con palabras
    no_disponibles: list[str] = []


class KardexProducto(BaseModel):
    """Cómo se movió un producto en el mes, en su unidad (kg, litro o unidades)."""

    nombre: str
    unidad: str
    inicial: Decimal  # lo que había al empezar el mes
    registrado: Decimal  # + lo que había al registrar el producto, si se registró en el mes
    compras: Decimal  # + pedidos recibidos
    vendido: Decimal  # − ventas (ya descontado lo que se quitó de una orden)
    mermas: Decimal  # − vencido, dañado, regalado
    ajustes: Decimal  # ± conteos
    final: Decimal  # inicial + registrado + compras − vendido − mermas + ajustes


class KardexDelMes(BaseModel):
    """Kardex mensual del inventario (Modulo-Analisis): entradas y salidas de cada producto."""

    mes: str  # "2026-11"
    desde: date
    hasta: date
    productos: list[KardexProducto]
    no_disponibles: list[str] = []
