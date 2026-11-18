"""Modelos del módulo Gastos (docs/03-modulos/Modulo-Gastos.md, D-24, ADR-051).

Un gasto es dinero que SALE de la caja: de la gaveta (efectivo) o del Yape. Puede ser del
puesto (alquiler, transporte, pagar un pedido al proveedor) o del hogar (comida, colegio):
separarlos es lo que deja ver si el negocio gana o si la casa se lo está comiendo.

Ventas y Compras no tienen clave foránea hacia aquí. El pago de un pedido llega por el evento
`compra.pagada` y es idempotente por `orden_compra_uuid`: pagar el mismo pedido dos veces
(la cola offline reenvía) no descuenta dos veces.
"""

import enum
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, Dinero, FechaHoraUTC
from fechas import ahora_utc


def _enum(clase, nombre):
    return Enum(clase, name=nombre, native_enum=False, values_callable=lambda e: [x.value for x in e])


class MedioDePago(str, enum.Enum):
    """De dónde sale el dinero. Los mismos valores que Ventas, sin depender de su módulo."""

    EFECTIVO = "efectivo"
    YAPE_PLIN = "yape_plin"


class AmbitoGasto(str, enum.Enum):
    PUESTO = "puesto"
    HOGAR = "hogar"


class CategoriaGasto(str, enum.Enum):
    PROVEEDOR = "proveedor"  # pagar un pedido de mercadería
    ALQUILER = "alquiler"
    SERVICIOS = "servicios"  # luz, agua, internet
    TRANSPORTE = "transporte"
    ALIMENTACION = "alimentacion"
    EDUCACION = "educacion"
    OTROS = "otros"


class Gasto(Base):
    __tablename__ = "gastos"
    __table_args__ = (CheckConstraint("monto > 0", name="ck_gasto_monto_positivo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    monto: Mapped[Decimal] = mapped_column(Dinero)
    medio: Mapped[MedioDePago] = mapped_column(_enum(MedioDePago, "mediodepago"))
    ambito: Mapped[AmbitoGasto] = mapped_column(_enum(AmbitoGasto, "ambitogasto"))
    categoria: Mapped[CategoriaGasto] = mapped_column(_enum(CategoriaGasto, "categoriagasto"))
    descripcion: Mapped[str | None] = mapped_column(String(120))
    # Solo para el pago de un pedido: un pedido se paga una vez (idempotencia de la cola)
    orden_compra_uuid: Mapped[str | None] = mapped_column(String(36), unique=True)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, index=True)
