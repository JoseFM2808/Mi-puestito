# 05 · Deuda técnica e higiene del repositorio

> Última revisión: 2026-11-22 · rama `claude/loving-albattani-qxwm6d`.
> Prioridad: **P1** antes de usar el negocio real · **P2** antes de la nube · **P3** mejora continua.

## 1. Pendientes

| ID | P | Hallazgo | Riesgo | Propuesta | Relación |
|---|---|---|---|---|---|
| D-08 | P2 | El registro de proyectos (`backend/proyectos.py`) tiene el nombre de un negocio real en código público | Exposición de identidad del cliente; dar de alta un negocio exige una versión nueva | Pantalla de alta de negocio + `proyectos.json` en la carpeta de datos (ignorado). El owner pidió opciones (2026-11-17). Los datos del vendedor incluirán su número de Yape/Plin para el QR | ADR-030 |
| D-12 | P2 | Falta activar en GitHub *Secret scanning + Push protection* | gitleaks en CI lo detecta, pero después de publicado; push protection lo impide antes | Lo activa el owner en Settings → Code security | ADR-030 |
| D-15 | P2 | El Asistente necesita internet | Sin red no hay ayuda | **Decidido (owner, 2026-11-17):** modelo local ultraligero (una versión mínima de Gemma o un modelo tipo "colibrí") que corra en una computadora de pocos recursos, servido con Ollama/llama.cpp; luego fine-tuning | ADR-039 |
| D-21 | P3 | El RUC se escribe a mano | Un RUC válido en forma pero inexistente pasa | Búsqueda en SUNAT: requiere elegir un servicio externo. **Pospuesto por el owner (2026-11-17)** | `Modulo-Compras.md` |
| D-23 | P2 | La copia de respaldo va sin cifrar | Quien tenga el archivo ve clientes, fiados y ventas | Cifrar con una contraseña que elija el vendedor. **Decidido (owner, 2026-11-17):** si la olvida, se le envía un enlace a su Gmail mediante una conexión con Google Cloud. Falta que el owner cree el proyecto de Google Cloud (credenciales OAuth / API de Gmail) | ADR-044 |
| D-31 | P2 | Lo nuevo del Asistente (recordar, pedidos a proveedores, señalar campos de la pantalla, manual de los README, grafo de LangGraph) solo se probó con un modelo falso | Un modelo real puede no usar bien `RECORDAR`, `COMPRA` o `resaltar <id visible>` | Correr `python -m ia.evaluar` con la llave en Staging (`scripts/staging-con-ia.ps1`): 38 casos, 5 nuevos. Necesita la llave del owner | ADR-052, 055, 056, 057 |
| D-32 | P2 | El `.exe` con LangGraph (~90 MB) solo se construyó en Linux | Un import que PyInstaller no recoja en Windows dejaría al Asistente en el recorrido simple (no se cae, pero no usa el grafo) | Correr el flujo `Ejecutable Windows` y revisar `/api/salud` y el log. Bloqueado: esta sesión no pudo publicar la rama en GitHub (403) | ADR-057 |

## 2. Hechos

| ID | Fecha | Qué se resolvió | Evidencia |
|---|---|---|---|
| D-01 | 2026-09-28 | El Dashboard muestra las cifras reales del proyecto (`GET /api/dashboard/resumen`) | Navegador: demo S/ 485.50 → 508.50 al cobrar |
| D-02 | 2026-09-28 | SQLite con WAL, `busy_timeout` y `BEGIN IMMEDIATE` en escrituras | Control negativo: sin IMMEDIATE, `database is locked` |
| D-03 | 2026-09-28 | Alembic: migraciones 0001–0003, una base por proyecto | `tests/test_migraciones.py`; `.exe` migró datos anteriores |
| D-04 | 2026-09-28 | Límite de intentos de PIN con espera exponencial (`429`) | `tests/test_auth.py` |
| D-05 | 2026-09-28 | Seudonimización de resumen, pregunta e historial hacia la IA | `tests/test_asistente.py` |
| D-06 | 2026-09-28 | El Asistente ya no depende del router del Dashboard | Test con Dashboard roto: responde sin cifras |
| D-09 | 2026-09-28 | `MI_PUESTITO_ENTORNO=production` exige secreto ≥ 32 caracteres | `tests/test_auth.py` |
| D-11 | 2026-09-28 | `monto_total` siempre calculado en el servidor; un total del cliente da `422` | `tests/test_ventas.py` |
| — | 2026-10-08 | Modelos de IA por defecto inexistentes en el catálogo de NVIDIA → proveedor genérico y verificación con la llave | ADR-036, `tests/test_asistente.py` |
| — | 2026-10-08 | El hash de la URL no cambiaba de pantalla (Atrás/Adelante) | `frontend/src/stores/navegacion.ts` escucha `hashchange` |
| — | 2026-10-10 | Nemotron devolvía su razonamiento en inglés como respuesta; gpt-oss sumaba mal con prompt corto | Ajustes por familia + descarte de borradores + verificación con el prompt real (ADR-036) |
| — | 2026-10-10 | Una respuesta larga en el historial daba `422` en la pregunta siguiente | El historial se recorta a 1000 caracteres por turno |
| — | 2026-10-10 | "El Sra. Flora" al restituir nombres; el Asistente no veía a todos los deudores | Artículos ajustados en `ia/privacidad.py`; `clientes_que_deben` (top 5, seudonimizado) en el contexto |
| D-13 | 2026-11-01 | En local el secreto de firma se conserva en `sesion.key`: reiniciar el programa no cierra la sesión | `tests/test_auth.py`; navegador: token válido tras reiniciar el servidor |
| D-14 | 2026-11-01 | El vendedor guarda la llave desde el panel del Asistente, cifrada con DPAPI | `tests/test_llave_local.py` con DPAPI real; navegador: NVIDIA rechazó una llave falsa y no se escribió archivo; `.exe`: `puede_guardar_llave` |
| D-16 | 2026-11-01 | Compras completo y offline-first: proveedores, pedidos, checklist, `monto_real`, evento a Inventario | `tests/test_compras.py`; navegador: S/ 320 → S/ 330 con un cambio, flujo sin red entregado en orden |
| D-18 | 2026-11-01 | La PWA avisa de una versión nueva y se aplica cuando el operador decide | Navegador: aviso, "Actualizar ahora" y recarga sin SW en espera |
| D-19 | 2026-11-01 | Botón para reiniciar los datos de práctica; `403` con un negocio real | `tests/test_api.py`; navegador: 4 → 3 órdenes, S/ 485.50, cola local vacía |
| D-20 | 2026-11-01 | `ia/dataset.py` exporta solo lo útil y descarta borradores, respaldos y cifras sin respaldo | `tests/test_asistente.py`; registro de Staging: 0 ejemplos, sin valoraciones |
| — | 2026-11-01 | Escaneo de secretos con gitleaks sobre todo el historial en CI (parte de D-12) | `.github/workflows/ci.yml` |
| — | 2026-11-01 | Respaldo y restauración del archivo de datos (Fase 5) | `tests/test_respaldo.py`; navegador y `.exe`: copia y restauración, lo posterior desaparece y queda copia en `respaldos/` |
| — | 2026-11-01 | Nemotron inventaba montos | Verificador de cifras (ADR-042); `ia.evaluar` 19/19 con Bolt en la última corrida |
| — | 2026-11-01 | Navegación en teléfono y tablet: controles recortados y desbordes | Sin desborde a 375 y 768 px en todas las pantallas; sin `data-ai-id` faltantes ni duplicados |
| D-25 | 2026-11-07 | El mismo RUC registrado sin red en dos tablets queda como alias: nada se rechaza | `tests/test_compras.py`, migración 0005 |
| — | 2026-11-07 | Vitest 4.1.12 y `npm audit fix`: sin vulnerabilidades críticas ni altas en desarrollo (producción: 0); actions en Node 24 | `npm audit`; 63 tests de frontend |
| — | 2026-11-07 | Pantalla de Inventario: alta, conteo, merma, precio y mínimo, historial; offline | `modules/inventario/almacen.test.ts`; navegador: 10 → 8.5 → 8 kg, compra recibida +50 kg, conteo sin red entregado; sin desborde a 375 px |
| — | 2026-11-07 | `ia.evaluar` abortaba en la consola de Windows al imprimir una falla | `sys.stdout.reconfigure` en `main` |
| — | 2026-11-07 | Ventas elige productos del inventario: cantidad en su unidad, monto sugerido y stock descontado | `almacen.test.ts`; navegador: 2.5 kg a S/ 4.00 → S/ 10.00, stock 58 → 55.5 kg y de vuelta a 58 al quitarlo |
| — | 2026-11-08 | El Asistente abre la pantalla que se le pide y señala botones y partes de ella; la conversación queda al lado del formulario (ADR-047) | `tests/test_asistente.py`, `senalar.test.ts`, `navegacion.test.ts`; `ia.evaluar` 23–24/24; navegador a 1280, 887×347, 768 y 375 px: "Quiero registrar una compra" abre Compras, "¿Dónde está el botón…?" marca Nuevo pedido, el buscador conserva lo escrito al preguntar |
| — | 2026-11-08 | "¿Dónde veo a todos los que me deben?" llevaba a la Caja en vez de Fiados | Guía del Asistente; caso nuevo en `ia.evaluar` |
| — | 2026-11-08 | En una pantalla baja la ventana del Asistente escondía su cabecera y la conversación | Columna a todo el alto y caja de escribir en una fila; navegador a 887×347 px |
| — | 2026-11-08 | El Asistente llena órdenes de venta que el operador revisa y guarda; se le puede hablar; los productos que se nombran llevan a su inventario (ADR-049) | `tests/test_asistente.py` (orden llenada, precios del operador, líneas de control), `nombres.test.ts`, `dictado.test.ts`; `ia.evaluar` 28/29; navegador: "2 fideos anita a 4.80" → Orden 4 por S/ 9.60 y stock 30 → 28 |
| — | 2026-11-08 | Prueba del owner: "regístrala por mí" no contaba, "revisa la orden" sin orden, nombre de la clienta perdido, "ACCION: ventas" visible | Regla por raíz del verbo y mensaje anterior; texto corregido sin orden; `PARA:`; red final de líneas de control; navegador: orden "Bertha" con Arroz Costeño 1 kg a S/ 4.20 |
| — | 2026-11-08 | La demo no traía inventario | 7 productos sembrados con movimiento `stock_inicial` |
| D-27 | 2026-11-17 | Una sola fuente de color: `docs/06-diseno/` pasa a `docs/design-system/producto/` y los colores salen solo de `tokens.json` (ADR-050) | `estilos-aislados.test.ts` (tokens que existen); `ds-validar` 0 errores; build con los mismos colores de la PWA |
| D-29 | 2026-11-17 | Decisión del owner: el dictado sigue siendo el del navegador (Google o Microsoft) o el del teléfono; no se instala uno local | ADR-049; aviso de privacidad en un negocio real |
| — | 2026-11-17 | PR #2 fusionado en `main`; etiqueta `v0.1.0` publicada para construir el `.exe` (D-17); `.venv/` en Drive borrada con permiso del owner | `931e977`; flujo `Ejecutable Windows` |
| D-17 | 2026-11-17 | El `.exe` nuevo está publicado: release `v0.1.0` con `MiPuestito.exe` adjunto | Flujo `Ejecutable Windows` en verde; https://github.com/JoseFM2808/Mi-puestito/releases/tag/v0.1.0 |
| D-24 | 2026-11-17 | La caja empieza con efectivo y Yape, suma lo cobrado y resta los gastos; "Ya le pagué" pide el medio y lo descuenta (ADR-051) | `tests/test_caja.py` (13 casos); navegador: abrir con S/ 50 y S/ 20 → S/ 451.50 y S/ 104.00; gasto de S/ 5 → S/ 446.50; el Asistente lo dice |
| D-22 | 2026-11-17 | Costo de la última compra y ganancia por unidad, vencimientos con aviso en Inventario y en la Caja, búsqueda por código de barras | `test_compras.py`, `test_inventario.py`, `almacen.test.ts`; navegador: Leche "Costó S/ 3.60 · ganas S/ 0.60", "Vence el 20 nov.", Caja "2 productos vencen esta semana" |
| D-28 | 2026-11-17 | El Asistente llena pagos de fiado, gastos y mermas en sus pantallas; el operador los guarda | `tests/test_asistente.py`; `ia.evaluar` 32/32; navegador: "la señora Rosa me pagó 10 soles por Yape" → Fiados con S/ 10.00 y Yape marcado; al guardar, Yape de la caja S/ 84 → S/ 94 |
| — | 2026-11-17 | ¿Cómo me va? (Análisis, Fase 7): vendido, proveedores, gastos del puesto y de la casa, libre, día por día y ganancia por producto; el Asistente ya responde por la semana y el mes | `tests/test_analisis.py`, `analisis.test.ts`; `ia.evaluar` 33/33 ("Vendiste S/ 485.50 esta semana"); navegador |
| — | 2026-11-17 | "señora Rosa" viajaba con el nombre real al proveedor y el pago se llenaba a otra clienta | La seudonimización reconoce las formas del tratamiento; test con 5 maneras de escribirlo |
| — | 2026-11-17 | Todo abono entraba a la caja como efectivo | El pago de fiado pregunta efectivo o Yape |
| — | 2026-11-17 | Módulo Gastos (Fase 7): del puesto o de la casa, por medio de pago, offline | `almacen.test.ts`; navegador |
| D-10 | 2026-11-17 | El TestClient usa `httpx2`; el aviso de Starlette ahora es error | Control negativo: sin `httpx2` los tests no arrancan |
| — | 2026-11-17 | Asistente: "Ir a la Caja" se corrige hacia la pantalla del tema y un pedido de hacer algo sin acción abre la suya | `tests/test_asistente.py`; `ia.evaluar` 30/30 |
| D-26 | 2026-11-22 | La conversación con el Asistente se guarda en el dispositivo (sobrevive a recargar y actualizar) y el Asistente recuerda lo que se le pide, con tope de 20 que el modelo consolida; panel «Lo que recuerdo» para olvidar (ADR-052). De paso, un cliente que no está en el resumen tampoco viaja con su nombre | `tests/test_asistente.py` (recuerdos, tope, olvidar, seudonimización), `conversacion.test.ts`, `Recuerdos.test.tsx`; Staging con modelo falso: "Acuérdate que la Sra. Rosa siempre paga por Yape" → el modelo recibe "Cliente 3", el panel muestra "Sra. Rosa…", recargar conserva la conversación, sin desborde a 375 px |
| — | 2026-11-22 | El Asistente llena pedidos a proveedores (`COMPRA`/`PROVEEDOR`): Compras abre «Nuevo pedido» con el proveedor y los productos; los montos que el operador no dijo quedan para él. "Pídele…", "encárgale…" y "haz un pedido" cuentan como pedido de hacer | `tests/test_asistente.py`, `llenado.test.ts`; Staging con modelo falso: "Pídele a Distribuidora Norte 2 sacos de arroz por 180 soles y 1 saco de azúcar" → el modelo ve "Proveedor B", Arroz S/ 180 en el pedido, Azúcar en «Falta cuánto cuesta», guardado con S/ 95 |
| D-07 | 2026-11-22 | El PIN generado en el primer arranque ya no va a la consola: vive en memoria y la pantalla de ingreso lo muestra una vez, solo en la misma computadora, con «Ya lo anoté» (ADR-053) | `tests/test_primer_ingreso.py` (7 casos: no va a consola ni disco, otro equipo recibe `[]`/`403`, cerrar sin anotarlo genera otro); Staging a 375 px: carpeta nueva → PIN de 6 dígitos en pantalla, «Ya lo anoté» lo esconde y ese PIN entra |
| D-30 | 2026-11-22 | Escanear el código de barras con la cámara (`BarcodeDetector`) en el buscador y el alta de Inventario y al vender; en Ventas, el código que escribe un lector elige el producto solo | `EscanearCodigo.test.tsx` (lee y apaga la cámara, cancelar, sin permiso, sin soporte); Staging con cámara y detector simulados a 768 px: alta de «Galletas Soda» con código leído, buscar por cámara, venderla por lector y por cámara; sin desborde a 375 px |
| — | 2026-11-22 | Sugerencia de pedido por stock bajo: «Pedir lo que se acaba» en Inventario y «Se te está acabando» en Nuevo pedido | `llenado.test.ts`; Staging a 768 px: Leche Gloria (5 de 6) y Papa amarilla (3 de 5) llegan a «Falta cuánto cuesta»; en un pedido nuevo, tocar Leche Gloria la pone en el formulario; sin desborde a 375 px |
| — | 2026-11-22 | Análisis: kardex mensual del inventario y ganancia por categoría de producto (migración 0009, ADR-054) | `tests/test_analisis.py` (kardex que cruza la medianoche de Lima, registro aparte de los conteos, mes futuro `422`, categoría normalizada y borrable), `kardex.test.ts`; Staging: la migración 0009 se aplicó sobre la base existente, Arroz Costeño → «Abarrotes», kardex de 8 productos, mes pasado sin movimientos; sin desborde a 375 px |
| — | 2026-11-22 | El Asistente lee lo que el operador tiene en pantalla (`data-ai-id`, sin valores) y puede señalar el campo exacto (ADR-055) | `tests/test_asistente.py` (señala lo visible, no lo inventado, nunca viaja el valor, id raro `422`, llega al prompt), `leerPantalla.test.ts`; Staging a 1280 px con orden abierta y Asistente en ventana: "¿Dónde pongo cuánto le cobro?" marcó `ventas-orden-<uuid>.monto` |
| — | 2026-11-22 | Ventas a 1280 px con el menú y el Asistente en ventana cortaba «Cobrar en efectivo» (la orden seguía en dos columnas porque la media query miraba la ventana, no el espacio) | `container-type` en la pantalla de Ventas y `@container (max-width: 760px)`; navegador: Ventas, Compras, Inventario, Análisis, Asistente, Caja, Fiados y Gastos sin desborde ni botones recortados a 375, 768, 1280 y 1600 px |
| — | 2026-11-22 | Los README de los módulos como contexto del Asistente en runtime: si pide ayuda, recibe la tabla "Qué acciones permite" de la pantalla (ADR-056) | `tests/test_asistente.py` (llegan los botones, una pregunta de cifras no carga el manual, cada pantalla tiene su tabla, limpieza de marcas); build de PyInstaller en Linux: `/api/salud` sin módulos degradados, el modelo recibió el manual de Fiados desde `guias/` y `/api/auth/primer-ingreso` dio el PIN sin imprimirlo |
| — | 2026-11-22 | El flujo del Asistente corre en un grafo de LangGraph (preparar → generar → verificar → sin_respuesta) con recorrido simple si falta la librería (ADR-057) | 157 tests del Asistente sin cambios de comportamiento; `test_el_grafo_prueba_modelos…` con y sin LangGraph; build de PyInstaller en Linux (~90 MB): sin módulos degradados y "Acuérdate que…" respondido por el grafo |
| — | 2026-11-22 | El Asistente no conocía las funciones nuevas ni sabía qué se acaba; una cifra visible en la pantalla del operador se descartaba como inventada | Guía de la app al día, `productos_por_acabarse` (solo nombres) en el contexto, apartados `inventario.pedir-lo-que-se-acaba`, `analisis.kardex` y `analisis.por-dia`; lo visible cuenta para el verificador. `tests/test_asistente.py` (3 casos nuevos) |
| — | 2026-11-22 | El kardex se ve sin conexión: el último de cada mes queda en el dispositivo (IndexedDB v7) y se recalcula al terminar de enviar lo pendiente | `Kardex.test.tsx` (guarda con red y muestra lo guardado sin red, diciendo de cuándo; sin nada guardado lo dice) |
| — | 2026-11-22 | A 1024 px con el Asistente en ventana, el menú fijo (288 px) y la ventana (430 px) dejaban ~230 px a la pantalla y la ventana tapaba parte de ella («Nuevo pedi…», la barra) | Entre 1000 y 1399 px con la ventana abierta, el menú pasa a panel con «Menú» (`data-asistente="ventana"`). Navegador: la pantalla pasa de 234 a 594 px a 1024 y de 400 a 760 a 1280; el menú se abre, navega y se cierra; sin la ventana vuelve a quedar fijo |
| — | 2026-11-22 | Con letra «Muy grande» a 375 px se salían de la pantalla la Caja (439 px), Compras/Nuevo pedido (412) y Gastos/Anotar (399): las pantallas (`margin: auto`) tomaban el ancho de su contenido y un campo de texto con letra grande lo ensanchaba; en la Caja, los accesos en `1fr 1fr` no se angostaban | `main` a `width: 100%` en el marco (`App.module.css`); accesos de la Caja en `minmax(0, 1fr)` y uno por fila con letra muy grande. Navegador: las 8 pantallas, con sus formularios abiertos, sin desborde a 375, 768 y 1280 px con letra «Grande» y «Muy grande» |
| — | 2026-11-22 | Memoria: una línea `RECORDAR:` pegada al final de una frase llegaba al operador sin guardarse, y una consolidación numerada («1. …») dejaba el número en el recuerdo | `ia/memoria.py` acepta `RECORDAR:` en mayúsculas tras un punto y limpia viñetas y números; `tests/test_asistente.py` (4 casos) |
| — | 2026-11-22 | `COMPRA`, `PROVEEDOR`, `ABONO`, `GASTO` y `MERMA` pegados al final de una frase no llenaban el formulario y llegaban al operador | `formularios.linea_de_control()` (en su línea, o en mayúsculas tras un punto), usado también por `ia/pedido.py`; `tests/test_asistente.py` |
| — | 2026-11-22 | `npm audit fix`: dependencias de desarrollo al día (typescript-eslint y otras); producción sigue en 0 vulnerabilidades | Quedan 3 moderadas de desarrollo (glob, minimatch vía `workbox-build`) sin arreglo compatible; `pip-audit` del backend con LangGraph: ninguna conocida |
| — | 2026-11-22 | Tras 5 PIN errados el servidor pide esperar (`429`, D-04), pero la pantalla decía «Usuario o PIN incorrecto»: la persona seguía probando sin saber que debía esperar. Un error del programa también se veía como PIN errado | `sesion.ts` muestra el motivo del servidor; `sesion.test.ts`; navegador a 375 px: el 6.º intento dice «Espera 30 segundos». Además: axe-core sin problemas de accesibilidad en las 9 pantallas |
| — | 2026-11-22 | La cola offline tenía una sola vuelta de envío para todos los negocios: al cambiar de negocio a mitad de un envío, el nuevo esperaba hasta 20 s y podía mostrar los pendientes del anterior | Una vuelta por negocio y conteos solo del negocio abierto (`cola.ts`); `cola.test.ts` con control negativo (con el código anterior la prueba falla) |

## 3. Resueltos en la auditoría inicial (2026-09-27, verificados en Staging)

| Hallazgo | Evidencia | Arreglo |
|---|---|---|
| `.exe` moría al arrancar: `ruta_base_datos()` sin proyecto | Test nuevo falló con `TypeError` antes del arreglo | `escritorio.py` informa `directorio_datos()` |
| `.exe` con **todos** los módulos degradados (`/api/salud` → `ok`) | Build local: `modulos_degradados: [asistente, auth, compras, dashboard, ventas]` | `collect_submodules` + `sys.path` en el spec → `[]` |
| Dashboard/Asistente degradados en Windows (falta `tzdata`) | `ZoneInfoNotFoundError: America/Lima` al correr pytest en Windows | `tzdata` en runtime + CI backend en Windows |
| Humo de CI nunca podía ver el puerto (proceso hijo) ni detectar degradación | Mismo fallo reproducido al probar localmente | Lee `puerto.txt` y exige `modulos_degradados == []` |
| `MI_PUESTITO_SECRETO=` vacío firmaba tokens con llave HMAC vacía (falsificables) | `os.environ.get(k, default)` devuelve `""` si k existe vacía; token forjado con `hmac.new(b'')` → `401` en Staging tras el arreglo | `_secreto_de_firma()` usa `or`; test de regresión |
| `.obsidian/workspace.json` versionado | `test_higiene_repo.py` lo detectó | `git rm --cached` + ignorado |

Resultado Staging: `pytest` 42/42 · `vitest` 14/14 · `npm run build` ok · `.exe` construido y probado (login demo/anita, 401 sin token, SPA en `/ventas`).

## 4. Estado de `.gitignore`

| Categoría | Patrones | Control automático |
|---|---|---|
| Secretos / entorno | `.env`, `.env.*`, `*.env`, `config/*`, `secrets/` (excepto `*.env.example`) | ✅ test |
| Llaves y certificados | `*.pem`, `*.key`, `*.dpapi`, `*.p12`, `*.pfx`, `*.crt`, `id_rsa*`, `id_ed25519*` | ✅ test + regex de contenido |
| Credenciales de la app | `usuarios.json` | ✅ test |
| Base de datos del vendedor | `*.db`, `*.db-wal`, `*.db-shm`, `*.db-journal`, `*.sqlite*`, `*.dump`, `backups/`, `respaldos/` | ✅ test |
| Datos de negocio | `data/raw/`, `data/processed/`, `data/vector_store/`, `*.csv`, `*.xlsx` | ✅ test (carpetas) |
| Actas y acuerdos internos | `docs/meetings/`, `docs/privado/`, `docs/acuerdos/`, `.ai-context/privado/`, `*.private.md`, `*-privado.md` | ✅ test |
| Logs | `*.log`, `logs/` | ✅ test |
| Registro de la IA (ADR-038) | `*.jsonl` | ✅ test |
| Herramientas locales | `.claude/settings.local.json`, `.obsidian/workspace*.json`, `.vscode/`, `.idea/` | ✅ test (las 2 primeras) |
| Build / dependencias | `node_modules/`, `frontend/dist/`, `backend/build/`, `backend/dist/`, cachés Python | — |
| SO / Google Drive | `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.gdoc`, `*.gsheet` | — |

Escaneo del historial completo (`git log --all -p`) el 2026-09-27: **sin** archivos sensibles ni patrones de llaves.

## 5. Reglas para `.ai-context/`

- ✅ Arquitectura, flujos, esquema, ADRs, deuda técnica.
- ❌ Actas de reunión, acuerdos comerciales, precios pactados con clientes, datos reales de ventas o clientes, PINs, llaves, URLs con credenciales.
- Lo privado del equipo va en `.ai-context/privado/` (ignorado por git).