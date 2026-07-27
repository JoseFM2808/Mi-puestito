"""Modelos del módulo Compras y Proveedores (docs/03-modulos/Modulo-Compras.md).

Sin claves foráneas hacia otros módulos: cada módulo es independiente.
Fechas en UTC; la zona (America/Lima) se aplica solo al presentar.
"""

import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, FechaHoraUTC


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class EstadoOrdenCompra(str, enum.Enum):
    """Ciclo de vida: Borrador → Pendiente → En camino → Recibida → Cerrada."""

    BORRADOR = "borrador"
    PENDIENTE = "pendiente"
    EN_CAMINO = "en_camino"
    RECIBIDA = "recibida"
    CERRADA = "cerrada"


class EstadoRecepcion(str, enum.Enum):
    """Checklist de recepción: recibido / no recibido / cambio de producto."""

    PENDIENTE = "pendiente"
    RECIBIDO = "recibido"
    NO_RECIBIDO = "no_recibido"
    CAMBIADO = "cambiado"


class Proveedor(Base):
    """El proveedor puede registrarse a sí mismo desde la tablet."""

    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Se busca al proveedor por nombre, empresa o RUC
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    empresa: Mapped[str | None] = mapped_column(String(120), index=True)
    # Único: el RUC identifica a la empresa ante SUNAT. Sin esto, el mismo
    # proveedor se registra dos veces al pasarle la tablet.
    ruc: Mapped[str | None] = mapped_column(String(11), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    categoria: Mapped[str | None] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)

    ordenes: Mapped[list["OrdenCompra"]] = relationship(back_populates="proveedor")


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"
    __table_args__ = (
        # La proyección "Mañana necesitas en caja" filtra por estas dos
        Index("ix_ordenes_estado_llegada", "estado", "fecha_estimada_llegada"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"), index=True)
    estado: Mapped[EstadoOrdenCompra] = mapped_column(
        Enum(EstadoOrdenCompra, native_enum=False, values_callable=lambda e: [x.value for x in e]),
        default=EstadoOrdenCompra.BORRADOR,
    )
    # Alimenta la proyección "Mañana necesitas en caja" del Dashboard
    fecha_estimada_llegada: Mapped[date | None] = mapped_column(Date)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    # Recalculado tras el checklist según lo efectivamente recibido
    monto_real: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notas: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
    actualizado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, onupdate=ahora_utc)

    proveedor: Mapped[Proveedor] = relationship(back_populates="ordenes")
    # Los items no sobreviven a su orden: quedarían sin monto al que pertenecer
    items: Mapped[list["ItemOrdenCompra"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan"
    )


class ItemOrdenCompra(Base):
    __tablename__ = "items_orden_compra"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_compra_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes_compra.id", ondelete="CASCADE"), index=True
    )
    # Nombre único del producto en el sistema; en esta fase se registra
    # monto total por ítem, no precio unitario
    nombre_producto: Mapped[str] = mapped_column(String(120))
    cantidad: Mapped[str | None] = mapped_column(String(60))  # texto libre: "2 packs"
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    estado_recepcion: Mapped[EstadoRecepcion] = mapped_column(
        Enum(EstadoRecepcion, native_enum=False, values_callable=lambda e: [x.value for x in e]),
        default=EstadoRecepcion.PENDIENTE,
    )
    producto_sustituto: Mapped[str | None] = mapped_column(String(120))
    monto_sustituto: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    orden: Mapped[OrdenCompra] = relationship(back_populates="items")
