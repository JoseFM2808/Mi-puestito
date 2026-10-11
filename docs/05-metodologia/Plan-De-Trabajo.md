# Plan de Trabajo por Fases

#metodologia

> **Tablero de avance del proyecto.** Cada fase tiene una meta clara, una lista
> de tareas y un criterio de cierre. Se actualiza al terminar cada bloque de
> trabajo. Ver [[Metodologia-Desarrollo]] para *cómo* se construye cada tarea.

## Resumen del avance

| Fase | Meta | Estado | Avance |
|---|---|---|---|
| [[#Fase 0 — Demo 1 esqueleto y primera pantalla]] | Que exista algo ejecutable | **Terminada** | 8/8 |
| [[#Fase 1 — Correcciones antes de los datos reales]] | Arreglar lo que después sale caro | **Terminada** | 10/10 |
| [[#Fase 2 — Base técnica sostenible]] | Que crecer no duela | **Terminada** | 6/6 |
| [[#Fase 3 — Módulo Ventas]] | Vender de verdad | En curso | 6/7 |
| [[#Fase 4 — Módulo Compras]] | Comprar de verdad | Pendiente | 1/6 |
| [[#Fase 5 — Offline real y sincronización]] | Que funcione sin internet | En curso | 4/5 |
| [[#Fase 6 — AI Companion]] | El asistente que guía | En curso | 2/6 |
| [[#Fase 7 — Módulos de Fase 2 del producto]] | Inventario, Análisis, Gastos | Pendiente | 0/3 |

**Regla de orden:** la Fase 1 va antes que cualquier módulo nuevo. Sus tareas
son baratas hoy y caras después: tocar el esquema cuando ya hay ventas reales
obliga a migraciones, y un error de fechas o de almacenamiento offline
descubierto en producción significa datos perdidos del vendedor.

---

## Fase 0 — Demo 1: esqueleto y primera pantalla

**Terminada.** Meta: pasar de solo documentación a algo que se pueda abrir.

- [x] Esqueleto frontend: PWA React + TypeScript + Vite + Zustand
- [x] Esqueleto backend: FastAPI + SQLAlchemy + SQLite modular
- [x] `tokens.css` integrado como fuente de verdad visual (sin copia)
- [x] Barra superior fija con Menú, Asistente y selector de tamaño de letra
- [x] [[Modulo-Dashboard]] con datos ficticios y `data-ai-id` en cada elemento
- [x] Esquema inicial de base de datos (ventas, compras, proveedores)
- [x] Aislamiento de fallos en el frontend (`LimiteErrores`) e íconos PWA
- [x] Ejecutable de escritorio para Windows ([[Distribucion-Escritorio]])

---

## Fase 1 — Correcciones antes de los datos reales

**Terminada.** Meta: dejar el cimiento sano **antes** de que exista una sola
venta guardada. Todo lo de esta lista se detectó en una auditoría del código,
se verificó reproduciendo el fallo y quedó cubierto con un test que lo impide
volver.

### Bloqueantes (rompen una regla no negociable)

- [x] **Puerto fijo en la app de escritorio.** Hoy el lanzador pide un puerto
      nuevo en cada arranque. Para el navegador, cada puerto es un **origen
      distinto**: todo lo guardado en IndexedDB, `sessionStorage` y la caché
      de la PWA queda huérfano al reabrir el programa. Esto anula el pilar
      offline-first ([[Sincronizacion-Offline]]) antes de que Dexie exista.
      *Arreglo:* guardar el puerto elegido en la carpeta de datos y reutilizarlo,
      buscando otro solo si está ocupado. → `backend/escritorio.py`
- [x] **Aislamiento de módulos en el backend.** El frontend ya tiene su límite
      de errores; el backend importa y monta todos los módulos sin protección,
      así que un fallo al importar Ventas tumba también Compras, el Dashboard
      y `/api/salud`. Contradice `AGENTS.md` y lo que promete el README del
      Dashboard. *Arreglo:* registro que envuelve cada `include_router` y anota
      el módulo degradado. → `backend/main.py`
- [x] **Índices, restricciones y cascadas en el esquema.** No hay ningún
      `index=`, `unique=`, `cascade` ni `CheckConstraint`. Consecuencias: un
      `Pago` puede quedar sin venta ni cliente (dinero registrado a nadie, y la
      deuda derivada miente), borrar una venta deja items huérfanos, el mismo
      proveedor se registra dos veces con el mismo RUC, y cada tarjeta del
      Dashboard hace un barrido completo de tabla. *Hacerlo ahora evita
      Alembic.* → `backend/modules/*/models.py`

### Correcciones de datos y fechas

- [x] **El backend usa el día del servidor, no el de Perú.** `date.today()` en
      el Dashboard: entre las 19:00 y medianoche de Lima el servidor en UTC ya
      está en el día siguiente, y la tarjeta "Mañana necesitas en caja" cita un
      pedido que la interfaz muestra como "pasado mañana".
      *Arreglo:* helper compartido `dia_peruano()`. → `backend/modules/dashboard/router.py`
- [x] **Un pedido atrasado se muestra como "Llega hoy".** `formatearFechaRelativa`
      manda toda fecha pasada a la rama "hoy". El vendedor cree que una entrega
      vencida llega hoy — justo la señal de caja que debe ser confiable.
      *Arreglo:* rama propia para atrasados. → `frontend/src/modules/dashboard/formato.ts`
- [x] **Tests que se contaminan entre sí.** El test de fechas hace `commit` en
      la base compartida y no limpia; hoy la suite pasa solo porque el orden
      alfabético lo ejecuta después. Con `pytest-randomly`, `-p xdist` o un
      archivo nuevo, CI se rompe sin que nadie toque el código.
      *Arreglo:* transacción por test. → `backend/tests/`

### Correcciones de la app de escritorio y publicación

- [x] **Sin fallback de rutas (SPA).** `GET /` responde 200 pero `GET /ventas`
      responde 404: al llegar el enrutado, recargar o marcar una página fallará.
      *Arreglo:* ruta comodín que devuelve `index.html` fuera de `/api`. → `backend/main.py`
- [x] **El service worker se traga las rutas del API.** Registra un
      `NavigationRoute` a `index.html` sin lista de exclusión y, en el
      ejecutable, API y app comparten origen: navegar a `/api/...` o `/docs`
      devuelve la cáscara de la app. *Arreglo:* `navigateFallbackDenylist`. → `frontend/vite.config.ts`
- [x] **El flujo de Release fallará con 403.** Ningún workflow declara
      `permissions`, y publicar la Release necesita `contents: write`. La ruta
      de descarga documentada en el README se rompería en su primer uso.
      → `.github/workflows/ejecutable-windows.yml`
- [x] **"Volver a intentar" no reintenta nada.** El límite de errores solo baja
      la bandera sin volver a montar el subárbol: ante un error determinista
      (datos locales corruptos, el caso más probable) el mismo panel reaparece
      siempre. *Arreglo:* contador de intento como `key`. → `LimiteErrores.tsx`

**Criterio de cierre cumplido:** 24 tests en el backend y 14 en el frontend,
la suite pasa en cualquier orden, y el ejecutable se verificó de punta a punta
(dos arranques seguidos conservan el puerto, la ruta profunda `/ventas`
responde, el API atraviesa el service worker y el pedido vencido se muestra
como "Debió llegar ayer (atrasado)").

Extras que salieron del mismo trabajo:

- [x] **N+1 en los listados.** `selectinload` + paginación: 5 ventas pasaron de
      6 consultas a 2. → `modules/*/router.py`
- [x] **Claves foráneas activas en SQLite** (`PRAGMA foreign_keys=ON`), sin lo
      cual las cascadas declaradas no se aplicarían.
- [x] **Cobertura de fechas en el frontend** y del límite de errores
      (`@testing-library/react`), los dos huecos que señaló la auditoría.

---

## Fase 2 — Base técnica sostenible

Meta: que sumar el módulo número dos no ensucie al número uno.

- [x] **Tokens tipográficos.** `tokens.css` no materializa la escala de
      [[Design-System]] §2, así que los CSS escriben tamaños a mano mientras su
      comentario dice lo contrario. Añadir `--texto-1..--texto-6` y usar los
      `--esp-*` que ya existen y nadie usa.
- [x] **Aislar los estilos por módulo.** `Dashboard.css` declara nombres
      globalísimos (`.card`, `.btn`, `.monto`, `.nota`). Cuando Ventas traiga su
      propio `.card`, uno reestilará al otro en silencio: un módulo rompiendo a
      otro, que es justo lo prohibido. Decidir **ahora**: CSS Modules o prefijo
      obligatorio por módulo.
- [x] **Una sola copia de la paleta.** Los hexadecimales `#1E6E42` y `#FAF7F2`
      están re-escritos en `vite.config.ts` e `index.html`; generarlos desde
      `tokens.css` o documentar por qué no se puede.
- [x] **Eliminar el bloque duplicado** entre `.btn-secundario` y `.btn-reintentar`.
- [x] **Linters.** No hay ESLint, Prettier ni ruff; nada hace cumplir la regla
      "TypeScript estricto, nada de `any` sin justificar" de `AGENTS.md`.
      Añadirlos y engancharlos al CI.
- [x] **Cerrar la brecha de documentación.** `README.md`, `AGENTS.md` y
      [[Agentes-De-Desarrollo]] describen un directorio `.claude/` (subagente
      revisor, permisos) que **no existe** en el repositorio. Como estos MD son
      el contexto del [[AI-Companion]], el asistente describirá con seguridad
      algo inexistente. Crear los archivos o quitar las referencias.

---

## Fase 3 — Módulo Ventas

Meta: registrar ventas reales. Ver [[Modulo-Ventas]].

- [x] Panel de órdenes activas en paralelo (cards/pestañas, botón "+")
- [x] Registro de venta con descripción manual y búsqueda por nombre
- [x] Fiado: cliente, deuda derivada y límite de crédito opcional
- [x] Venta rápida (solo monto) y su formalización posterior
- [ ] Cierre y pago: efectivo y YAPE/Plin con QR *(cobro hecho; falta el QR, que necesita el número del vendedor)*
- [x] Endpoints de escritura con paginación (evitar el N+1 ya detectado)
- [x] `README.md` del módulo y `data-ai-id` en todo elemento interactivo

---

## Fase 4 — Módulo Compras

Meta: gestionar proveedores y pedidos. Ver [[Modulo-Compras]].

- [ ] Auto-registro del proveedor desde la tablet
- [ ] Creación de orden de pedido con sugerencia de productos frecuentes
- [ ] Checklist de recepción (recibido / no recibido / cambio)
- [ ] Recálculo del monto real a pagar
- [x] Conectar la proyección real del Dashboard ("Mañana necesitas en caja")
- [ ] `README.md` del módulo y `data-ai-id`

---

## Fase 5 — Offline real y sincronización

Meta: cumplir el pilar offline-first con datos reales. Ver [[Sincronizacion-Offline]].

- [x] IndexedDB con Dexie.js (depende del **puerto fijo** de la Fase 1)
- [x] Escritura local primero, sincronización cuando haya red
- [x] Resolución de conflictos y orden por fecha UTC
- [x] Indicador visible de "sin conexión" / "sincronizando"
- [ ] Respaldo y restauración del archivo de datos del vendedor

---

## Fase 6 — AI Companion

Meta: el asistente integrado. Ver [[AI-Companion]] y [[Orquestacion-IA]].

- [x] Capa de abstracción agnóstica al modelo ([[Conexion-Agnostica]])
- [ ] Orquestación con LangGraph
- [ ] Lectura del estado de la UI vía `data-ai-id`
- [ ] Navegación y llenado de formularios guiado *(navegación sugerida hecha, ADR-037; falta el llenado guiado)*
- [x] Explicación de cifras en lenguaje simple
- [ ] Los MD de módulos como contexto en runtime

---

## Fase 7 — Módulos de Fase 2 del producto

- [ ] [[Modulo-Inventario]] — stock, vencimientos, precios
- [ ] [[Modulo-Analisis]] — rentabilidad y reportes
- [ ] [[Modulo-Gastos]] — gastos del puesto y del hogar

---

## Decisiones aplazadas conscientemente

| Tema | Por qué se aplaza | Cuándo decidir |
|---|---|---|
| ~~Dinero en céntimos enteros vs `Numeric`~~ | **Decidido:** céntimos enteros (decisión 35 de [[Decisiones-Tecnicas]]) | Resuelto en la Fase 3 |
| ~~Alembic para migraciones~~ | **Decidido:** Alembic, una base por proyecto (decisión 41) | Resuelto en la Fase 3 |
| Ejecutables de macOS y Linux | La receta ya sirve; falta añadirlos al flujo automático | Cuando haya usuarios que lo pidan |
