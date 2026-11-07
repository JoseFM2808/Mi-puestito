# Componente: Asistente (AI Companion)

## Qué es

El Asistente en dos formas con la misma conversación: el **apartado** (pantalla de chat, opción del menú lateral) y la
**ventana flotante** (botón **Asistente** de la barra), que queda sobre la pantalla actual y sigue abierta al cambiar de
pantalla, para que el operador vea lo que el Asistente le indica (ADR-046). Habla con
`POST /api/asistente/preguntar`; el backend decide el modelo (NVIDIA hoy, local mañana) y protege los nombres.

## Qué datos maneja

- La conversación vive en `stores/conversacion.ts`: no se pierde al cambiar de pantalla, se borra al cerrar la app o al
  cambiar de negocio, y nunca se guarda en el dispositivo.
- Envía los últimos 6 turnos como historial, para que el Asistente recuerde de qué se habla.
- En un negocio real muestra un aviso: los nombres de clientes y proveedores se cambian por códigos antes de salir.

## Qué acciones permite

| Acción                                    | Botón                                                                            |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| Preguntar                                 | Campo "Escribe tu pregunta" + **Enviar pregunta**, o tocar una pregunta sugerida |
| Empezar de cero                           | **Empezar una conversación nueva**                                               |
| Pasar a ventana o a pantalla completa     | **Usar en ventana mientras trabajo** / **Pantalla completa**; **Cerrar**         |
| Ir a la pantalla que el Asistente sugiere | Botón con texto completo ("Ir a Ventas"), solo de la lista blanca                |
| Valorar una respuesta                     | **Me sirvió** / **No me sirvió** (ayuda a entrenar un modelo local, ADR-038)     |

Sin internet dice que necesita conexión y que lo demás de la app sigue funcionando.

## Cómo interactúa la IA

Es la cara de la IA. `data-ai-id`: `asistente`, `asistente.privacidad`, `asistente.conversacion`, `asistente.pregunta`,
`asistente.enviar`, `asistente.sugerencia-<n>`, `asistente.empezar-de-nuevo`, `asistente.accion-<n>-<pantalla>`,
`asistente.sirvio-<n>`, `asistente.no-sirvio-<n>`, `asistente.a-ventana`.

En la ventana los `data-ai-id` llevan el prefijo `asistente-ventana` (`asistente-ventana.pregunta`,
`asistente-ventana.accion-<n>-<pantalla>`, `asistente-ventana.ampliar`, `asistente-ventana.cerrar`…).
