# .ai-context/

Arquitectura viva de Mi Puestito para agentes de IA (Claude Code y otros). Se versiona en el repo **público**.

| Archivo | Contenido |
|---|---|
| `llms.txt` | Índice para LLMs (formato llmstxt.org) |
| `01-logica-sistema.md` | Flujos transaccionales, inventario y cobro |
| `02-arquitectura.md` | Entornos, dependencias, capa de IA |
| `03-base-de-datos.md` | ER + diccionario de datos |
| `04-decisiones.md` | ADRs desde el 028 |
| `05-deuda-tecnica-higiene.md` | Deuda priorizada + estado de `.gitignore` |
| `06-api-mcp.md` | Contrato REST por módulo, autenticación y estado de MCP |

**Qué entra aquí**: solo decisiones formales de arquitectura o negocio con impacto técnico.
**Qué no entra**: actas, acuerdos comerciales, conversaciones de aprendizaje, datos reales de clientes o ventas, secretos. Lo privado del equipo va en `privado/` (ignorado por git y vigilado por `backend/tests/test_higiene_repo.py`).

Precedencia: `AGENTS.md` > `docs/` > `.ai-context/`. Si una decisión Aceptada cambia, también se actualiza `docs/02-arquitectura/Decisiones-Tecnicas.md`.
