# 05 · Deuda técnica e higiene del repositorio

> Última revisión: 2026-11-01 · rama `chore/auditoria-arquitectura-higiene`.
> Prioridad: **P1** antes de usar el negocio real · **P2** antes de la nube · **P3** mejora continua.

## 1. Pendientes

| ID | P | Hallazgo | Riesgo | Propuesta | Relación |
|---|---|---|---|---|---|
| D-07 | P3 | El PIN generado se imprime una vez en consola | Si stdout se redirige a un log, el PIN queda en disco | Mostrarlo en la UI de primer arranque; `*.log` ya ignorado | ADR-030 |
| D-08 | P2 | El registro de proyectos (`backend/proyectos.py`) tiene el nombre de un negocio real en código público | Exposición de identidad del cliente; dar de alta un negocio exige una versión nueva | Pantalla de alta de negocio + `proyectos.json` en la carpeta de datos (ignorado) | ADR-030 |
| D-10 | P3 | `starlette.testclient` depreca su uso con `httpx` (aviso filtrado en `backend/pytest.ini`) | Tests rotos en una versión futura de Starlette | Migrar de cliente de pruebas cuando se estabilice | — |
| D-12 | P2 | Falta activar en GitHub *Secret scanning + Push protection* | gitleaks en CI lo detecta, pero después de publicado; push protection lo impide antes | Lo activa el owner en Settings → Code security | ADR-030 |
| D-15 | P2 | El Asistente necesita internet | Sin red no hay ayuda | Modelo local (Ollama/llama.cpp) con Gemma pequeño; luego fine-tuning | ADR-039 |
| D-17 | P2 | El `.exe` publicado aún tiene el frontend anterior | El vendedor no ve Ventas, Fiados ni Compras hasta publicar uno nuevo | Construido y probado localmente el 2026-11-01. Falta que el owner publique una etiqueta `v*` → flujo `Ejecutable Windows` | ADR-029 |
| D-21 | P3 | El RUC se escribe a mano | Un RUC válido en forma pero inexistente pasa | Búsqueda en SUNAT: requiere elegir un servicio externo | `Modulo-Compras.md` |
| D-22 | P3 | Inventario sin costo, vencimientos ni código de barras; Ventas aún no elige productos del inventario | Las ventas no descuentan stock desde la pantalla; las compras no alimentan el costo | Elegir producto al vender; costo desde la última compra; alertas de vencimiento | ADR-045 |
| D-23 | P2 | La copia de respaldo va sin cifrar | Quien tenga el archivo ve clientes, fiados y ventas | Cifrar con una contraseña que elija el vendedor; decidir qué pasa si la olvida | ADR-044 |
| D-24 | P3 | "Ya le pagué" cierra el pedido pero no descuenta de la caja | La caja no refleja lo pagado a proveedores | Definir el flujo de caja (efectivo inicial, egresos) | `Modulo-Dashboard.md` |

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
