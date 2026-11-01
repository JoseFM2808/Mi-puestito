"""Esquemas Pydantic del módulo Compras y Proveedores.

Mismo contrato que Ventas: dinero como string decimal (ADR-033) e identidad
pública por `uuid` generado en el dispositivo (ADR-032); el id entero es interno.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .models import EstadoOrdenCompra, EstadoRecepcion

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
MontoPositivo = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
MontoNoNegativo = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
CantidadPositiva = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]


class _Operacion(BaseModel):
    """Hora real en el dispositivo: sin red, la operación se envía después."""

    ocurrido_en: datetime | None = None


# ---- Proveedores ----

class ProveedorEntrada(_Operacion):
    uuid: Uuid
    nombre: Texto
    empresa: Texto | None = None
    # 11 dígitos o nada: es opcional, y un RUC mal escrito rompería la búsqueda
    ruc: Annotated[str, StringConstraints(pattern=r"^\d{11}$")] | None = None
    telefono: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = None
    categoria: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None


class ProveedorSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    nombre: str
    empresa: str | None
    ruc: str | None
    telefono: str | None
    categoria: str | None
    creado_en: datetime


class ProductoFrecuente(BaseModel):
    """Lo que se le suele pedir a un proveedor, con la cantidad y el monto de la última vez."""

    nombre_producto: str
    cantidad: str | None
    monto: Decimal
    veces: int


# ---- Órdenes ----

class ItemOrdenEntrada(BaseModel):
    uuid: Uuid
    nombre_producto: Texto
    cantidad: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None
    monto: MontoPositivo


class OrdenEntrada(_Operacion):
    uuid: Uuid
    proveedor_uuid: Uuid
    # Solo se crea como borrador o pendiente: lo demás ocurre después
    estado: Literal["borrador", "pendiente"] = "pendiente"
    fecha_estimada_llegada: date | None = None
    notas: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    items: Annotated[list[ItemOrdenEntrada], Field(min_length=1, max_length=100)]


class CambioEstadoEntrada(_Operacion):
    estado: Literal["pendiente", "en_camino"]


class ItemRecepcionEntrada(BaseModel):
    item_uuid: Uuid
    # "pendiente" = dejarlo para después: la orden sigue esperando ese producto
    estado: EstadoRecepcion
    producto_sustituto: Texto | None = None
    monto_sustituto: MontoNoNegativo | None = None
    # Cuánto entra al stock, si ese producto se lleva en Inventario
    cantidad_stock: CantidadPositiva | None = None

    @model_validator(mode="after")
    def _cambio_completo(self):
        if self.estado == EstadoRecepcion.CAMBIADO and (
            self.producto_sustituto is None or self.monto_sustituto is None
        ):
            raise ValueError("Un cambio de producto necesita el sustituto y su monto")
        if self.estado != EstadoRecepcion.CAMBIADO and (
            self.producto_sustituto is not None or self.monto_sustituto is not None
        ):
            raise ValueError("El sustituto solo aplica a un cambio de producto")
        return self


class RecepcionEntrada(_Operacion):
    items: Annotated[list[ItemRecepcionEntrada], Field(min_length=1, max_length=100)]


class ItemOrdenCompraSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    nombre_producto: str
    cantidad: str | None
    monto: Decimal
    estado_recepcion: EstadoRecepcion
    producto_sustituto: str | None
    monto_sustituto: Decimal | None


class OrdenCompraSalida(BaseModel):
    uuid: str
    proveedor_uuid: str
    proveedor: str
    proveedor_telefono: str | None
    estado: EstadoOrdenCompra
    fecha_estimada_llegada: date | None
    monto_total: Decimal
    monto_real: Decimal | None
    notas: str | None
    items: list[ItemOrdenCompraSalida]


class ResultadoOrden(BaseModel):
    orden: OrdenCompraSalida
    # Mensajes para el operador, por ejemplo de Inventario ("no se sumó al stock")
    avisos: list[str] = []
