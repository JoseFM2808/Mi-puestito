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

En el primer arranque, si el programa generó el PIN del negocio, lo pide a
`GET /api/auth/primer-ingreso` y lo muestra grande una sola vez (solo llega a la
computadora del programa). «Ya lo anoté» avisa al servidor y lo esconde.

## Qué acciones permite

| Acción                              | Descripción                                     |
| ----------------------------------- | ----------------------------------------------- |
| Elegir cuenta (Demo / negocio real) | Muestra el campo de PIN de esa cuenta           |
| **Ingresar**                        | Valida el PIN y, si es correcto, entra a la app |
| **Ya lo anoté**                     | Esconde el PIN del primer arranque (D-07)       |

## Cómo interactúa la IA

`data-ai-id` disponibles: `login`, `login.cuenta-<usuario>`,
`login.pin-<usuario>`, `login.ingresar-<usuario>`, `login.error`,
`login.pin-nuevo-<usuario>`, `login.pin-anotado-<usuario>`. El AI
Companion no debe rellenar ni leer el campo de PIN ni la tarjeta del PIN
nuevo — es lo único de la app que queda fuera de su alcance.
