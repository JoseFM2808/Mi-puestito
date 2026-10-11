"""Verifica qué modelos responden y cuánto tardan, y deja el orden elegido.

    cd backend
    python -m ia.verificar            # usa NVIDIA_API_KEY del entorno

El catálogo de NVIDIA cambia: un modelo listado puede no estar disponible
para tu llave. Este script prueba cada candidato con una pregunta del puesto
que tiene UNA respuesta correcta (120 + 45 = 165) y guarda en la carpeta de
datos `ia_modelos.json`: primero los que acertaron, del más rápido al más
lento; después los que respondieron mal (el Asistente no los usa). Un modelo
rápido que suma mal no sirve en una caja.

El archivo guarda solo nombres de modelos y tiempos: NUNCA la llave.
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone

import httpx

import rutas

from . import configuracion
from .compatible_openai import ProveedorCompatibleOpenAI, RespuestaConBorrador
from .servicio import armar_mensajes

# Candidatos de NVIDIA (catálogo del 2026-10-08), eficientes primero. Gemma 4
# y Gemma 3 son la familia del modelo local futuro; los Nemotron con "a3b"
# son MoE con ~3B de parámetros activos por token (rápidos).
CANDIDATOS_NVIDIA = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "openai/gpt-oss-20b",
    "google/gemma-4-31b-it",
    "nvidia/nemotron-nano-3-30b-a3b",
    "google/gemma-3-12b-it",
    "google/gemma-3-4b-it",
]

# La prueba usa el MISMO prompt que el Asistente (guía de la app + reglas), con
# un contexto ya seudonimizado: así se detecta un modelo que no sigue el formato
# o que devuelve su razonamiento, no solo uno que no sabe sumar.
CONTEXTO_PRUEBA = (
    '{"ventas_hoy": "120.00", "fiados_por_cobrar": "45.00", "ordenes_activas": '
    '[{"nombre": "Cliente 1", "tipo": "fiado", "monto": "0.00", "deuda_cliente": "45.00"}]}'
)
PRUEBA = armar_mensajes(
    "Hoy vendí S/ 120 y Cliente 1 me debe S/ 45. Si hoy me paga, ¿cuánto tendré en total?",
    CONTEXTO_PRUEBA,
    [],
)
LARGO_MAXIMO = 600  # "1 a 4 frases cortas": algo más largo no sirve en el puesto

TIEMPO_PRUEBA = 30.0
RESPUESTA_CORRECTA = "165"
# Un modelo en frío puede tardar en la primera llamada: se le da otra oportunidad
REINTENTOS_POR_TIEMPO = 1


def es_correcta(texto: str) -> bool:
    return RESPUESTA_CORRECTA in texto.replace(" ", "").replace(",", "") and len(texto) <= LARGO_MAXIMO


def ordenar(resultados: list[dict]) -> list[dict]:
    """Correctos por latencia; luego los que respondieron mal; luego los caídos."""
    def clave(fila: dict):
        if not fila["responde"]:
            return (2, 0.0)
        return (0 if fila.get("correcto", True) else 1, fila["segundos"])

    return sorted(resultados, key=clave)


def _motivo(error: Exception) -> str:
    """Explicación corta y SIN datos sensibles (nunca la cabecera con la llave)."""
    if isinstance(error, httpx.HTTPStatusError):
        codigo = error.response.status_code
        return {401: "llave inválida", 403: "sin permiso para este modelo", 404: "no disponible",
                429: "límite de uso alcanzado"}.get(codigo, f"error HTTP {codigo}")
    if isinstance(error, httpx.TimeoutException):
        return f"no respondió en {TIEMPO_PRUEBA:.0f} s"
    if isinstance(error, RespuestaConBorrador):
        return "devolvió su razonamiento en vez de la respuesta"
    return type(error).__name__


async def probar(proveedor, modelo: str) -> dict:
    for intento in range(REINTENTOS_POR_TIEMPO + 1):
        inicio = time.perf_counter()
        try:
            ajustes = configuracion.ajustes_para(modelo)
            texto = await proveedor.responder(PRUEBA, modelo, TIEMPO_PRUEBA, ajustes)
        except httpx.TimeoutException as error:
            if intento < REINTENTOS_POR_TIEMPO:
                continue
            return {"modelo": modelo, "responde": False, "motivo": _motivo(error)}
        except Exception as error:  # noqa: BLE001 — se informa y se sigue con el siguiente
            return {"modelo": modelo, "responde": False, "motivo": _motivo(error)}
        return {
            "modelo": modelo,
            "responde": True,
            "correcto": es_correcta(texto),
            "segundos": round(time.perf_counter() - inicio, 2),
            "ejemplo": texto[:160],
        }
    raise AssertionError("inalcanzable")


async def verificar(candidatos: list[str] | None = None) -> dict:
    config = configuracion.leer()
    if not config.lista and config.proveedor == "nvidia":
        raise SystemExit("Falta NVIDIA_API_KEY en el entorno de esta ventana.")
    proveedor = ProveedorCompatibleOpenAI(config.url_base, config.api_key)
    lista = candidatos or (CANDIDATOS_NVIDIA if config.proveedor == "nvidia" else list(config.modelos))

    resultados = []
    for modelo in lista:
        print(f"  Probando {modelo} …", flush=True)
        resultados.append(await probar(proveedor, modelo))

    datos = {
        "proveedor": config.proveedor,
        "verificado_en": datetime.now(timezone.utc).isoformat(),
        "modelos": ordenar(resultados),
    }
    (rutas.directorio_datos() / configuracion.ARCHIVO_MODELOS).write_text(
        json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return datos


def main() -> int:
    print("\nVerificando modelos de IA…\n")
    datos = asyncio.run(verificar(sys.argv[1:] or None))
    print("\n  Resultado (el Asistente usará este orden):\n")
    for fila in datos["modelos"]:
        if fila["responde"] and fila.get("correcto", True):
            print(f"   OK   {fila['segundos']:>6.2f} s   {fila['modelo']}")
        elif fila["responde"]:
            respuesta = fila["ejemplo"][:50]
            print(f"   MAL  {fila['segundos']:>6.2f} s   {fila['modelo']}  (respondió: {respuesta!r})")
        else:
            print(f"   --   {'':>8}   {fila['modelo']}  ({fila['motivo']})")
    print(f"\n  Guardado en {rutas.directorio_datos() / configuracion.ARCHIVO_MODELOS} (sin la llave).\n")
    return 0 if any(f["responde"] and f.get("correcto", True) for f in datos["modelos"]) else 1


if __name__ == "__main__":
    sys.exit(main())
