# Agentes de Desarrollo

#metodologia

Roles de IA que asisten la construcción del proyecto. Definidos como archivos Markdown portables, para que cualquier colaborador los active en su herramienta preferida.

## Enfoque elegido: planificación + ejecución

Por eficiencia, **no** se usa el ciclo multi-agente completo. El flujo base es: Claude Code planifica (plan mode), José aprueba, Claude ejecuta, José revisa por bloques. El subagente revisor se usa solo cuando un módulo lo amerite, para auditar en contexto limpio.

## Roles disponibles

| Rol | Función | Acceso | Cuándo |
|---|---|---|---|
| **Ejecutor** (Claude Code base) | Planifica e implementa siguiendo AGENTS.md | Lectura/escritura | Siempre |
| **Revisor** (`.claude/agents/revisor.md`) | Audita diseño, contrato y convenciones en contexto limpio | Solo lectura | Bajo demanda, en módulos grandes |

## Principios

1. **Separación escritor/revisor:** quien escribe el código no lo audita en la misma sesión (evita puntos ciegos).
2. **Definición portable:** cada rol vive como MD con frontmatter (formato subagentes de Claude Code en `.claude/agents/`, replicable a `.github/agents/` para Copilot).
3. Los roles consultan [[Metodologia-Desarrollo]] y AGENTS.md como contexto base.
