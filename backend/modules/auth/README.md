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
primer arranque (o toma `MI_PUESTITO_ANITA_PIN`). El PIN generado **no** se
imprime ni se guarda en claro (D-07, ADR-053): queda solo en memoria y la
pantalla de ingreso lo muestra una vez, únicamente en la misma computadora,
hasta que el dueño toca «Ya lo anoté» o entra con él. `usuarios.json` guarda
solo la marca `pin_por_mostrar`; si el programa se cierra antes, al volver a
abrir se genera otro. En un servidor (`MI_PUESTITO_ENTORNO` distinto de
`local`) no hay pantalla local: ahí se imprime en la consola (mejor fijarlo con
la variable).

## Qué acciones permite

| Endpoint | Descripción |
|---|---|
| `POST /api/auth/ingresar` | `{nombre_usuario, pin}` → `{token, proyecto, nombre_proyecto, es_real}` |
| `GET /api/auth/cuentas` | Cuentas para la pantalla de ingreso, sin secretos |
| `GET /api/auth/primer-ingreso` | PIN generado aún sin anotar; solo a la misma computadora (si no, `[]`) |
| `POST /api/auth/primer-ingreso/{usuario}/anotado` | «Ya lo anoté» (`403` desde otro equipo) |

El token es un valor firmado (HMAC), sin librerías externas: alcanza para una
app de escritorio de un solo dispositivo que solo escucha en `127.0.0.1`
(ver [[Distribucion-Escritorio]]). Dura una jornada de trabajo (12 horas).

## Cómo interactúa la IA

El AI Companion no debe ver PINes ni tokens. Su única relación con este
módulo es indirecta: siempre debe saber en qué proyecto está operando
(`demo` vs `anita`, visible en la barra superior) para no confundir datos de
práctica con datos reales al responder o navegar.
