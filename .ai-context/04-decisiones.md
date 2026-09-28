# 04 · Decisiones de arquitectura (ADR)

> Solo decisiones formales, técnicas o de negocio. Nada de conversaciones de aprendizaje.
> Las decisiones 1–27 (anteriores a este registro) viven en `docs/02-arquitectura/Decisiones-Tecnicas.md`.
> Las **Aceptadas** también se copian allí. Las **Propuestas** esperan aprobación del responsable antes de tocar código.

| ADR | Fecha | Estado | Decisión |
|---|---|---|---|
| 028 | 2026-09-27 | Aceptada | `tzdata` y `httpx` son dependencias de runtime |
| 029 | 2026-09-27 | Aceptada | El ejecutable empaqueta los módulos con `collect_submodules` y el humo exige `modulos_degradados == []` |
| 030 | 2026-09-27 | Aceptada | Higiene del repo público: `.gitignore` por categorías + test que lo hace cumplir + `.ai-context/` solo técnico |
| 031 | 2026-09-27 | Propuesta | Inventario como libro mayor de movimientos (deltas), no como stock sobreescrito |
| 032 | 2026-09-27 | Propuesta | Cola offline idempotente: `UNIQUE(dispositivo_id, id_operacion)` |
| 033 | 2026-09-27 | Propuesta | Contrato de dinero en JSON como string decimal + un único adaptador en el frontend |
| 034 | 2026-09-27 | Propuesta | Minimizar datos personales en el contexto que va a proveedores de IA externos |

---

## ADR-028 · `tzdata` y `httpx` como dependencias de runtime — Aceptada

- **Contexto**: Windows no trae la base de zonas IANA. `ZoneInfo("America/Lima")` fallaba al importar `fechas.py`, y el aislamiento de módulos lo ocultaba: Dashboard y Asistente quedaban degradados en Windows y `/api/salud` seguía diciendo `ok`. `httpx` estaba listado solo como dependencia de tests, pero `ia/nvidia.py` lo usa en producción.
- **Decisión**: ambos pasan al bloque de runtime de `requirements.txt`. El job de backend del CI corre también en `windows-latest`.
- **Implicaciones**: técnica: el fallo ya no puede volver sin romper CI. Negocio: la caja del día funciona en la PC del puesto (Windows), que es el entorno de producción real.

## ADR-029 · Empaquetado robusto del ejecutable — Aceptada

- **Contexto**: `main.py` carga módulos con `importlib`, y PyInstaller no los ve. La lista a mano en `MiPuestito.spec` se quedó sin `auth` ni `asistente`, así que el `.exe` arrancaba sin login. Además, `escritorio.py` llamaba `ruta_base_datos()` sin proyecto (TypeError antes de levantar el servidor). La prueba de humo del CI no detectaba nada de esto: buscaba el puerto por el PID del lanzador (en un ejecutable de un solo archivo lo abre un proceso hijo) y aceptaba `estado == "ok"` con módulos caídos.
- **Decisión**: `collect_submodules("modules")` y `collect_submodules("ia")` con `backend/` en `sys.path`. `escritorio.main()` informa la carpeta de datos. El humo lee `puerto.txt` y exige `modulos_degradados == []`. Hay un test de regresión: `test_el_arranque_informa_la_carpeta_de_datos_sin_romperse`.
- **Implicaciones**: un módulo nuevo entra al `.exe` sin editar el spec. Verificado en Staging: `.exe` construido localmente, `/api/salud` → `{"estado":"ok","modulos_degradados":[]}`, login demo/anita correcto, 401 sin token.

## ADR-030 · Higiene del repositorio público — Aceptada

- **Contexto**: el repo `JoseFM2808/Mi-puestito` es público. El `.gitignore` no cubría `.env`, llaves, `usuarios.json` (hash + sal de PIN, se crea en `backend/` en desarrollo), actas internas ni el estado personal de Obsidian (`.obsidian/workspace.json` estaba versionado).
- **Decisión**:
  1. `.gitignore` por categorías: secretos, llaves, credenciales de la app, BD, datos de negocio, actas/acuerdos, logs, herramientas locales.
  2. `backend/tests/test_higiene_repo.py` revisa `git ls-files` (rutas prohibidas + formas de llaves `nvapi-`, `sk-ant-`, `sk-`, `AKIA`, `ghp_`, `PRIVATE KEY`) y rompe CI.
  3. Plantilla `config/.env.example` sin valores (el código trata una variable vacía como ausente: `MI_PUESTITO_SECRETO=` vacío firmaba tokens con llave vacía); `config/.env.staging` y `config/.env.production` quedan ignorados.
  4. `.ai-context/` contiene **solo** arquitectura técnica. Lo privado va en `.ai-context/privado/` (ignorado).
- **Implicaciones**: negocio: cumple el deber de confidencialidad de la Ley 29733 sobre datos del vendedor. Técnica: ningún secreto nuevo puede llegar a `main` sin que falle un test.

## ADR-031 · Inventario como libro mayor de movimientos — Propuesta

- **Contexto**: el módulo Inventario (Fase 7) guardará stock. La regla actual de sincronización es *last-write-wins*. Con LWW, dos dispositivos (o la cola offline) que descuentan stock sobre la misma fila **pierden descuentos**. El patrón leer→restar→escribir en Python también pierde actualizaciones entre peticiones concurrentes.
- **Decisión propuesta**: tabla `movimientos_inventario` de solo inserción (`delta` ±). `productos.stock_actual` es una caché que se actualiza con `stock_actual = stock_actual + :delta` en la **misma transacción** (`BEGIN IMMEDIATE` en SQLite; `SELECT … FOR UPDATE` o el incremento atómico en PostgreSQL). Una venta **nunca se rechaza** por stock negativo: se marca un "descuadre" (la venta ya ocurrió físicamente). LWW queda solo para datos maestros.
- **Alternativas**: stock como columna con LWW (pierde datos); bloqueo optimista con `version` (rechaza ventas offline legítimas); CRDT PN-Counter (equivalente, más complejo).
- **Implicaciones**: técnica: los movimientos son conmutativos e idempotentes, así que la sincronización es segura en cualquier orden. Negocio: la vendedora ve por qué cambió el stock (auditoría) y el conteo físico se vuelve un "ajuste".
- **Requiere**: actualizar `docs/02-arquitectura/Sincronizacion-Offline.md` (excepción a LWW) y `docs/03-modulos/Modulo-Inventario.md`.

## ADR-032 · Cola offline idempotente — Propuesta

- **Contexto**: las operaciones hechas sin red se reintentan. Sin clave de idempotencia, un reintento después de un timeout duplica la venta y el dinero en caja.
- **Decisión propuesta**: cada operación lleva `id_operacion` (UUIDv7, ordenable por tiempo) generado en la tablet + `dispositivo_id`. El servidor guarda `(dispositivo_id, id_operacion)` como PK en `operaciones_aplicadas` dentro de la misma transacción. Un duplicado responde `200 ya_aplicada` sin efectos.
- **Implicaciones**: "Cerrar orden" responde al instante en la tablet. El servidor es la fuente de verdad sin riesgo de doble conteo.

## ADR-033 · Contrato de dinero en JSON — Propuesta

- **Contexto**: Pydantic v2 serializa `Decimal` como string (`"485.50"`, verificado en Staging). El frontend tipa `monto: number` en camelCase (`ventasHoy`) y el backend expone snake_case (`ventas_hoy`). Hoy no chocan solo porque el Dashboard aún usa `datos-ficticios.ts`.
- **Decisión propuesta**: se mantiene el string decimal en el cable, porque `float` redondea céntimos. En el frontend, un único módulo `api/contrato.ts` convierte snake→camel y string→número de céntimos (entero), y todo cálculo se hace en céntimos. Tipos generados desde `/openapi.json` para no desincronizar.
- **Implicaciones**: se eliminan errores de redondeo en caja y hay una sola frontera de conversión.

## ADR-034 · Datos personales en el contexto de IA — Propuesta

- **Contexto**: el Asistente envía `ResumenDashboard` a NVIDIA NIM (tercero, fuera del Perú), que incluye nombres de clientes con fiado y montos de deuda. Son datos personales bajo la Ley 29733.
- **Decisión propuesta**: seudonimizar antes de salir de `ia/` (p. ej. "Cliente A") y re-identificar solo en la respuesta local. Aviso de consentimiento en el primer uso del Asistente en un proyecto `es_real`. Preferir un modelo local cuando exista (ya soportado por el `ProveedorIA` Protocol).
- **Implicaciones**: se conserva la utilidad del Asistente sin transferir datos identificables de clientes.
