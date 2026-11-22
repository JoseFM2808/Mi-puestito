"""Esquemas del Asistente."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class TurnoPrevio(BaseModel):
    """Un mensaje anterior de la conversación, para que el Asistente tenga memoria."""

    rol: Literal["operador", "asistente"]
    # Se recorta en vez de rechazar: una respuesta larga del Asistente no debe
    # impedir hacer la siguiente pregunta
    texto: Annotated[str, BeforeValidator(lambda valor: str(valor)[:1000])]


class PreguntaEntrada(BaseModel):
    # Una pregunta del puesto cabe de sobra en 500 caracteres; el tope evita
    # enviar textos enormes (y su costo) al proveedor de IA
    mensaje: Texto
    historial: list[TurnoPrevio] = Field(default_factory=list, max_length=12)
    # Qué pantalla tiene abierta el operador: para decirle "toca este botón" donde está (ADR-047)
    pantalla_actual: (
        Literal["caja", "ventas", "fiados", "compras", "gastos", "analisis", "inventario", "asistente"] | None
    ) = None


class LlaveEntrada(BaseModel):
    # Sin restricciones de Pydantic a propósito: un 422 repetiría la llave en su
    # respuesta. El largo se valida en el router, con un mensaje que no la incluye.
    llave: str


class EstadoAsistente(BaseModel):
    """Nunca lleva la llave: solo si hay una y si se puede guardar desde la pantalla."""

    listo: bool
    puede_guardar_llave: bool
    llave_guardada: bool


class AccionSugerida(BaseModel):
    """Un botón que el Asistente propone. Si `automatica`, el operador pidió ir o hacer algo
    y la app abre esa pantalla sola, con el Asistente a la vista (ADR-047)."""

    tipo: Literal["ir_a", "resaltar"]
    pantalla: str
    etiqueta: str
    automatica: bool = False
    # Solo en "resaltar": el data-ai-id de la parte de la pantalla que se señala
    apartado: str | None = None


class ItemBorrador(BaseModel):
    nombre: str
    # Texto decimal ("2", "1.5"): la app lo lee en la unidad del producto
    cantidad: str
    # Precio de UNA unidad, solo si el operador lo dijo; si no, la app propone el del inventario
    precio: str | None = None


class BorradorVenta(BaseModel):
    """Una orden que el Asistente llenó y el operador revisa y guarda (ADR-049)."""

    items: list[ItemBorrador]
    # Para quién es ("Sra. Bertha"), si el operador lo dijo: será el nombre de la orden
    para: str | None = None


class FormularioLlenado(BaseModel):
    """Un pago de fiado, un gasto o una merma que el Asistente llenó; el operador lo guarda (D-28)."""

    tipo: Literal["abono", "gasto", "merma"]
    # abono: a quién; merma: qué producto (nombre que dijo el operador o del inventario)
    cliente: str | None = None
    producto: str | None = None
    # Solo si el operador lo dijo; si no, el campo queda para que lo escriba él
    monto: str | None = None
    cantidad: str | None = None
    medio: Literal["efectivo", "yape_plin"] | None = None
    ambito: Literal["puesto", "hogar"] | None = None
    categoria: str | None = None
    nota: str | None = None


class RespuestaSalida(BaseModel):
    respuesta: str
    acciones: list[AccionSugerida] = []
    borrador: BorradorVenta | None = None
    formulario: FormularioLlenado | None = None
    # Lo que se guardó en su memoria con esta respuesta (D-26), para decírselo al operador
    recordado: list[str] = []
    # Para valorar la respuesta ("Me sirvió" / "No me sirvió")
    id_respuesta: str
    modelo: str


class ValoracionEntrada(BaseModel):
    id_respuesta: Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
    util: bool


class RecuerdoSalida(BaseModel):
    """Un hecho que el Asistente recuerda del negocio (D-26). El operador lo puede olvidar."""

    model_config = {"from_attributes": True}

    uuid: str
    texto: str
    creado_en: datetime
