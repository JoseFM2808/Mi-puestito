"""Esquemas Pydantic del módulo Compras y Proveedores."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from .models import EstadoOrdenCompra, EstadoRecepcion


class ProveedorSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    empresa: str | None
    ruc: str | None
    telefono: str | None
    categoria: str | None
    creado_en: datetime


class ItemOrdenCompraSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_producto: str
    cantidad: str | None
    monto: Decimal
    estado_recepcion: EstadoRecepcion
    producto_sustituto: str | None
    monto_sustituto: Decimal | None


class OrdenCompraSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proveedor_id: int
    estado: EstadoOrdenCompra
    fecha_estimada_llegada: date | None
    monto_total: Decimal
    monto_real: Decimal | None
    notas: str | None
    items: list[ItemOrdenCompraSalida]
