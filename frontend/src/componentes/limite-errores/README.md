# Componente: Límite de errores

## Qué es

Contenedor que aísla el fallo de un módulo (React error boundary). Materializa
la regla no negociable de `AGENTS.md`: _"Cada módulo es independiente: el fallo
de uno no debe derribar otro"_. Sin él, un error de render en cualquier módulo
dejaría la pantalla en blanco.

## Qué datos maneja

Ninguno del dominio. Solo su propio estado (`hayError`, `intento`) y dos
props: `nombreModulo` (texto que lee el usuario, p. ej. "Caja de hoy") e
`idModulo` (identificador para el AI Companion).

## Qué acciones permite

| Acción                | Descripción                                                          |
| --------------------- | -------------------------------------------------------------------- |
| **Volver a intentar** | Desmonta y vuelve a montar el módulo desde cero, sin recargar la app |

El aviso lleva texto completo (nunca solo un ícono) y usa `--deuda` acompañado
de palabras, respetando la regla del color del Design System.

## Cómo interactúa la IA

- `error-modulo.<idModulo>` — el aviso completo; su presencia le indica al
  AI Companion que ese módulo está caído.
- `error-modulo.<idModulo>.reintentar` — botón de reintento, que la IA puede
  pulsar si el usuario pide "vuelve a intentarlo".

Cuando el Companion detecta este aviso debe explicar en lenguaje simple que
ese módulo no está disponible y que el resto sigue operativo, sin tecnicismos.

## Uso

```tsx
<LimiteErrores nombreModulo="Caja de hoy" idModulo="dashboard">
  <Dashboard />
</LimiteErrores>
```
