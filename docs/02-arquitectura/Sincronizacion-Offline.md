# Sincronización Offline-First

#arquitectura

> **Fechas:** todas se guardan en UTC con zona horaria explícita (tipo
> `FechaHoraUTC` en `backend/database.py`, decisión 21 de
> [[Decisiones-Tecnicas]]). Es requisito para que la sincronización pueda
> comparar y ordenar registros entre el dispositivo y la nube sin ambigüedad.

La conectividad en mercados peruanos es variable. El sistema **nunca** puede bloquear una venta o una compra por falta de red.

## Estrategia

- **Últimas ~2 semanas** de datos (ventas, compras, sesiones) viven localmente en el dispositivo (IndexedDB).
- **Histórico anterior** vive en la nube y se solicita bajo demanda.
- **Cola de sincronización (implementada):** `frontend/src/sincronizacion/cola.ts` guarda cada operación en IndexedDB antes de enviarla y la procesa en orden; sin red espera, un rechazo del servidor se muestra al operador en palabras. Cada entidad lleva un `uuid` generado en la tablet, así que reenviar nunca duplica (decisión 32 de [[Decisiones-Tecnicas]]).
- **La hora real viaja con la operación** (`ocurrido_en`): una venta hecha sin red a las 10:00 cuenta a las 10:00.
- **Conflictos:** last-write-wins **solo para datos maestros** (nombre o teléfono de un cliente, precio de un producto). El stock **no** usa LWW: es un libro de movimientos que se suman en cualquier orden (decisión 31, [[Modulo-Inventario]]).

## Reglas

1. Ninguna funcionalidad core ([[Modulo-Ventas]], [[Modulo-Compras]]) puede requerir conexión para operar.
2. El usuario debe poder ver con agilidad todo lo ocurrido en la semana actual y la anterior sin tocar la nube.
3. La fecha/hora se detecta automáticamente por zona horaria (Perú, UTC-5); el usuario nunca la digita.
