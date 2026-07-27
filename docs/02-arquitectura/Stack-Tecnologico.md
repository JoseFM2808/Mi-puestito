# Stack Tecnológico

#arquitectura

## Frontend
- **React 18+ / TypeScript / Vite** — ecosistema más maduro para productos AI-first; los asistentes de código generan React con mayor precisión; más contexto de entrenamiento disponible para una futura IA local. Ver razones completas en [[Decisiones-Tecnicas]].
- **PWA tablet-first** — instalable, sin pasar por tiendas de apps (`vite-plugin-pwa`).
- **Zustand** — estado global del frontend; su middleware `persist` guarda las preferencias del operador por sesión. Ver [[Decisiones-Tecnicas]] (entrada 18).
- **IndexedDB (Dexie.js)** — almacenamiento local para [[Sincronizacion-Offline]].

## Backend
- **Python 3.11+ / FastAPI** — ligero, async nativo, OpenAPI automático, lenguaje natural del ecosistema IA.
- **SQLAlchemy** — mismo ORM para SQLite (local/desarrollo) y PostgreSQL (nube), sin cambiar código.

## Capa de IA (runtime)
- **LangGraph** como orquestador del [[AI-Companion]]. Ver [[Orquestacion-IA]].
- **Conexión agnóstica al modelo** — ver [[Conexion-Agnostica]]. Ningún proveedor está definido como permanente: el programa debe poder ejecutarse junto a cualquier modelo.

## Desarrollo
- **AGENTS.md + Claude Code** como base. **Spec Kit** selectivo para módulos grandes. Ver [[Metodologia-Desarrollo]].
