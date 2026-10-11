"""Exporta el contrato del API a frontend/src/api/openapi.json.

    cd backend && python exportar_openapi.py

El frontend compara sus tipos con este archivo (contrato.test.ts) y
`tests/test_contrato.py` falla si el archivo quedó desactualizado respecto
del API real. Es la cadena que impide que backend y frontend se desalineen
(ADR-033) sin generar código ni depender de herramientas extra.
"""

import json
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "frontend" / "src" / "api" / "openapi.json"


def contrato_actual() -> dict:
    from main import app

    # Solo los esquemas: son el contrato de datos. Las rutas y textos de ayuda
    # pueden cambiar sin romper al frontend.
    esquemas = app.openapi()["components"]["schemas"]
    return {
        nombre: {
            "required": sorted(esquema.get("required", [])),
            "properties": sorted(esquema.get("properties", {})),
        }
        for nombre, esquema in sorted(esquemas.items())
        if "properties" in esquema
    }


def texto_del_contrato() -> str:
    return json.dumps(contrato_actual(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    DESTINO.write_text(texto_del_contrato(), encoding="utf-8")
    print(f"Contrato exportado a {DESTINO}")
