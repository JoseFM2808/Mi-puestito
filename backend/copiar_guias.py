"""Paso de build en Vercel: copia el README de cada pantalla dentro del backend (ADR-056, ADR-058).

El Asistente usa esas tablas "Qué acciones permite" como manual (`ia/guias.py`). En el repositorio
viven en `frontend/src/modules/<módulo>/README.md`, fuera del servicio del backend, así que el
build las copia a `backend/guias/` (ignorada por git) para que viajen con la función. Si no
están a la vista, no pasa nada: el Asistente usa su guía compacta.

    python copiar_guias.py
"""

import shutil
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ORIGEN = AQUI.parent / "frontend" / "src" / "modules"
DESTINO = AQUI / "guias"


def main() -> int:
    if not ORIGEN.is_dir():
        print(f"Sin {ORIGEN}: el Asistente usará su guía compacta.")
        return 0
    copiados = 0
    for readme in sorted(ORIGEN.glob("*/README.md")):
        destino = DESTINO / readme.parent.name / "README.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(readme, destino)
        copiados += 1
    print(f"Guías del Asistente copiadas: {copiados} en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
