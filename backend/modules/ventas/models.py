"""Modelos del módulo Ventas (docs/03-modulos/Modulo-Ventas.md).

Tres tipos de venta: orden activa, fiado y venta rápida. Sin claves foráneas
hacia otros módulos y sin validación de stock (funciona sin Inventario).
La deuda de un cliente se DERIVA (Σ ventas fiado − Σ pagos), no se duplica.
Fechas en UTC; la zona (America/Lima) se aplica solo al presentar.
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, FechaHoraUTC


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class TipoVenta(str, enum.Enum):
    ORDEN_ACTIVA = "orden_activa"  # abierta durante el día, se cobra al cerrar
    FIADO = "fiado"                # cliente registrado que paga después
    VENTA_RAPIDA = "venta_rapida"  # solo monto, se formaliza después


class EstadoVenta(str, enum.Enum):
    ABIERTA = "abierta"
    PAGADA_CERRADA = "pagada_cerrada"
    PENDIENTE_FORMALIZAR = "pendiente_formalizar"  # venta rápida sin detalle aún


class MetodoPago(str, enum.Enum):
    EFECTIVO = "efectivo"
    YAPE_PLIN = "yape_plin"


class Cliente(Base):
    """Clientes con nombre (necesarios para fiado)."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Se busca al cliente por nombre al registrar un fiado
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    # NULL = crédito libre (el default según la doc); un monto = límite opcional
    limite_credito: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)

    ventas: Mapped[list["Venta"]] = relationship(back_populates="cliente")
    pagos: Mapped[list["Pago"]] = relationship(back_populates="cliente")


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        # "Vendiste hoy" y el panel de órdenes abiertas filtran por estas dos
        Index("ix_ventas_estado_abierta_en", "estado", "abierta_en"),
        Index("ix_ventas_tipo_cliente", "tipo", "cliente_id"),
        # Un fiado sin cliente no se podría cobrar nunca
        CheckConstraint(
            "tipo != 'fiado' OR cliente_id IS NOT NULL",
            name="ck_fiado_requiere_cliente",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoVenta] = mapped_column(
        Enum(TipoVenta, native_enum=False, values_callable=lambda e: [x.value for x in e]),
    )
    # Obligatorio solo para fiado; una orden activa puede ser anónima ("Orden 2")
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"))
    nombre_orden: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[EstadoVenta] = mapped_column(
        Enum(EstadoVenta, native_enum=False, values_callable=lambda e: [x.value for x in e]),
        default=EstadoVenta.ABIERTA,
    )
    monto_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    metodo_pago: Mapped[MetodoPago | None] = mapped_column(
        Enum(MetodoPago, native_enum=False, values_callable=lambda e: [x.value for x in e]),
    )
    abierta_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
    cerrada_en: Mapped[datetime | None] = mapped_column(FechaHoraUTC)

    cliente: Mapped[Cliente | None] = relationship(back_populates="ventas")
    # Al borrar una venta se van con ella sus items y sus pagos: si quedaran
    # sueltos, los totales del Dashboard contarían dinero inexistente
    items: Mapped[list["ItemVenta"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )
    pagos: Mapped[list["Pago"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )


class ItemVenta(Base):
    """Detalle de una venta. La venta rápida no tiene items hasta formalizarse."""

    __tablename__ = "items_venta"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id", ondelete="CASCADE"), index=True)
    nombre_producto: Mapped[str] = mapped_column(String(120))
    # Texto libre; nullable: en granel sin inventario se digita el monto directo
    cantidad: Mapped[str | None] = mapped_column(String(60))
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    venta: Mapped[Venta] = relationship(back_populates="items")


class Pago(Base):
    """Pagos y abonos. Un abono de fiado puede ir a cuenta del cliente
    (cliente_id) sin estar atado a una venta puntual (venta_id)."""

    __tablename__ = "pagos"
    __table_args__ = (
        # Un pago sin venta NI cliente sería dinero registrado a nadie, y
        # haría mentir a la deuda derivada
        CheckConstraint(
            "venta_id IS NOT NULL OR cliente_id IS NOT NULL",
            name="ck_pago_tiene_destino",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int | None] = mapped_column(
        ForeignKey("ventas.id", ondelete="CASCADE"), index=True
    )
    # Indexado: la deuda de un cliente se calcula sumando sus pagos
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"), index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    metodo_pago: Mapped[MetodoPago] = mapped_column(
        Enum(MetodoPago, native_enum=False, values_callable=lambda e: [x.value for x in e]),
        default=MetodoPago.EFECTIVO,
    )
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)

    venta: Mapped[Venta | None] = relationship(back_populates="pagos")
    cliente: Mapped[Cliente | None] = relationship(back_populates="pagos")
