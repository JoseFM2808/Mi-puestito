# Sistema de Gestión para Pequeños Vendedores

Aplicación web (PWA, tablet-first) para vendedores informales en Perú, con un AI Companion integrado que guía y asiste al usuario. Proyecto open source.

## Documentación

Toda la planificación y arquitectura vive en [`docs/`](./docs/00-INICIO.md), estructurada como bóveda Obsidian navegable con wikilinks. Empezar por [`docs/00-INICIO.md`](./docs/00-INICIO.md).

## Para desarrollar con IA

Este repo usa el estándar `AGENTS.md` (raíz) como contexto para herramientas de IA. Claude Code lo lee vía `CLAUDE.md`. Flujo de trabajo: planificación + ejecución (plan mode → aprobación → ejecución → revisión por bloques).

## Estado

En planificación. La construcción del código aún no ha iniciado. Ver decisiones en [`docs/02-arquitectura/Decisiones-Tecnicas.md`](./docs/02-arquitectura/Decisiones-Tecnicas.md).

## Estructura

```
.
├── AGENTS.md              # Contexto para cualquier herramienta de IA (fuente de verdad)
├── CLAUDE.md              # Importa AGENTS.md + apunta a la bóveda
├── .claude/
│   ├── agents/            # Subagentes (revisor)
│   └── settings.json      # Permisos de Claude Code
├── docs/                  # Bóveda Obsidian (planificación completa)
├── frontend/              # React + TS + Vite (por crear)
└── backend/               # FastAPI + Python (por crear)
```
