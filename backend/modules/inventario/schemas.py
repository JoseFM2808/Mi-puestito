"""Esquemas del módulo Inventario. Cantidades con 3 decimales (kg), dinero como string."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .models import MotivoMovimiento, Unidad

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
CantidadPositiva = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
CantidadNoNegativa = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=3)]
Precio = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class ProductoEntrada(BaseModel):
    uuid: Uuid
    nombre: Texto
    unidad: Unidad = Unidad.UNIDAD
    precio_venta: Precio | None = None
    stock_minimo: CantidadNoNegativa | None = None
    stock_inicial: CantidadNoNegativa | None = None
    codigo_barras: Annotated[str, StringConstraints(max_length=32)] | None = None
    tiene_vencimiento: bool = False
    ocurrido_en: datetime | None = None


class ProductoCambios(BaseModel):
    nombre: Texto | None = None
    precio_venta: Precio | None = None
    stock_minimo: CantidadNoNegativa | None = None
    codigo_barras: Annotated[str, StringConstraints(max_length=32)] | None = None
    tiene_vencimiento: bool | None = None


class ProductoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    nombre: str
    unidad: Unidad
    precio_venta: Decimal | None
    stock_actual: Decimal
    stock_minimo: Decimal | None
    codigo_barras: str | None
    tiene_vencimiento: bool


class ProductoConEstado(ProductoSalida):
    # Se dice con palabras, no solo con color (Design-System §1)
    bajo_minimo: bool
    descuadre: bool


class AjusteEntrada(BaseModel):
    """Conteo físico: el operador dice cuánto HAY, no cuánto sumar o restar."""

    uuid: Uuid
    producto_uuid: Uuid
    contado: CantidadNoNegativa
    nota: Annotated[str, StringConstraints(max_length=200)] | None = None
    ocurrido_en: datetime | None = None


class MermaEntrada(BaseModel):
    uuid: Uuid
    producto_uuid: Uuid
    cantidad: CantidadPositiva
    nota: Annotated[str, StringConstraints(max_length=200)] | None = None
    ocurrido_en: datetime | None = None


class AjusteSalida(BaseModel):
    producto: ProductoSalida
    diferencia: Decimal


class MovimientoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    delta: Decimal
    motivo: MotivoMovimiento
    origen_tipo: str
    nota: str | None
    creado_en: datetime


class Descuadre(BaseModel):
    producto: ProductoSalida
    stock_segun_movimientos: Decimal
