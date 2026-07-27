"""Esquemas Pydantic del módulo Ventas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .models import EstadoVenta, MetodoPago, TipoVenta


class ClienteSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    telefono: str | None
    limite_credito: Decimal | None
    creado_en: datetime


class ItemVentaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_producto: str
    cantidad: str | None
    monto: Decimal


class VentaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoVenta
    cliente_id: int | None
    nombre_orden: str | None
    estado: EstadoVenta
    monto_total: Decimal
    metodo_pago: MetodoPago | None
    abierta_en: datetime
    cerrada_en: datetime | None
    items: list[ItemVentaSalida]
