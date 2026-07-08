# AGENTS.md — Sistema de Gestión para Pequeños Vendedores

## Visión general

Aplicación web (PWA, tablet-first) para vendedores informales en Perú con bajo perfil tecnológico. Gestiona compras a proveedores, ventas (órdenes activas, fiado, venta rápida), inventario y flujo de caja. Incluye un AI Companion integrado que guía, navega la UI y asiste al usuario en tiempo real. Proyecto open source.

## Stack

- **Frontend:** React 18+ con TypeScript, Vite, PWA. Offline-first con IndexedDB (Dexie.js).
- **Backend:** Python 3.11+ con FastAPI, SQLAlchemy. SQLite en local, PostgreSQL en nube.
- **IA en runtime:** LangGraph como orquestador. Conexión agnóstica al modelo (API comercial o modelo local — nunca acoplar a un proveedor específico).
- **Desarrollo:** AGENTS.md + Claude Code como base. Spec Kit selectivo para módulos grandes nuevos.

## Comandos

```bash
# Frontend
cd frontend && npm install && npm run dev    # desarrollo
npm run build                                 # build producción
npm run test                                  # tests

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload                     # desarrollo
pytest                                        # tests
```

## Convenciones de código

- TypeScript estricto. Nada de `any` sin justificación documentada.
- Cada módulo React vive en `frontend/src/modules/<nombre>/` con su propio `README.md`.
- Cada componente interactivo lleva atributo `data-ai-id` único para que el AI Companion pueda identificarlo y navegarlo.
- Backend modular: `backend/modules/<nombre>/` con router, modelos, esquemas y `README.md` propios.
- Nombres de variables, funciones y comentarios en español (el dominio es peruano: ventas, compras, fiado, proveedores).
- Cada módulo es independiente: el fallo de uno no debe derribar otro. No crear dependencias cruzadas obligatorias entre módulos.
- Estilos: usar exclusivamente los tokens de `docs/06-diseno/tokens.css`. Ningún color, tamaño o espaciado "a mano".

## Documentación obligatoria

- Todo módulo o componente nuevo DEBE incluir/actualizar su `README.md` describiendo: qué es, qué datos maneja, qué acciones permite, y cómo la IA debe interactuar con él.
- La documentación de arquitectura vive en `docs/` (bóveda Obsidian con wikilinks). Si una decisión técnica cambia, actualizar `docs/02-arquitectura/Decisiones-Tecnicas.md`.
- Estos MD son el contexto que alimenta al AI Companion en runtime: escribirlos pensando en que una IA los leerá.

## Reglas no negociables

- Offline-first: ninguna funcionalidad core (ventas, compras) puede requerir conexión para operar.
- Nunca acoplar el código a un proveedor de IA específico. Toda llamada a un modelo pasa por la capa de abstracción de IA.
- UI simple, tablet-first, pensada para usuarios sin experiencia tecnológica.
- Texto sobre íconos: los botones siempre llevan texto completo. Un ícono jamás reemplaza la palabra ni cambia entre versiones.
- El sistema detecta fecha/hora/zona horaria automáticamente (Perú: UTC-5). El usuario nunca las ingresa manualmente.
- No tocar `docs/` sin reflejar los cambios en los documentos relacionados (los wikilinks deben mantenerse válidos).

## Flujo de trabajo con Claude Code

- Trabajar en modo **planificación + ejecución**: antes de escribir código, presentar un plan (plan mode), esperar aprobación, luego ejecutar. Revisión por bloques.
- No usar ciclo multi-agente pesado. Usar el subagente revisor (`.claude/agents/revisor.md`) solo cuando un módulo lo amerite, para auditar en contexto limpio.

## Seguridad

- No almacenar credenciales en el repo.
- Datos del vendedor (ventas, fiados, clientes) son sensibles: tratarlos bajo la ley peruana de protección de datos personales.
