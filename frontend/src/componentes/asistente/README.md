# Componente: Asistente (AI Companion)

## Qué es

El panel de conversación que se abre con el botón **Asistente** de la barra superior. Habla con
`POST /api/asistente/preguntar`; el backend decide el modelo (NVIDIA hoy, local mañana) y protege los nombres.

## Qué datos maneja

- La conversación en memoria de la pantalla (no se guarda en el dispositivo).
- Envía los últimos 6 turnos como historial, para que el Asistente recuerde de qué se habla.
- En un negocio real muestra un aviso: los nombres de clientes y proveedores se cambian por códigos antes de salir.

## Qué acciones permite

| Acción                                    | Botón                                                                        |
| ----------------------------------------- | ---------------------------------------------------------------------------- |
| Preguntar                                 | Campo "Escríbele al Asistente" + **Enviar**                                  |
| Ir a la pantalla que el Asistente sugiere | Botón con texto completo ("Ir a Ventas"), solo de la lista blanca            |
| Valorar una respuesta                     | **Me sirvió** / **No me sirvió** (ayuda a entrenar un modelo local, ADR-038) |

Sin internet dice que necesita conexión y que lo demás de la app sigue funcionando.

## Cómo interactúa la IA

Es la cara de la IA. `data-ai-id`: `asistente`, `asistente.privacidad`, `asistente.conversacion`, `asistente.pregunta`,
`asistente.enviar`, `asistente.accion-<n>-<pantalla>`, `asistente.sirvio-<n>`, `asistente.no-sirvio-<n>`.
