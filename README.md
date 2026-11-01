# Sistema de Gestión para Pequeños Vendedores

Aplicación web (PWA, tablet-first) para vendedores informales en Perú, con un AI Companion integrado que guía y asiste al usuario. Proyecto open source.

## Documentación

Toda la planificación y arquitectura vive en [`docs/`](./docs/00-INICIO.md), estructurada como bóveda Obsidian navegable con wikilinks. Empezar por [`docs/00-INICIO.md`](./docs/00-INICIO.md).

## Para desarrollar con IA

Este repo usa el estándar `AGENTS.md` (raíz) como contexto para herramientas de IA. Claude Code lo lee vía `CLAUDE.md`. Flujo de trabajo: planificación + ejecución (plan mode → aprobación → ejecución → revisión por bloques).

## Estado

**Funcionan de punta a punta, también sin internet**: Caja de hoy, Ventas (orden
activa, fiado, venta rápida), Fiados y Compras (pedidos a proveedores y checklist de
recepción). Además: respaldo y restauración de los datos, Asistente con IA que guía
sin inventar cifras, y ejecutable de escritorio para Windows. Inventario existe en el
backend y aún no tiene pantalla. Ver el tablero de avance en
[`docs/05-metodologia/Plan-De-Trabajo.md`](./docs/05-metodologia/Plan-De-Trabajo.md)
y las decisiones en [`docs/02-arquitectura/Decisiones-Tecnicas.md`](./docs/02-arquitectura/Decisiones-Tecnicas.md).

## Descargar el programa (Windows)

No hace falta instalar nada: se descarga **un solo archivo** y se abre con doble clic.

1. Entrar a la pestaña **Actions** del repositorio → flujo **Ejecutable Windows**.
2. Abrir la última ejecución y descargar el artefacto `MiPuestito-windows`.
3. Descomprimir y ejecutar `MiPuestito.exe`. Se abre solo en el navegador.

Los datos se guardan en `%LOCALAPPDATA%\MiPuestito\` (un archivo por proyecto;
la carpeta se muestra al arrancar). Detalles en [`docs/02-arquitectura/Distribucion-Escritorio.md`](./docs/02-arquitectura/Distribucion-Escritorio.md).

Para generarlo uno mismo, en la máquina destino:

```bash
cd frontend && npm ci && npm run build
cd ../backend && pip install -r requirements.txt -r requirements-empaquetado.txt
pyinstaller MiPuestito.spec --noconfirm      # → dist/MiPuestito.exe
```

## Cómo correr la Demo 1

```bash
# Frontend (http://localhost:5173)
cd frontend && npm install && npm run dev
npm run test      # tests
npm run build     # build producción (PWA)

# Backend (http://localhost:8000, OpenAPI en /docs)
cd backend && pip install -r requirements.txt
uvicorn main:app --reload
pytest            # tests
```

## Variables de entorno (opcionales)

Plantilla completa y sin valores en [`config/.env.example`](./config/.env.example).
Copiarla a `config/.env.staging` (ignorado por git) y arrancar con
`uvicorn main:app --reload --env-file ../config/.env.staging`.

| Variable | Default | Para qué |
|---|---|---|
| `MI_PUESTITO_BD` | un SQLite por proyecto | URL de la base de datos (PostgreSQL en nube) |
| `MI_PUESTITO_DATOS` | carpeta del backend / `%LOCALAPPDATA%\MiPuestito` | Dónde se guardan los datos (Staging: fuera del repo) |
| `MI_PUESTITO_ORIGENES` | `http://localhost:5173,http://127.0.0.1:5173` | Orígenes permitidos por CORS |
| `MI_PUESTITO_ENTORNO` | `local` | `production` exige `MI_PUESTITO_SECRETO` de 32+ caracteres |
| `NVIDIA_API_KEY` | — | Llave del Asistente (NVIDIA NIM). Si falta, el `.exe` la pide en pantalla y la guarda cifrada |
| `MI_PUESTITO_IA_PROVEEDOR` | `nvidia` | `local` para Ollama / llama.cpp |

Todas las de IA están explicadas en `backend/ia/configuracion.py`.

## Asistente con IA (Staging)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\staging-con-ia.ps1
```

La ventana pide la API Key de NVIDIA sin mostrarla (vive solo en memoria, o en tu usuario de
Windows si lo eliges), verifica qué modelos responden **bien** con esa llave y arranca la app en
`http://127.0.0.1:8765` con datos separados de los reales. Entra con la cuenta **Demo** (PIN 0000)
y toca **Asistente**. Los nombres de clientes se cambian por códigos antes de salir hacia la IA.

## Estructura

```
.
├── AGENTS.md              # Contexto para cualquier herramienta de IA (fuente de verdad)
├── CLAUDE.md              # Importa AGENTS.md + apunta a la bóveda
├── .claude/
│   ├── agents/            # Subagentes (revisor)
│   └── settings.json      # Permisos de Claude Code
├── docs/                  # Bóveda Obsidian (planificación completa)
│   └── 06-diseno/tokens.css   # Fuente de verdad visual (el frontend la importa directo)
├── frontend/              # PWA React + TS + Vite + Zustand
│   └── src/
│       ├── componentes/barra-superior/   # Menú, Asistente, tamaño de letra
│       ├── componentes/limite-errores/   # Aislamiento de fallos por módulo
│       ├── modules/dashboard/            # Caja Diaria (datos ficticios en Demo 1)
│       └── stores/preferencias.ts        # Zustand (persistencia por sesión)
└── backend/               # FastAPI + SQLAlchemy + SQLite
    ├── escritorio.py       # Lanzador del ejecutable de escritorio
    ├── MiPuestito.spec     # Receta de empaquetado (PyInstaller)
    └── modules/            # dashboard / ventas / compras / inventario / asistente / respaldo (router+README c/u)
```
