"""Registro opcional de intercambios para un futuro fine-tuning (ADR-038).

Objetivo: que un modelo muy pequeño (familia Gemma 4) que corra en la tablet
aprenda a responder como el Asistente, con ejemplos reales de uso.

Reglas que este archivo hace cumplir:
- APAGADO por defecto. `MI_PUESTITO_IA_REGISTRO=demo` registra solo el
  proyecto de práctica; `todos` incluye negocios reales y exige el
  consentimiento informado del vendedor antes de activarlo.
- Solo se guarda lo que ya salió seudonimizado hacia el proveedor ("Cliente 1",
  nunca un nombre real): la pregunta, el contexto, el historial y la respuesta
  tal como la escribió el modelo.
- Vive en la carpeta de datos del dispositivo (`ia_registro_<proyecto>.jsonl`),
  nunca en el repo (`*.jsonl` está en .gitignore y lo vigila el test de higiene).
- El operador puede valorar cada respuesta ("Me sirvió" / "No me sirvió"): esa
  es la señal para elegir qué ejemplos usar al entrenar.
"""

import json
import threading
from datetime import datetime, timezone

import rutas
from proyectos import PROYECTOS

from . import configuracion

_candado = threading.Lock()


def activo_para(proyecto: str) -> bool:
    modo = configuracion.leer().registro
    if modo == "todos":
        return True
    return modo == "demo" and proyecto in PROYECTOS and not PROYECTOS[proyecto].es_real


def _ruta(proyecto: str):
    return rutas.directorio_datos() / f"ia_registro_{proyecto}.jsonl"


def _agregar(proyecto: str, fila: dict) -> None:
    linea = json.dumps({**fila, "en": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False)
    with _candado, _ruta(proyecto).open("a", encoding="utf-8") as archivo:
        archivo.write(linea + "\n")


def guardar_intercambio(
    proyecto: str,
    id_respuesta: str,
    *,
    mensajes_enviados: list[dict[str, str]],
    respuesta_del_modelo: str,
    modelo: str,
) -> bool:
    """Guarda el intercambio YA seudonimizado, en formato de chat (listo para SFT)."""
    if not activo_para(proyecto):
        return False
    _agregar(
        proyecto,
        {
            "tipo": "intercambio",
            "id": id_respuesta,
            "modelo": modelo,
            "mensajes": [*mensajes_enviados, {"role": "assistant", "content": respuesta_del_modelo}],
        },
    )
    return True


def valorar(proyecto: str, id_respuesta: str, util: bool) -> bool:
    if not activo_para(proyecto):
        return False
    _agregar(proyecto, {"tipo": "valoracion", "id": id_respuesta, "util": util})
    return True
