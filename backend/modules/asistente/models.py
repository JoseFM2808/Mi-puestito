"""Modelos del Asistente: lo que recuerda del negocio (D-26, ADR-052).

Hechos cortos que el operador le contó y sirven para después ("la Sra. Rosa paga por Yape",
"los sábados vendo menú"). Viven en la base del proyecto, en la computadora del vendedor; hacia el
proveedor de IA viajan seudonimizados como todo lo demás (ADR-034). El operador los ve y los
puede olvidar uno por uno.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, FechaHoraUTC
from fechas import ahora_utc


class MemoriaAsistente(Base):
    __tablename__ = "memorias_asistente"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    texto: Mapped[str] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(FechaHoraUTC, default=ahora_utc)
