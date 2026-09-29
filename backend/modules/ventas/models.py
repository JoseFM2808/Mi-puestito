"""Modelos del módulo Ventas (docs/03-modulos/Modulo-Ventas.md).

Tres tipos de venta: orden activa, fiado y venta rápida. Sin claves foráneas
hacia otros módulos y sin validación de stock (funciona sin Inventario).
La deuda de un cliente se DERIVA (Σ ventas fiadas − Σ abonos), no se duplica.
Fechas en UTC; la zona (America/Lima) se aplica solo al presentar.

Sincronización offline (ADR-032): todo lo que la tablet crea sin red lleva un
`uuid` generado en el dispositivo. Ese uuid es la identidad pública (la API
nunca expone el id entero) y también la clave de idempotencia: reenviar la
misma operación encuentra la fila existente en vez de duplicar la venta.
Dinero en céntimos enteros (tipo `Dinero`, ADR-035).
"""

import enum
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, Cantidad, Dinero, FechaHoraUTC
from fechas import ahora_utc


def nuevo_uuid() -> str:
    """uuid para filas creadas en el servidor (seed, tests); la API exige el del dispositivo."""
    return str(uuid4())


def _enum(clase):
    return Enum(clase, native_enum=False, values_callable=lambda e: [x.value for x in e])


class TipoVenta(str, enum.Enum):
    ORDEN_ACTIVA = "orden_activa"  # abierta durante el día, se cobra al cerrar
    FIADO = "fiado"                # cliente registrado que paga después
    VENTA_RAPIDA = "venta_rapida"  # solo monto, se formaliza después


class EstadoVenta(str, enum.Enum):
    ABIERTA = "abierta"                            # se siguen agregando productos
    PAGADA_CERRADA = "pagada_cerrada"              # cobrada: dinero en caja
    FIADA = "fiada"                                # entregada a crédito: suma a la deuda
    PENDIENTE_FORMALIZAR = "pendiente_formalizar"  # venta rápida cobrada, sin detalle aún


class MetodoPago(str, enum.Enum):
    EFECTIVO = "efectivo"
    YAPE_PLIN = "yape_plin"


class Cliente(Base):
    """Clientes con nombre (necesarios para fiado)."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=nuevo_uuid)
    # Se busca al cliente por nombre al registrar un fiado
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    # NULL = crédito libre (el default según la doc); un monto = límite opcional
    limite_credito: Mapped[Decimal | None] = mapped_column(Dinero)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
    # Datos maestros: se resuelven con "gana la última edición" (ADR-031)
    actualizado_en: Mapped[datetime] = mapped_column(
        FechaHoraUTC, default=ahora_utc, onupdate=ahora_utc
    )

    ventas: Mapped[list["Venta"]] = relationship(back_populates="cliente")
    pagos: Mapped[list["Pago"]] = relationship(back_populates="cliente")


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        # "Vendiste hoy" y el panel de órdenes abiertas filtran por estas dos
        Index("ix_ventas_estado_abierta_en", "estado", "abierta_en"),
        Index("ix_ventas_tipo_cliente", "tipo", "cliente_id"),
        Index("ix_ventas_estado_cerrada_en", "estado", "cerrada_en"),
        # Un fiado sin cliente no se podría cobrar nunca
        CheckConstraint(
            "tipo != 'fiado' OR cliente_id IS NOT NULL",
            name="ck_fiado_requiere_cliente",
        ),
        CheckConstraint("monto_total >= 0", name="ck_venta_monto_no_negativo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=nuevo_uuid)
    tipo: Mapped[TipoVenta] = mapped_column(_enum(TipoVenta))
    # Obligatorio solo para fiado; una orden activa puede ser anónima ("Orden 2")
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"))
    nombre_orden: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[EstadoVenta] = mapped_column(_enum(EstadoVenta), default=EstadoVenta.ABIERTA)
    # Orden activa y fiado: Σ items, lo calcula SIEMPRE el servidor (D-11).
    # Venta rápida: el monto cobrado; el detalle debe cuadrar al formalizar.
    monto_total: Mapped[Decimal] = mapped_column(Dinero, default=Decimal("0"))
    metodo_pago: Mapped[MetodoPago | None] = mapped_column(_enum(MetodoPago))
    abierta_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
    cerrada_en: Mapped[datetime | None] = mapped_column(FechaHoraUTC)

    cliente: Mapped[Cliente | None] = relationship(back_populates="ventas")
    # Al borrar una venta se van con ella sus items y sus pagos: si quedaran
    # sueltos, los totales del Dashboard contarían dinero inexistente
    items: Mapped[list["ItemVenta"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan", order_by="ItemVenta.id"
    )
    pagos: Mapped[list["Pago"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )


class ItemVenta(Base):
    """Detalle de una venta. La venta rápida no tiene items hasta formalizarse."""

    __tablename__ = "items_venta"
    __table_args__ = (CheckConstraint("monto >= 0", name="ck_item_venta_monto_no_negativo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=nuevo_uuid)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id", ondelete="CASCADE"), index=True)
    nombre_producto: Mapped[str] = mapped_column(String(120))
    # Texto libre; nullable: en granel sin inventario se digita el monto directo
    cantidad: Mapped[str | None] = mapped_column(String(60))
    monto: Mapped[Decimal] = mapped_column(Dinero)
    # Enlace OPCIONAL a Inventario por uuid, sin clave foránea: Ventas funciona
    # aunque Inventario no exista, y un producto creado sin red ya tiene uuid.
    # Si viene, cantidad_num es lo que se descuenta del stock.
    producto_uuid: Mapped[str | None] = mapped_column(String(36), index=True)
    cantidad_num: Mapped[Decimal | None] = mapped_column(Cantidad)

    venta: Mapped[Venta] = relationship(back_populates="items")


class Pago(Base):
    """Pagos y abonos. Un abono de fiado va a cuenta del cliente (cliente_id)
    sin estar atado a una venta puntual (venta_id NULL)."""

    __tablename__ = "pagos"
    __table_args__ = (
        # Un pago sin venta NI cliente sería dinero registrado a nadie, y
        # haría mentir a la deuda derivada
        CheckConstraint(
            "venta_id IS NOT NULL OR cliente_id IS NOT NULL",
            name="ck_pago_tiene_destino",
        ),
        CheckConstraint("monto > 0", name="ck_pago_monto_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=nuevo_uuid)
    venta_id: Mapped[int | None] = mapped_column(
        ForeignKey("ventas.id", ondelete="CASCADE"), index=True
    )
    # Indexado: la deuda de un cliente se calcula sumando sus abonos
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"), index=True)
    monto: Mapped[Decimal] = mapped_column(Dinero)
    metodo_pago: Mapped[MetodoPago] = mapped_column(_enum(MetodoPago), default=MetodoPago.EFECTIVO)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)

    venta: Mapped[Venta | None] = relationship(back_populates="pagos")
    cliente: Mapped[Cliente | None] = relationship(back_populates="pagos")
