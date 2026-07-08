# Registro de Decisiones Técnicas

#arquitectura

> Registro histórico. Cada decisión nueva se agrega aquí con alternativas consideradas y razón.

| # | Decisión | Alternativas | Razón |
|---|---|---|---|
| 1 | React sobre Vue | Vue, HTML vanilla | Ecosistema AI-first más maduro; asistentes generan React más preciso; más datos de entrenamiento para una IA local futura |
| 2 | TypeScript | JavaScript puro | Tipado explícito = mayor legibilidad para IA y menos errores |
| 3 | FastAPI sobre Django | Django, Flask | Ligero, async nativo, OpenAPI automático |
| 4 | SQLite → PostgreSQL | MySQL, MongoDB | Desarrollo local sin infraestructura; mismo ORM (SQLAlchemy) al migrar a nube |
| 5 | Offline-first con IndexedDB | Solo cloud | Conectividad variable en mercados. Ver [[Sincronizacion-Offline]] |
| 6 | Documentación en Markdown | JSDoc, solo Swagger | El MD es contexto directo para la IA ([[AI-Companion]] y agentes de desarrollo) |
| 7 | AGENTS.md + Claude Code como base de desarrollo | BMAD-METHOD, Spec Kit total | Mínimo overhead para 1 dev; estándar portable cross-tool. Ver [[Metodologia-Desarrollo]] |
| 8 | Spec Kit solo selectivo | Spec Kit como flujo total | Útil en módulos grandes; pesado para fixes pequeños |
| 9 | LangGraph para runtime de IA | CrewAI, llamadas directas | Menor consumo de tokens, checkpointing, mejor soporte de modelos locales. Ver [[Orquestacion-IA]] |
| 10 | Conexión agnóstica al modelo | Acoplarse a un proveedor | Cualquier modelo debe poder ejecutarse junto al programa. Ver [[Conexion-Agnostica]] |
| 11 | Paleta "A — Mercado" (cálida) | Paleta C austera, B fría | Calidez familiar, bajo brillo bajo luz natural; validada en preview. Ver [[Design-System]] |
| 12 | Tipografía Lexend | Inter, system fonts | Diseñada para baja fluidez lectora ([[Publico-Objetivo]]) |
| 13 | Escala tipográfica en rem desde raíz | px fijos | Permite re-escalar toda la UI con un solo cambio (selector de letra) |
| 14 | Selector de tamaño de letra siempre visible y persistente | Enterrarlo en configuración | Decisión de UX para adulto mayor. Ver [[Design-System]] |
| 15 | Texto sobre íconos (regla dura) | Íconos | El usuario no descifra significados por logo |
| 16 | Teclado nativo de la tablet | Teclado propio | El nativo respeta accesibilidad del SO; uno propio complicaría al usuario |
| 17 | Barra superior fija (no lateral) | Barra lateral flotante | La lateral tapaba contenido y caía en zona de pulgares |
