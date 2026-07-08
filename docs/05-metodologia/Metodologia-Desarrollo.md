# Metodología de Desarrollo

#metodologia

Cómo se construye este proyecto (development time). La capa de IA en producción se documenta en [[Orquestacion-IA]].

## Base permanente: AGENTS.md + Claude Code

- `AGENTS.md` en la raíz del repo es la **fuente de verdad** para cualquier herramienta de IA: stack, comandos, convenciones, reglas no negociables.
- `CLAUDE.md` importa `@AGENTS.md` (Claude Code aún no lee AGENTS.md nativo).
- Es el estándar portable cross-tool (Codex, Cursor, Copilot, Gemini CLI, etc.): si se cambia de herramienta, el contexto viaja con el repo.
- Se mantiene **escrito a mano y corto** (< 500 líneas).

## Flujo de trabajo: planificación + ejecución

Se trabaja con Claude Code en CLI bajo un ciclo de **plan mode → aprobación → ejecución → revisión por bloques**. No se usa el ciclo multi-agente pesado (BMAD y similares) por eficiencia. Ver [[Agentes-De-Desarrollo]].

## Selectivo: Spec Kit para módulos grandes

Para módulos nuevos grandes (ej. [[Modulo-Ventas]], [[Modulo-Inventario]]) se puede correr el flujo Spec-Driven:
`constitution → specify → plan → tasks → implement`

Los `specs/` generados se versionan: sirven de documentación de onboarding. **No** se usa para fixes pequeños (overhead innecesario).

## Documentación como contexto

Cada módulo de código lleva su `README.md` (qué es, qué datos, qué acciones, cómo interactúa la IA). Esta bóveda (`docs/`) conecta todo con wikilinks navegables en Obsidian. La documentación no es un anexo: **es el contexto operativo** de los agentes de desarrollo ([[Agentes-De-Desarrollo]]) y del [[AI-Companion]] en runtime.

## Evolución prevista

- Si el equipo crece a 3+ devs → evaluar Spec Kit como flujo por defecto.
- Si aparecen requisitos de compliance → evaluar BMAD-METHOD.
- Registrado en [[Decisiones-Tecnicas]].
