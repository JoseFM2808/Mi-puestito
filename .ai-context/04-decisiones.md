# 04 · Decisiones de arquitectura (ADR)

> Solo decisiones formales, técnicas o de negocio. Nada de conversaciones de aprendizaje.
> Las decisiones 1–27 (anteriores a este registro) viven en `docs/02-arquitectura/Decisiones-Tecnicas.md`.
> Las **Aceptadas** también se copian allí. Las **Propuestas** esperan aprobación antes de tocar código.

| ADR | Fecha | Estado | Decisión |
|---|---|---|---|
| 028 | 2026-09-27 | Aceptada | `tzdata` y `httpx` son dependencias de runtime |
| 029 | 2026-09-27 | Aceptada | El ejecutable empaqueta los módulos con `collect_submodules` y el humo exige `modulos_degradados == []` |
| 030 | 2026-09-27 | Aceptada | Higiene del repo público: `.gitignore` por categorías + test que lo hace cumplir + `.ai-context/` solo técnico |
| 031 | 2026-09-28 | Aceptada | Inventario como libro mayor de movimientos con incremento atómico |
| 032 | 2026-09-28 | Aceptada | Idempotencia por `uuid` del dispositivo en cada entidad + cola FIFO en IndexedDB |
| 033 | 2026-09-28 | Aceptada | Dinero como string decimal en el cable y céntimos enteros en el frontend |
| 034 | 2026-09-28 | Aceptada | Seudonimizar todo lo que sale hacia un proveedor de IA |
| 035 | 2026-09-28 | Aceptada | Dinero en céntimos enteros en la base de datos (tipos `Dinero` y `Cantidad`) |
| 036 | 2026-10-08 | Aceptada | Proveedor de IA genérico compatible con OpenAI y orden de modelos verificado con la llave del operador |
| 037 | 2026-10-08 | Aceptada | El Asistente sugiere acciones con una línea de texto de lista blanca; nunca las ejecuta |
| 038 | 2026-10-08 | Aceptada | Registro opt-in y seudonimizado de intercambios para entrenar un modelo propio |
| 039 | 2026-10-08 | Propuesta | Fine-tuning LoRA de un Gemma 4 pequeño para correr en el dispositivo |
| 040 | 2026-09-28 | Aceptada | Estilos aislados con CSS Modules y piezas base compartidas en `src/ui` |
| 041 | 2026-09-28 | Aceptada | Migraciones con Alembic, una base por proyecto |

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

## ADR-031 · Inventario como libro mayor de movimientos — Aceptada

- **Contexto**: la regla de sincronización era *last-write-wins*. Con LWW, dos dispositivos (o la cola offline) que
  descuentan stock sobre la misma fila **pierden descuentos**. El patrón leer→restar→escribir en Python también pierde
  actualizaciones entre peticiones concurrentes.
- **Decisión**: `movimientos_inventario` de solo inserción (`delta` ±, `UNIQUE(origen_tipo, origen_ref)`).
  `productos.stock_actual` es una caché que solo cambia `registrar_movimiento`, con `stock_actual = stock_actual + :delta`
  en la misma transacción. Una venta **nunca se rechaza** por stock negativo: se avisa el descuadre. Ventas avisa a
  Inventario por `eventos.py`; el suscriptor corre en un SAVEPOINT, así un fallo de Inventario no tumba la venta.
- **Consecuencias**: sincronización segura en cualquier orden; historial de por qué cambió el stock; el conteo físico es
  un ajuste. Verificado con 40 ventas en paralelo y control negativo (`tests/test_inventario.py`). LWW queda solo para
  datos maestros.

## ADR-032 · Idempotencia por uuid del dispositivo — Aceptada

- **Contexto**: las operaciones hechas sin red se reintentan; sin clave, un reintento tras un timeout duplica la venta.
  La propuesta inicial era una tabla `operaciones_aplicadas(dispositivo_id, id_operacion)`.
- **Decisión**: más simple y sin tabla extra. Cada entidad que crea la tablet (cliente, venta, item, abono, producto,
  ajuste) lleva un `uuid` generado en el dispositivo, único en su tabla: crear con un uuid existente devuelve la fila
  existente (`200`); cobrar o fiar algo ya cerrado devuelve el estado actual. El pago de un cobro reutiliza el uuid de la
  venta. En el frontend, `sincronizacion/cola.ts` guarda cada operación en IndexedDB antes de enviarla y la procesa FIFO.
- **Consecuencias**: "Cerrar orden" responde al instante; el servidor es la fuente de verdad sin doble conteo. Verificado
  en navegador con el servidor apagado, recarga de página y sesión vencida.

## ADR-033 · Contrato de dinero en JSON — Aceptada

- **Contexto**: Pydantic v2 serializa `Decimal` como string; el frontend tipaba `number` y usaba camelCase.
- **Decisión**: en el cable, string decimal (`"485.50"`) y snake_case. `frontend/src/api/contrato.ts` es la única
  frontera: convierte a céntimos enteros y camelCase. Las listas de campos se comparan con `openapi.json` (tests en ambos
  lados).
- **Consecuencias**: sin errores de redondeo en caja; un cambio de esquema que no se refleja del otro lado rompe un test.

## ADR-034 · Datos personales en el contexto de IA — Aceptada

- **Contexto**: el Asistente envía el resumen de caja a un tercero (NVIDIA NIM), con nombres de clientes y deudas
  (Ley 29733).
- **Decisión**: `ia/privacidad.py` cambia nombres por alias ("Cliente 1", "Proveedor A") en el resumen, la pregunta y el
  historial, y los restituye solo en la respuesta local. En negocios reales la UI lo explica en palabras simples.
- **Consecuencias**: el Asistente sigue siendo útil (las cifras viajan) sin transferir datos identificables.

## ADR-035 · Dinero en céntimos enteros en la base — Aceptada

- **Contexto**: decisión aplazada en el Plan de Trabajo "hasta Ventas real": SQLite guarda `NUMERIC` como coma flotante.
- **Decisión**: tipos `Dinero` (céntimos) y `Cantidad` (milésimas) en `database.py`: `INTEGER` en SQL, `Decimal` en
  Python. La migración 0002 convierte los datos existentes antes de cambiar el tipo.
- **Consecuencias**: sumas exactas también en `SUM()`. `SUM()` hereda el tipo y ya devuelve soles (se cubrió con test tras
  detectar una doble conversión).

## ADR-036 · Proveedor de IA genérico y modelos verificados — Aceptada

- **Contexto**: el código estaba escrito para NVIDIA y su lista de modelos por defecto ya no existía en el catálogo
  (verificado el 2026-10-08 con `GET /v1/models`): con una llave real, el Asistente habría fallado. Además, la meta es
  correr un modelo muy pequeño (familia Gemma 4) en el dispositivo.
- **Decisión**: `ia/compatible_openai.py` habla con cualquier API compatible con OpenAI (NVIDIA NIM, Ollama, llama.cpp,
  vLLM) con `httpx`; `ia/configuracion.py` elige proveedor, URL, llave y orden de modelos por variables de entorno.
  `python -m ia.verificar` prueba los candidatos con la llave del operador **usando el prompt real del Asistente** y
  guarda en `ia_modelos.json` (solo nombres y latencias): primero los que responden **bien** y en ≤ 600 caracteres, del
  más rápido al más lento; los que responden mal o devuelven su razonamiento no se usan. Los modelos de razonamiento
  llevan un ajuste por familia (`AJUSTES_POR_FAMILIA`: Nemotron `enable_thinking: false`, gpt-oss
  `reasoning_effort: low`) y `compatible_openai.py` descarta cualquier respuesta que sea un borrador.
- **Medición del 2026-10-08/10 con la llave del owner**: `nemotron-3.5-lightning-30b-a3b` 1.7 s ✅,
  `gpt-oss-20b` 2.1 s ✅; `gemma-4-31b-it` no respondió en 30 s. Sin ajustes, Nemotron devolvía su borrador en inglés
  cortado por `max_tokens`, y gpt-oss sumó mal (S/ 75 en vez de S/ 165) con el prompt corto: por eso la verificación
  exige la respuesta correcta y no solo velocidad.
- **Consecuencias**: pasar a un modelo local es cambiar `MI_PUESTITO_IA_PROVEEDOR=local` y el nombre del modelo. El
  catálogo puede cambiar sin tocar código. La llave solo vive en variables de entorno. Gemma 4 queda de respaldo hasta
  que responda a tiempo (sigue siendo la familia objetivo para el modelo local).
- **Actualización 2026-11-01**: la llave también puede guardarse desde la pantalla (ADR-043). El orden pasa a ser
  `nemotron-3.5-bolt-e4b`, `nemotron-3.5-lightning-30b-a3b`, `gemma-4-31b-it`: `ordenar` conserva la preferencia entre los
  que aciertan a tiempo, y `python -m ia.evaluar` decide esa preferencia con casos reales. Medición: Bolt 18/18 y 19/19 en
  sus mejores corridas, 17/18 en otras, mediana ~1,4 s; Lightning 16/18. `gpt-oss-20b` y `gemma-4-31b-it` no responden a
  tiempo hoy. Bolt da 404 intermitentes: los códigos transitorios se reintentan antes de pasar al siguiente modelo.

## ADR-037 · Acciones sugeridas por el Asistente — Aceptada

- **Contexto**: la Fase 6 pide que el Asistente guíe y navegue la UI, pero sin ejecutar nada por el operador.
- **Decisión**: el modelo termina con `ACCION: ir_a <pantalla>`; `ia/acciones.py` acepta solo `caja`, `ventas`, `fiados`
  (máximo 2) y el frontend los muestra como botones con texto completo. Se prefirió una línea de texto a *tool calling*:
  los modelos muy pequeños la siguen mejor y es trivial de enseñar con fine-tuning.
  Red de seguridad (2026-10-10): si el modelo no escribe la línea pero dice "ve a la pantalla fiados", igual se ofrece
  el botón; Nemotron olvidaba el formato y los modelos pequeños lo harán más.
- **Consecuencias**: el modelo no puede inducir acciones fuera de la lista; ampliar el catálogo es agregar entradas a
  `PANTALLAS` y al prompt.

## ADR-038 · Registro para entrenar un modelo propio — Aceptada

- **Contexto**: para que un Gemma pequeño en la tablet responda como el Asistente hacen falta ejemplos reales de uso.
- **Decisión**: `ia/registro.py` guarda, solo si `MI_PUESTITO_IA_REGISTRO` lo activa (`demo` = solo práctica; `todos`
  requiere consentimiento del vendedor), cada intercambio en formato chat (system/user/assistant) **ya seudonimizado**,
  más la valoración "Me sirvió" / "No me sirvió". Vive en la carpeta de datos (`*.jsonl`, ignorado y vigilado).
- **Consecuencias**: dataset listo para SFT sin datos personales. Staging lo activa en modo `demo`.

## ADR-039 · Fine-tuning de un Gemma 4 pequeño en el dispositivo — Propuesta

- **Contexto**: el puesto puede no tener red; el Asistente hoy la necesita.
- **Propuesta**: con el dataset de ADR-038 (filtrado por valoraciones positivas), entrenar un LoRA sobre la variante más
  pequeña de Gemma 4 disponible, cuantizarlo (GGUF de 4 bits) y servirlo con llama.cpp u Ollama mediante
  `MI_PUESTITO_IA_PROVEEDOR=local`. Evaluar contra un set fijo de preguntas (cifras exactas, uso correcto de `ACCION`,
  sin inventar) antes de reemplazar a la nube.
- **Pendiente de decidir**: tamaño mínimo aceptable en la tablet objetivo, licencia del modelo y dónde se entrena.

## ADR-040 · Estilos aislados con CSS Modules — Aceptada

- **Contexto**: la Fase 2 exigía decidir "CSS Modules o prefijo obligatorio": `Dashboard.css` declaraba `.card` y `.btn`
  globales y `Login.css` dependía de ellos.
- **Decisión**: CSS Modules en todos los módulos y piezas base compartidas (`Boton`, `Campo`, `Monto`, `Aviso`,
  `Tarjeta`) en `frontend/src/ui/`, con `aiId` obligatorio por tipo. Un test impide CSS global nuevo y colores escritos a
  mano.
- **Consecuencias**: un módulo ya no puede reestilar a otro; la regla "texto sobre íconos" y el tamaño táctil viven en un
  solo lugar.

## ADR-041 · Migraciones con Alembic, una base por proyecto — Aceptada

- **Contexto**: `create_all` no sirve cuando hay datos reales que preservar.
- **Decisión**: `backend/migraciones/` con un historial único para todos los módulos; `ejecutar.migrar()` corre al
  arrancar en cada base, marca en 0001 las bases creadas antes de Alembic y apaga las claves foráneas durante la
  migración (el modo batch de SQLite recrea tablas y, con FK activas, dispararía `ON DELETE CASCADE`).
- **Consecuencias**: verificado sobre la carpeta de datos del `.exe` anterior: migra sin perder items.

## ADR-042 · Verificador de cifras en el servidor — Aceptada

- **Fecha**: 2026-11-01.
- **Contexto**: en la evaluación con NVIDIA, Nemotron inventó montos ("S/ 130.00", "S/ 12.50") con las reglas del prompt ya
  puestas. En una caja, un monto falso hace más daño que no responder, y un modelo pequeño lo hará más.
- **Decisión**: `ia/cifras.py` compara cada monto de la respuesta con el contexto enviado y con lo dicho por el operador. Si
  no aparece, se prueba el siguiente modelo; si ninguno pasa, se responde un mensaje fijo con el botón a la Caja y el modelo
  queda como `verificador-de-cifras`. La aritmética solo se acepta con cifras que dijo el operador.
- **Consecuencias**: el modelo puede fallar sin que el operador vea una cifra falsa. Puede rechazar de más una suma correcta
  no prevista: ese es el lado seguro. Esas respuestas de respaldo no entran al dataset de fine-tuning.

## ADR-043 · Llave de IA guardada con DPAPI desde la pantalla — Aceptada

- **Fecha**: 2026-11-01.
- **Contexto**: un vendedor no sabe configurar variables de entorno, y sin llave no hay Asistente en el `.exe` (D-14). La llave
  es un secreto con costo asociado: no puede quedar en claro ni devolverse por la API.
- **Decisión**: el panel del Asistente la pide si falta, la prueba con un saludo al proveedor (solo 401/403 la rechaza; sin
  red se guarda igual) y `ia/llave_local.py` la cifra con DPAPI en `ia_llave.dpapi`, ligada a la cuenta de Windows. Solo en modo
  local, proveedor NVIDIA, Windows y **desde la misma computadora**: el PIN de demo es público y no debe permitir reemplazarla
  desde otro equipo. La variable de entorno sigue mandando. El esquema de entrada no valida con Pydantic para que un `422` no
  repita la llave en su respuesta; el frontend la envía directo, nunca por la cola offline.
- **Consecuencias**: copiar el archivo a otra PC o cuenta no sirve. Reinstalar Windows obliga a escribirla de nuevo. Otro
  programa corriendo con la misma cuenta de Windows podría descifrarla: es el límite conocido de DPAPI. Fuera de Windows se
  sigue usando la variable.

## ADR-044 · Respaldo con la API de SQLite y copias que saben de qué negocio son — Aceptada

- **Fecha**: 2026-11-01.
- **Contexto**: los datos del vendedor viven en un archivo de su computadora (Fase 5). Copiarlo a mano con WAL puede perder lo
  último, restaurar la copia equivocada borraría ventas reales, y un archivo recibido no es de confianza.
- **Decisión**: la copia sale de `Connection.backup` y lleva una tabla `respaldo_info` con el proyecto. Antes de tocar nada se
  revisa cabecera, `integrity_check`, tablas necesarias, ausencia de triggers y vistas, proyecto y revisión conocida. Lo actual
  se guarda en `respaldos/`; si falla la migración, se vuelve a ello. Las rutas viven en un módulo propio y solo con SQLite.
- **Consecuencias**: la práctica no puede pisar un negocio real. Una copia de una versión anterior se migra; una más nueva se
  rechaza. La copia va sin cifrar (D-23) y no incluye PIN, llave ni secreto: en otra PC hay PIN nuevos. `respaldos/` no se limpia
  sola, a propósito.

## ADR-045 · Recepción de compras inmutable y stock solo con cantidad explícita — Aceptada

- **Fecha**: 2026-11-01.
- **Contexto**: la recepción mueve stock y dinero, y la cola offline puede reenviarla. La cantidad del pedido es texto libre
  ("2 packs"), que no equivale a unidades de inventario.
- **Decisión**: un ítem confirmado no se reescribe: la misma confirmación es un no-op y otra distinta da `409`. El evento
  `compra.item_recibido` suma al stock solo si llega `cantidad_stock`, y la pantalla solo la pregunta si el producto existe en
  Inventario. Compras identifica el producto por nombre, único en el sistema, sin clave foránea entre módulos. Se agregan `uuid`
  a proveedores, órdenes e ítems (migración 0004) y la API deja de exponer sus ids enteros.
- **Consecuencias**: reenviar no duplica stock. Un error de recepción se corrige con un ajuste de Inventario, que aún no tiene
  pantalla (D-22). Compras sigue funcionando sin Inventario.

