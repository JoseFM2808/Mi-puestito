"""Modelos del módulo Caja (D-24, ADR-051).

La caja de cada día empieza con lo que hay al abrir: un saldo en efectivo (la gaveta) y otro
en Yape (decisión del owner, 2026-11-17). Una apertura por día peruano: abrir otra vez el
mismo día corrige los saldos ("me equivoqué al contar"), no crea una segunda caja.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, Dinero, FechaHoraUTC
from fechas import ahora_utc


class AperturaCaja(Base):
    __tablename__ = "aperturas_caja"
    __table_args__ = (
        CheckConstraint("efectivo_inicial >= 0", name="ck_apertura_efectivo_no_negativo"),
        CheckConstraint("yape_inicial >= 0", name="ck_apertura_yape_no_negativo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    dia: Mapped[date] = mapped_column(Date, unique=True)
    efectivo_inicial: Mapped[Decimal] = mapped_column(Dinero)
    yape_inicial: Mapped[Decimal] = mapped_column(Dinero)
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
    actualizado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc, onupdate=ahora_utc)
