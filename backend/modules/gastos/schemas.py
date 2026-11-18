"""Esquemas del módulo Gastos. Montos como string decimal (ADR-033); identidad por uuid (ADR-032)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .models import AmbitoGasto, CategoriaGasto, MedioDePago

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
MontoPositivo = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


class GastoEntrada(BaseModel):
    uuid: Uuid
    monto: MontoPositivo
    medio: MedioDePago
    ambito: AmbitoGasto = AmbitoGasto.PUESTO
    categoria: CategoriaGasto = CategoriaGasto.OTROS
    descripcion: Descripcion | None = None
    # La hora real en el dispositivo (sin red se envía después); la pone la app
    ocurrido_en: datetime | None = None


class GastoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    monto: Decimal
    medio: MedioDePago
    ambito: AmbitoGasto
    categoria: CategoriaGasto
    descripcion: str | None
    orden_compra_uuid: str | None
    creado_en: datetime


class TotalesPorMedio(BaseModel):
    efectivo: Decimal
    yape_plin: Decimal


class GastosDelDia(BaseModel):
    dia: date
    gastos: list[GastoSalida]
    total: TotalesPorMedio
    # Cuánto fue del puesto y cuánto del hogar: separa el negocio de la casa
    del_puesto: Decimal
    del_hogar: Decimal
