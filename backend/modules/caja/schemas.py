"""Esquemas del módulo Caja. Montos como string decimal (ADR-033)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
MontoNoNegativo = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class AperturaEntrada(BaseModel):
    uuid: Uuid
    efectivo_inicial: MontoNoNegativo
    yape_inicial: MontoNoNegativo
    # La hora real en el dispositivo: define a qué día pertenece la apertura
    ocurrido_en: datetime | None = None


class SaldoPorMedio(BaseModel):
    efectivo: Decimal
    yape_plin: Decimal


class CajaDelDia(BaseModel):
    dia: date
    abierta: bool
    inicial: SaldoPorMedio
    # Lo que entró: ventas cobradas y abonos de fiado, por medio de pago
    ingresos: SaldoPorMedio
    # Lo que salió: gastos del puesto y del hogar, incluidos los pagos a proveedores
    egresos: SaldoPorMedio
    # inicial + ingresos − egresos
    en_caja: SaldoPorMedio
    # Partes que no se pudieron calcular (un módulo caído): la caja las dice con palabras
    no_disponibles: list[str] = []
