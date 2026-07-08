# AI Companion

#ia #mvp

Asistente de IA integrado en la interfaz. **Es core del MVP**: la primera versión no se libera sin él, porque el [[Publico-Objetivo]] no puede quedar atrapado en ningún punto.

## Capacidades

1. Responder preguntas sobre cualquier dato registrado.
2. Indicar dónde está cada módulo o función.
3. **Navegar automáticamente** la interfaz hacia donde el usuario necesita ir, avisando antes de cualquier transición.
4. **Rellenar formularios** si el usuario lo pide (dictado o texto).
5. Ofrecer ayuda proactiva si detecta que el usuario está perdido.

## Flujo típico

```
Usuario: "¿Dónde registro que llegó un pedido?"
IA: "Te llevo al módulo de Compras, sección Confirmación de Recepción. ¿Continuamos?"
Usuario: "Sí"
IA: [navega y resalta el checklist] "Estamos aquí. ¿Te ayudo a completarlo?"
```

## Requisito técnico fundamental

**Cada componente de la UI es identificable programáticamente:**
- Atributo `data-ai-id` único en cada elemento interactivo.
- Cada módulo/componente tiene su `README.md` describiendo: qué es, qué datos acepta, qué acciones permite, cómo la IA debe dirigirse al usuario en ese contexto.
- La IA consulta esos MD como contexto antes de responder — por eso toda la documentación del proyecto se escribe pensando en que una IA la leerá.

## Arquitectura

La orquestación del companion corre sobre LangGraph → [[Orquestacion-IA]]. El modelo subyacente es intercambiable → [[Conexion-Agnostica]]. Su identidad visual (color, ubicación) se define en [[Design-System]].
