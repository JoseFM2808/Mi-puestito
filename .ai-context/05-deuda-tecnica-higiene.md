# 05 · Deuda técnica e higiene del repositorio

> Última revisión: 2026-10-08 · rama `chore/auditoria-arquitectura-higiene`.
> Prioridad: **P1** antes de usar el negocio real · **P2** antes de la nube · **P3** mejora continua.

## 1. Pendientes

| ID | P | Hallazgo | Riesgo | Propuesta | Relación |
|---|---|---|---|---|---|
| D-07 | P3 | El PIN generado se imprime una vez en consola | Si stdout se redirige a un log, el PIN queda en disco | Mostrarlo en la UI de primer arranque; `*.log` ya ignorado | ADR-030 |
| D-08 | P2 | El registro de proyectos (`backend/proyectos.py`) tiene el nombre de un negocio real en código público | Exposición de identidad del cliente; dar de alta un negocio exige una versión nueva | Pantalla de alta de negocio + `proyectos.json` en la carpeta de datos (ignorado) | ADR-030 |
| D-10 | P3 | `starlette.testclient` depreca su uso con `httpx` (aviso filtrado en `backend/pytest.ini`) | Tests rotos en una versión futura de Starlette | Migrar de cliente de pruebas cuando se estabilice | — |
| D-12 | P2 | Sin escaneo de secretos en el remoto | Un `git add -f` se detecta en CI, pero ya estaría publicado | Activar *Secret scanning + Push protection* en GitHub (lo hace el owner) y hook `pre-commit` con gitleaks | ADR-030 |
| D-13 | P2 | En modo local el secreto de firma es aleatorio por arranque | Al reiniciar el programa se cierran las sesiones (la cola offline espera, no pierde nada) | Guardar un secreto generado una vez en la carpeta de datos | ADR-032 |
| D-14 | P1 | La llave de IA del vendedor en el `.exe` solo se puede dar por variable de entorno | Un vendedor no sabe configurar variables; sin llave no hay Asistente | Pantalla "Configurar Asistente" que guarde la llave con DPAPI de Windows (nunca en texto plano) | ADR-036 |
| D-15 | P2 | El Asistente necesita internet | Sin red no hay ayuda | Modelo local (Ollama/llama.cpp) con Gemma pequeño; luego fine-tuning | ADR-039 |
| D-16 | P2 | Compras solo tiene lectura | Recepción de pedidos no mueve stock ni actualiza la proyección | Fase 4: escrituras idempotentes + evento `compra.item_recibido` hacia Inventario | 01-logica §4 |
| D-17 | P2 | El `.exe` publicado aún tiene el frontend anterior | El vendedor no ve Ventas/Fiados hasta reconstruirlo | Etiqueta `v*` → flujo `Ejecutable Windows` (humo ya exige módulos sanos) | ADR-029 |
| D-18 | P3 | Una versión nueva de la PWA se aplica recién en la segunda recarga | El operador puede ver la versión anterior un rato | Aviso "Hay una versión nueva — Actualizar" con `registerType: 'prompt'` | — |
| D-19 | P3 | Los datos de demo se siembran una vez, relativos a ese día | Días después "Vendiste hoy" sale en cero y los pedidos aparecen atrasados (el Asistente lo dice bien, pero la demo pierde gracia) | Botón "Reiniciar datos de práctica" solo en demo | `backend/datos_demo.py` |
| D-20 | P2 | El registro de Staging tiene 1 intercambio del 2026-10-11 02:12 UTC con un borrador de razonamiento (antes del arreglo) | Ensuciaría el fine-tuning | Al armar el dataset, usar solo intercambios con valoración positiva y descartar los que empiecen como borrador | ADR-038/039 |

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
| Llaves y certificados | `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `id_rsa*`, `id_ed25519*` | ✅ test + regex de contenido |
| Credenciales de la app | `usuarios.json` | ✅ test |
| Base de datos del vendedor | `*.db`, `*.db-wal`, `*.db-shm`, `*.db-journal`, `*.sqlite*`, `*.dump`, `backups/` | ✅ test |
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
