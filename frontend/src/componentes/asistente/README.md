# Componente: Asistente (AI Companion)

## Qué es

El Asistente en dos formas con la misma conversación: el **apartado** (pantalla de chat, opción del menú lateral) y la
**ventana** (botón **Asistente** de la barra), que va junto a la pantalla de trabajo y sigue abierta al cambiar de
pantalla (ADR-046). En pantalla ancha es una columna a la derecha; en teléfono y tablet, una hoja abajo que se achica.
Si el operador pide ir o hacer algo, abre la pantalla solo; si pregunta dónde está algo, además la señala (ADR-047). Habla con
`POST /api/asistente/preguntar`; el backend decide el modelo (NVIDIA hoy, local mañana) y protege los nombres.

## Qué datos maneja

- La conversación vive en `stores/conversacion.ts` y se guarda en la base local del negocio (IndexedDB, D-26): no se
  pierde al cambiar de pantalla ni al recargar o actualizar la app. Se guardan los últimos 40 mensajes; cada negocio
  tiene la suya; «Empezar una conversación nueva» la borra también del dispositivo.
- Lo que el Asistente recuerda del negocio vive en el servidor (`/api/asistente/recuerdos`); `Recuerdos.tsx` lo muestra
  y lo olvida. Bajo una respuesta que guardó algo se lee "Lo voy a recordar: …".
- Envía los últimos 6 turnos como historial, para que el Asistente recuerde de qué se habla, y la pantalla abierta
  (`pantalla_actual`), para que diga "toca este botón" donde el operador está.
- En un negocio real muestra un aviso: los nombres de clientes y proveedores se cambian por códigos antes de salir.

## Qué acciones permite

| Acción                                     | Botón                                                                            |
| ------------------------------------------ | -------------------------------------------------------------------------------- |
| Preguntar                                  | Campo "Escribe tu pregunta" + **Enviar pregunta**, o tocar una pregunta sugerida |
| Empezar de cero                            | **Empezar una conversación nueva**                                               |
| Pasar a ventana o a pantalla completa      | **Usar en ventana mientras trabajo** / **Pantalla completa**; **Cerrar**         |
| Ver la pantalla de atrás (teléfono/tablet) | **Achicar** / **Agrandar**                                                       |
| Ir a la pantalla que el Asistente sugiere  | Botón con texto completo ("Ir a Ventas"), solo de la lista blanca                |
| Ver la parte que el Asistente señala       | Botón "Muéstrame el botón Nuevo pedido": lleva y marca esa parte 4 s             |
| Hablar en vez de escribir                  | **Hablar** / **Listo, enviar** (solo si el navegador tiene dictado)              |
| Ver un producto que se nombra              | Tocar su nombre subrayado: lleva a su tarjeta en Inventario                      |
| Ir a la orden que llenó                    | **Revisar la orden por guardar**                                                 |
| Valorar una respuesta                      | **Me sirvió** / **No me sirvió** (ayuda a entrenar un modelo local, ADR-038)     |
| Ver lo que recuerda                        | **Lo que recuerdo** (apartado) → **Volver a la conversación**                    |
| Olvidar un recuerdo o todos                | **Olvidar esto** / **Olvidar todo** → **Sí, olvidar todo**                       |

Sin internet dice que necesita conexión y que lo demás de la app sigue funcionando.

## Cómo interactúa la IA

Es la cara de la IA. `data-ai-id`: `asistente`, `asistente.privacidad`, `asistente.conversacion`, `asistente.pregunta`,
`asistente.enviar`, `asistente.sugerencia-<n>`, `asistente.empezar-de-nuevo`, `asistente.accion-<n>-<pantalla>`,
`asistente.sirvio-<n>`, `asistente.no-sirvio-<n>`, `asistente.a-ventana`, `asistente.ver-recuerdos`,
`asistente.recuerdos`, `asistente.olvidar-<uuid>`, `asistente.olvidar-todo`, `asistente.confirmar-olvidar-todo`,
`asistente.cancelar-olvidar-todo`, `asistente.cerrar-recuerdos`.

Lo que hace solo (ADR-047): con una acción `automatica` abre la pantalla (`llevarConAsistente`) y, si es `resaltar`,
marca el `data-ai-id` indicado con `senalar.ts` (atributo `data-resaltado`, estilo en `estilos-base.css`). Debajo de la
respuesta dice qué hizo: "Abrí Compras. Sigo aquí…" o "Te lo marqué en la pantalla."

En la ventana los `data-ai-id` llevan el prefijo `asistente-ventana` (`asistente-ventana.pregunta`,
`asistente-ventana.accion-<n>-<pantalla>`, `asistente-ventana.achicar`, `asistente-ventana.ampliar`,
`asistente-ventana.cerrar`…). Además `<prefijo>.hablar`, `<prefijo>.producto-<n>-<m>` (enlace a un producto) y
`<prefijo>.ver-borrador-<n>`.

Si pide registrar una venta, la respuesta trae `borrador`: la app lo deja en `stores/borradorAsistente.ts`, abre Ventas y
lo señala (ADR-049). El Asistente nunca guarda. La voz usa `dictado.ts` (Web Speech API, `es-PE`); en un negocio real
se avisa que va a Google o Microsoft.

Si pide anotar un pago de fiado, un gasto o una merma, la respuesta trae `formulario`: se deja en
`stores/borradorAsistente.ts` (`ponerFormulario`), se abre Fiados, Gastos o Inventario y esa pantalla lo toma una vez
(`tomarFormulario`) para abrir su formulario de siempre ya llenado (D-28).

Si pide hacer un pedido a un proveedor, la respuesta trae `pedido` (proveedor y productos): se deja en
`stores/borradorAsistente.ts` (`ponerPedido`), se abre Compras y esa pantalla lo toma una vez (`tomarPedido`) para abrir
«Nuevo pedido» llenado. Debajo se lee "Dejé el pedido llenado en Compras…".
