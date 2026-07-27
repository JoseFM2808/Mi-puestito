# Módulo backend: Auth (login)

## Qué es

Login simple por usuario + PIN. Cada usuario está ligado a **un solo
proyecto** (`demo` o `anita`): el token que se entrega solo abre la base de
datos de ese proyecto, nunca la de otro. No hay registro de cuentas desde la
app — las cuentas se crean solas al primer arranque (`seguridad.py`).

## Qué datos maneja

Ninguna tabla del esquema de negocio. Guarda un archivo `usuarios.json` (en
la carpeta de datos, fuera del repo) con el PIN **con hash** de cada cuenta,
nunca en claro. La cuenta `demo` usa un PIN fijo y público (`0000`, no
protege nada real); la cuenta del proyecto real genera su PIN al azar en el
primer arranque (o toma `MI_PUESTITO_ANITA_PIN`) y lo imprime una sola vez en
la consola.

## Qué acciones permite

| Endpoint | Descripción |
|---|---|
| `POST /api/auth/ingresar` | `{nombre_usuario, pin}` → `{token, proyecto, nombre_proyecto, es_real}` |

El token es un valor firmado (HMAC), sin librerías externas: alcanza para una
app de escritorio de un solo dispositivo que solo escucha en `127.0.0.1`
(ver [[Distribucion-Escritorio]]). Dura una jornada de trabajo (12 horas).

## Cómo interactúa la IA

El AI Companion no debe ver PINes ni tokens. Su única relación con este
módulo es indirecta: siempre debe saber en qué proyecto está operando
(`demo` vs `anita`, visible en la barra superior) para no confundir datos de
práctica con datos reales al responder o navegar.
