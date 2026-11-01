"""Arma el dataset de fine-tuning desde el registro del Asistente (ADR-038/039).

    cd backend
    python -m ia.dataset salida.jsonl                # solo proyecto demo
    python -m ia.dataset salida.jsonl --proyecto otro

Solo entran los intercambios que el operador marcó "Me sirvió". Se descartan los
borradores de razonamiento (D-20), las respuestas de respaldo del verificador de
cifras y cualquier respuesta con un monto que no esté en su propio contexto: un
modelo pequeño no debe aprender de un error. Todo lo guardado ya viene
seudonimizado; la salida es JSONL con {"messages": [...]}, el formato habitual de
entrenamiento supervisado, y como `*.jsonl` no se versiona.
"""

import json
import sys

import rutas

from .cifras import cifras_no_respaldadas
from .compatible_openai import es_borrador
from .servicio import MODELO_VERIFICADOR


def _utilizable(fila: dict) -> bool:
    mensajes = fila.get("mensajes") or []
    if fila.get("modelo") == MODELO_VERIFICADOR or len(mensajes) < 3:
        return False
    respuesta = mensajes[-1].get("content", "")
    if mensajes[-1].get("role") != "assistant" or not respuesta or es_borrador(respuesta):
        return False
    previos = " ".join(m.get("content", "") for m in mensajes[:-1])
    return not cifras_no_respaldadas(respuesta, previos, previos)


def armar(proyecto: str = "demo") -> list[dict]:
    """Ejemplos listos para entrenar, sin repetir conversaciones idénticas."""
    ruta = rutas.directorio_datos() / f"ia_registro_{proyecto}.jsonl"
    if not ruta.exists():
        return []
    intercambios, utiles = {}, set()
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        fila = json.loads(linea)
        if fila.get("tipo") == "intercambio":
            intercambios[fila["id"]] = fila
        elif fila.get("tipo") == "valoracion":
            # La última valoración manda: un "No me sirvió" posterior lo saca
            (utiles.add if fila.get("util") else utiles.discard)(fila["id"])

    vistos, ejemplos = set(), []
    for id_respuesta, fila in intercambios.items():
        if id_respuesta in utiles and _utilizable(fila):
            huella = json.dumps(fila["mensajes"], ensure_ascii=False, sort_keys=True)
            if huella not in vistos:
                vistos.add(huella)
                ejemplos.append({"messages": fila["mensajes"]})
    return ejemplos


def main() -> int:
    argumentos = sys.argv[1:]
    proyecto = "demo"
    if "--proyecto" in argumentos:
        indice = argumentos.index("--proyecto")
        proyecto = argumentos[indice + 1]
        del argumentos[indice : indice + 2]
    if len(argumentos) != 1:
        print("Uso: python -m ia.dataset salida.jsonl [--proyecto demo]")
        return 2
    ejemplos = armar(proyecto)
    with open(argumentos[0], "w", encoding="utf-8") as salida:
        for ejemplo in ejemplos:
            salida.write(json.dumps(ejemplo, ensure_ascii=False) + "\n")
    print(f"{len(ejemplos)} ejemplos en {argumentos[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
