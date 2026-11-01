# Componente: Login

## Qué es

Pantalla de ingreso por usuario + PIN. Es la puerta de entrada de la app: sin
sesión iniciada no se ve ningún dato (ni siquiera el de demo). Cada cuenta
abre **un solo proyecto** — nunca hay forma de mezclar datos de práctica con
los del negocio real.

## Qué datos maneja

Solo el PIN que el operador escribe (no se guarda en el frontend). Llama a
`POST /api/auth/ingresar`; si es correcto, el token y el proyecto quedan en
`src/stores/sesion.ts` (persistido en `sessionStorage`, dura la sesión).

## Qué acciones permite

| Acción                              | Descripción                                     |
| ----------------------------------- | ----------------------------------------------- |
| Elegir cuenta (Demo / negocio real) | Muestra el campo de PIN de esa cuenta           |
| **Ingresar**                        | Valida el PIN y, si es correcto, entra a la app |

## Cómo interactúa la IA

`data-ai-id` disponibles: `login`, `login.cuenta-<usuario>`,
`login.pin-<usuario>`, `login.ingresar-<usuario>`, `login.error`. El AI
Companion no debe rellenar ni leer el campo de PIN — es lo único de la app
que queda fuera de su alcance.
