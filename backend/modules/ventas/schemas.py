"""Esquemas Pydantic del módulo Ventas.

Contrato de dinero (ADR-033): los montos viajan como string decimal
("485.50"), nunca como float. Identidad pública: `uuid` (ADR-032); el id
entero es interno y no sale de la API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .models import EstadoVenta, MetodoPago, TipoVenta

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
MontoPositivo = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
MontoNoNegativo = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class _Operacion(BaseModel):
    """Base de toda escritura: la hora en que ocurrió en el dispositivo.

    Sin red la operación se envía después; `ocurrido_en` conserva la hora
    real. El usuario nunca la escribe: la pone la app.
    """

    ocurrido_en: datetime | None = None


# ---- Clientes ----

class ClienteEntrada(_Operacion):
    uuid: Uuid
    nombre: Texto
    telefono: Annotated[str, StringConstraints(max_length=20)] | None = None
    limite_credito: MontoPositivo | None = None


class ClienteCambios(BaseModel):
    nombre: Texto | None = None
    telefono: Annotated[str, StringConstraints(max_length=20)] | None = None
    limite_credito: MontoPositivo | None = None
    quitar_limite: bool = False


class ClienteSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    nombre: str
    telefono: str | None
    limite_credito: Decimal | None
    creado_en: datetime


class ClienteConDeuda(ClienteSalida):
    deuda: Decimal


# ---- Ventas ----

class VentaEntrada(_Operacion):
    uuid: Uuid
    tipo: TipoVenta
    cliente_uuid: Uuid | None = None
    nombre_orden: Texto | None = None
    # Solo venta rápida: el monto cobrado y cómo se cobró
    monto: MontoPositivo | None = None
    metodo_pago: MetodoPago | None = None


class ItemEntrada(_Operacion):
    uuid: Uuid
    nombre_producto: Texto
    cantidad: Annotated[str, StringConstraints(max_length=60)] | None = None
    monto: MontoNoNegativo
    # Opcional: si Inventario está activo, se descuenta cantidad_num del stock
    producto_uuid: Uuid | None = None
    cantidad_num: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)] | None = None


class CobroEntrada(_Operacion):
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO


class FiarEntrada(_Operacion):
    # Una orden activa se puede "apuntar" a un cliente al final ("fíamelo")
    cliente_uuid: Uuid | None = None


class AbonoEntrada(_Operacion):
    uuid: Uuid
    cliente_uuid: Uuid
    monto: MontoPositivo
    metodo_pago: MetodoPago = MetodoPago.EFECTIVO


class ItemVentaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    nombre_producto: str
    cantidad: str | None
    monto: Decimal
    producto_uuid: str | None
    cantidad_num: Decimal | None


class VentaSalida(BaseModel):
    uuid: str
    tipo: TipoVenta
    cliente_uuid: str | None
    cliente_nombre: str | None
    nombre_orden: str | None
    estado: EstadoVenta
    monto_total: Decimal
    metodo_pago: MetodoPago | None
    abierta_en: datetime
    cerrada_en: datetime | None
    items: list[ItemVentaSalida]
    # Solo fiado: cuánto debe el cliente en total (derivado, nunca guardado)
    deuda_cliente: Decimal | None = None


class ResultadoVenta(BaseModel):
    """Respuesta de toda operación de escritura sobre una venta."""

    venta: VentaSalida
    # Avisos en lenguaje simple: límite de crédito, stock que quedó negativo…
    avisos: list[str] = []


class AbonoSalida(BaseModel):
    uuid: str
    cliente_uuid: str
    monto: Decimal
    metodo_pago: MetodoPago
    creado_en: datetime
    deuda_restante: Decimal
    avisos: list[str] = []
