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

## Estado (2026-11-08)

- Capacidades 1 y 2: hechas (cifras de hoy con verificador, guía de la app).
- Capacidad 3: hecha sin pedir confirmación, porque solo abre pantallas cuando el operador lo pide ("quiero registrar
  una compra") o pregunta dónde está algo, y marca la parte (ADR-047). La conversación queda al lado: el operador llena los
  datos mientras pregunta. La "Confirmación de Recepción" del flujo de arriba aún no se puede señalar: es una vista que se
  abre por pedido, no una parte fija de la pantalla.
- Capacidad 4 (rellenar formularios): hecha para órdenes de venta (ADR-049). El Asistente llena y el operador revisa y
  toca «Guardar orden»; los precios solo salen de lo que dijo el operador o del inventario. Se le puede hablar
  (dictado del navegador). Compras y pagos: pendientes (D-28).
- Capacidad 5 (ayuda proactiva): pendiente; exigirá una decisión formal nueva.
