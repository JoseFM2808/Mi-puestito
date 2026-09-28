# 01 · Lógica del sistema

> Flujos transaccionales, lógica de inventario y cobro. Última revisión: 2026-09-27.
> Leyenda: **[Implementado]** existe en `main` · **[Propuesto]** diseño aprobable, aún sin código.
> Fuente funcional: `docs/03-modulos/Modulo-Ventas.md`, `Modulo-Inventario.md`, `docs/02-arquitectura/Sincronizacion-Offline.md`.

## 1. Ciclo de vida de una venta [Implementado: esquema · Propuesto: escritura]

Tres tipos (`TipoVenta`) comparten tabla `ventas`. El estado vive en `EstadoVenta`.

```mermaid
stateDiagram-v2
    [*] --> abierta: orden_activa / fiado
    [*] --> pendiente_formalizar: venta_rapida (solo monto)
    abierta --> abierta: agregar item (recalcula monto_total)
    abierta --> pagada_cerrada: cobrar (efectivo | yape_plin)
    abierta --> abierta: fiado → queda como deuda derivada
    pendiente_formalizar --> pagada_cerrada: formalizar (agrega items)
    pagada_cerrada --> [*]
```

Reglas de integridad:

- `monto_total` **siempre** lo calcula el servidor como Σ `items_venta.monto`, en la misma transacción que inserta el item. Nunca se acepta del cliente.
- Un fiado exige `cliente_id` (`ck_fiado_requiere_cliente`).
- La deuda de un cliente se **deriva**: Σ ventas fiado − Σ pagos. No existe columna `deuda`.
- Todo `Pago` tiene destino: venta o cliente (`ck_pago_tiene_destino`).

## 2. Cobro offline-first con cola idempotente [Propuesto — ADR-032]

La venta ocurre en la tablet aunque no haya red. El servidor **no puede rechazar** una venta que ya ocurrió en el mundo físico. Solo registra y avisa.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operadora
    participant UI as PWA (React)
    participant IDB as IndexedDB (Dexie)
    participant API as FastAPI /api/ventas
    participant BD as SQLite / PostgreSQL

    Op->>UI: Toca "Cerrar orden" (efectivo)
    UI->>IDB: guarda venta + id_operacion (UUIDv7) en cola
    UI-->>Op: "Venta registrada" (sin esperar red)
    loop Mientras haya pendientes y red
        IDB->>API: POST /operaciones {id_operacion, dispositivo_id, payload}
        API->>BD: BEGIN (IMMEDIATE en SQLite)
        alt id_operacion ya existe (reintento)
            BD-->>API: UNIQUE(dispositivo_id,id_operacion) choca
            API-->>IDB: 200 {estado: "ya_aplicada"} → se borra de la cola
        else nueva
            API->>BD: INSERT venta + items (monto_total = Σ items)
            API->>BD: INSERT movimientos_inventario (−cantidad) si hay producto
            API->>BD: UPDATE productos SET stock_actual = stock_actual + delta
            API->>BD: COMMIT
            API-->>IDB: 201 → se borra de la cola
        end
    end
```

## 3. Lógica de inventario: libro mayor de movimientos [Propuesto — ADR-031]

El stock **no es un número que se sobreescribe**. Es la suma de un libro de movimientos que solo crece.

| Evento | Movimiento | Origen |
|---|---|---|
| Compra recibida (checklist) | `+cantidad` por ítem `recibido`/`cambiado` | Compras |
| Venta con producto | `−cantidad` | Ventas |
| Conteo físico | `ajuste` = contado − calculado | Inventario |
| Merma / vencido | `−cantidad` con motivo | Inventario |

```mermaid
flowchart TD
    A[Operación llega con id_operacion] --> B{¿Ya aplicada?<br/>UNIQUE dispositivo_id+id_operacion}
    B -- Sí --> Z[Responder ya_aplicada<br/>sin tocar stock]
    B -- No --> C[BEGIN IMMEDIATE / SELECT ... FOR UPDATE en PG]
    C --> D[INSERT movimiento delta]
    D --> E["UPDATE productos<br/>SET stock_actual = stock_actual + :delta<br/>(incremento atómico, sin leer antes)"]
    E --> F{stock_actual &lt; 0?}
    F -- Sí --> G[Marcar alerta 'descuadre'<br/>NO se rechaza la venta]
    F -- No --> H[COMMIT]
    G --> H
```

Por qué así (auditoría de condiciones de carrera):

1. **Actualización perdida**: el patrón *leer stock → restar en Python → escribir* pierde ventas cuando dos peticiones se cruzan. Se usa `stock_actual = stock_actual + :delta` en SQL, que es atómico en SQLite y PostgreSQL.
2. **Sincronización con last-write-wins** (la regla actual de `Sincronizacion-Offline.md`) destruiría los descuentos de stock hechos sin red. Los movimientos son **conmutativos**: se pueden aplicar en cualquier orden y el total es el mismo. LWW sigue siendo válido para datos maestros (nombre de cliente, precio).
3. **Doble envío por reintento**: la clave `UNIQUE(dispositivo_id, id_operacion)` hace la operación idempotente.
4. **Fuente de verdad**: `stock_actual` es una caché. Un job de conciliación recalcula `Σ movimientos` y avisa si difiere.

## 4. Recepción de compras [Implementado: esquema]

```mermaid
flowchart LR
    B[borrador] --> P[pendiente] --> C[en_camino] --> R[recibida] --> X[cerrada]
    R -. checklist por ítem .-> I{estado_recepcion}
    I -->|recibido| S1[+stock]
    I -->|cambiado| S2[+stock del sustituto<br/>monto_sustituto]
    I -->|no_recibido| S3[sin movimiento]
    R --> M[monto_real = Σ recibido + Σ sustitutos]
```

## 5. Asistente (AI Companion) en una consulta [Implementado]

```mermaid
sequenceDiagram
    participant UI as Asistente.tsx
    participant R as /api/asistente/preguntar
    participant D as dashboard.obtener_resumen
    participant S as ia.servicio
    participant P as Proveedor (NVIDIA NIM hoy)
    UI->>R: {mensaje} + Bearer token
    R->>D: resumen SOLO del proyecto del token
    R->>S: preguntar(mensaje, contexto_json)
    loop modelos por prioridad (3b → 8b → 8x22b)
        S->>P: chat/completions (timeout 8 s)
        P-->>S: texto o error → siguiente modelo
    end
    S-->>R: primera respuesta a tiempo
    R-->>UI: {respuesta} | 503 AsistenteNoDisponible
```
