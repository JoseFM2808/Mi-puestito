# Componente: Barra superior

## Qué es

Franja fija (`sticky top`) presente en **toda** la experiencia, definida en
`docs/06-diseno/Design-System.md` (sección 6). No pertenece a ningún módulo:
es el punto de anclaje de la navegación, del AI Companion y del selector de
tamaño de letra.

## Qué datos maneja

- **Tamaño de letra** del operador, leído/escrito en el store Zustand
  `src/stores/preferencias.ts`. Tres niveles: Normal (20px), Grande (23px),
  Muy grande (27px). Se persiste en `sessionStorage` (dura la sesión; vuelve a
  Normal en una sesión nueva). El cambio escribe `data-letra` en `<html>` y
  toda la UI re-escala vía la escala rem de `tokens.css`.

## Qué acciones permite

| Acción              | Resultado                                                                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Menú**            | Solo en pantalla angosta: abre el menú lateral (`componentes/menu-lateral`). En la ancha el menú ya está a la vista y el botón no aparece |
| **Asistente**       | Abre o cierra la ventana flotante del Asistente sobre la pantalla actual (`componentes/asistente`). Su apartado completo está en el menú  |
| **Tamaño de letra** | Cambia entre los 3 niveles; persiste durante la sesión                                                                                    |

Debajo de la barra aparece el estado de conexión cuando hay cambios por enviar o no hay red
(`componentes/sincronizacion/EstadoSincronizacion.tsx`).

## Cómo interactúa la IA

`data-ai-id` disponibles para que el AI Companion identifique y accione:

- `barra` — el contenedor completo
- `barra.menu` — abre el menú lateral en pantalla angosta (la navegación vive en `menu.*`, ver `componentes/menu-lateral`)
- `barra.asistente` — botón Asistente (color `--ia`, identidad del Companion)
- `barra.letra-normal`, `barra.letra-grande`, `barra.letra-muygrande` — selector

Si el usuario pide "letra más grande", la IA puede sugerir el siguiente nivel del selector. El botón Asistente es el
hogar visual permanente del Companion: mismo color y lugar siempre.
