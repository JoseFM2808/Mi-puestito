"""El repositorio es PÚBLICO: nada sensible puede estar versionado.

`.gitignore` evita que se agreguen por descuido, pero no protege lo que ya
se versionó ni un `git add -f`. Este test revisa lo que git realmente tiene
y falla en CI antes de que el secreto llegue a GitHub.
"""

import fnmatch
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

# Archivos que jamás deben estar versionados (plantillas *.example sí)
PATRONES_PROHIBIDOS = [
    ".env", "*/.env", ".env.*", "*/.env.*", "*.env",
    "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*",
    "*usuarios.json",
    "*.db", "*.db-journal", "*.db-wal", "*.sqlite", "*.sqlite3", "*.dump",
    "docs/meetings/*", "docs/privado/*", "docs/acuerdos/*", ".ai-context/privado/*",
    "*.private.md", "*-privado.md",
    "*.log", "*puerto.txt",
    ".claude/settings.local.json", ".obsidian/workspace*.json",
    "data/raw/*", "data/processed/*", "data/vector_store/*",
]
PERMITIDOS = ["*.env.example", ".env.example"]

# Formas conocidas de llaves reales dentro del contenido
LLAVES = re.compile(
    r"nvapi-[A-Za-z0-9_\-]{20,}"          # NVIDIA NIM
    r"|sk-ant-[A-Za-z0-9_\-]{20,}"        # Anthropic
    r"|sk-[A-Za-z0-9]{32,}"               # OpenAI y compatibles
    r"|AKIA[0-9A-Z]{16}"                  # AWS
    r"|gh[pousr]_[A-Za-z0-9]{36,}"        # GitHub
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


def _archivos_versionados() -> list[str]:
    if shutil.which("git") is None or not (RAIZ / ".git").exists():
        pytest.skip("fuera de un repositorio git (p. ej. dentro del ejecutable)")
    salida = subprocess.run(
        ["git", "-C", str(RAIZ), "ls-files", "-z"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return [ruta for ruta in salida.split("\0") if ruta]


def test_no_hay_archivos_sensibles_versionados():
    prohibidos = [
        ruta
        for ruta in _archivos_versionados()
        if any(fnmatch.fnmatch(ruta, p) for p in PATRONES_PROHIBIDOS)
        and not any(fnmatch.fnmatch(ruta, p) for p in PERMITIDOS)
    ]
    assert prohibidos == [], f"Archivos sensibles versionados: {prohibidos}"


def test_no_hay_llaves_en_el_contenido_versionado():
    con_llaves = []
    for ruta in _archivos_versionados():
        archivo = RAIZ / ruta
        if not archivo.is_file() or archivo.stat().st_size > 1_000_000:
            continue
        try:
            texto = archivo.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binarios (íconos, .ico)
        if LLAVES.search(texto):
            con_llaves.append(ruta)
    assert con_llaves == [], f"Posibles llaves en: {con_llaves}"
