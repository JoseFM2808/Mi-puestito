"""Modelos del módulo Inventario (docs/03-modulos/Modulo-Inventario.md, ADR-031).

El stock NO es un número que se sobreescribe: es la suma de un libro de
movimientos que solo crece (+ compra, − venta, ± ajuste). Así:

- dos ventas simultáneas nunca se pisan (cada una inserta su propio delta),
- la sincronización offline puede aplicar movimientos en cualquier orden y
  el total es el mismo (son conmutativos),
- reenviar una operación no descuenta dos veces: `(origen_tipo, origen_ref)`
  es único.

`productos.stock_actual` es una caché de Σ movimientos que se actualiza con un
incremento atómico en la misma transacción; `conciliar()` la verifica.
Ventas y Compras no tienen clave foránea hacia aquí: funcionan sin Inventario.
"""

import enum
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, Cantidad, Dinero, FechaHoraUTC
from fechas import ahora_utc


def _enum(clase):
    return Enum(clase, native_enum=False, values_callable=lambda e: [x.value for x in e])


class Unidad(str, enum.Enum):
    UNIDAD = "unidad"
    KG = "kg"
    LITRO = "litro"


class MotivoMovimiento(str, enum.Enum):
    VENTA = "venta"                        # − al registrar un item vendido
    ANULACION_VENTA = "anulacion_venta"    # + al quitar un item de una orden abierta
    COMPRA = "compra"                      # + al recibir un pedido
    AJUSTE = "ajuste"                      # ± conteo físico (contado − calculado)
    MERMA = "merma"                        # − vencido, dañado, regalado


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    # Nombre único del producto en el sistema (Modulo-Compras lo exige)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    codigo_barras: Mapped[str | None] = mapped_column(String(32), unique=True)
    unidad: Mapped[Unidad] = mapped_column(_enum(Unidad), default=Unidad.UNIDAD)
    precio_venta: Mapped[Decimal | None] = mapped_column(Dinero)
    stock_actual: Mapped[Decimal] = mapped_column(Cantidad, default=Decimal("0"))
    # Debajo de esto, el sistema sugiere pedirlo al proveedor
    stock_minimo: Mapped[Decimal | None] = mapped_column(Cantidad)
    tiene_vencimiento: Mapped[bool] = mapped_column(default=False)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
    actualizado_en: Mapped[datetime] = mapped_column(
        FechaHoraUTC, default=ahora_utc, onupdate=ahora_utc
    )

    movimientos: Mapped[list["MovimientoInventario"]] = relationship(back_populates="producto")


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        # Idempotencia: el mismo item vendido (o ajuste, o recepción) nunca
        # mueve el stock dos veces aunque la tablet reenvíe la operación
        UniqueConstraint("origen_tipo", "origen_ref", name="uq_movimiento_origen"),
        CheckConstraint("delta != 0", name="ck_movimiento_delta_no_cero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), index=True)
    delta: Mapped[Decimal] = mapped_column(Cantidad)
    motivo: Mapped[MotivoMovimiento] = mapped_column(_enum(MotivoMovimiento))
    # De dónde viene: "item_venta", "ajuste", "recepcion"… + el uuid del origen
    origen_tipo: Mapped[str] = mapped_column(String(40))
    origen_ref: Mapped[str] = mapped_column(String(36))
    nota: Mapped[str | None] = mapped_column(String(200))
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, index=True)

    producto: Mapped[Producto] = relationship(back_populates="movimientos")
