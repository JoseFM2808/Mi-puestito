# Piezas base del Design System (`src/ui`)

## Qué es

Los componentes que todos los módulos usan en vez de definir sus propios estilos (ADR-040): `Boton`, `Campo`,
`Tarjeta`, `Aviso`, `Monto`, `TituloPagina`, `TituloSeccion`, `Nota`. Sus estilos están en `ui.module.css` y salen
solo de los tokens de `docs/06-diseno/tokens.css`.

## Qué datos maneja

Ninguno. `Monto` recibe **céntimos enteros** y los formatea en soles (`formatearCentimos`, ADR-033).

## Qué acciones permite

Reglas que estas piezas imponen por construcción:

- `Boton` solo acepta texto como contenido: nunca un ícono solo (Design-System §4), con alto táctil mínimo.
- `Boton` y `Campo` exigen `aiId` por tipo: TypeScript no compila un control sin su `data-ai-id`.
- `Campo` siempre muestra la etiqueta encima y el error en palabras (`role="alert"`).
- `Aviso` comunica con palabras; el color solo acompaña.

## Cómo interactúa la IA

Cada control renderiza `data-ai-id={aiId}`: es el punto de anclaje que usará el Asistente para ubicar y señalar
controles en la pantalla.
