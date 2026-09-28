# 05 · Deuda técnica e higiene del repositorio

> Última auditoría: 2026-09-27 · rama `chore/auditoria-arquitectura-higiene`.
> Prioridad: **P1** antes de guardar datos reales en `anita` · **P2** antes de la nube · **P3** mejora continua.

## 1. Deuda técnica

| ID | P | Hallazgo | Riesgo | Propuesta | Relación |
|---|---|---|---|---|---|
| D-01 | P1 | El Dashboard del frontend muestra `datos-ficticios.ts` para **todos** los proyectos | Anita ve cifras de demo, y el Asistente (que lee el backend) le responde "0": dos verdades distintas | Consumir `GET /api/dashboard/resumen` vía adaptador | ADR-033 |
| D-02 | P1 | SQLite sin `journal_mode=WAL` ni `busy_timeout`; transacciones diferidas | `database is locked` y actualizaciones perdidas cuando lleguen las escrituras de Ventas | `PRAGMA journal_mode=WAL; busy_timeout=5000` en el listener `connect`; `BEGIN IMMEDIATE` en escrituras | ADR-031 |
| D-03 | P1 | Esquema con `create_all`, sin migraciones | Cambiar una tabla con ventas reales exige migración manual | Alembic antes de la primera escritura real en `anita` | Plan Fase 2 |
| D-04 | P2 | `/api/auth/ingresar` sin límite de intentos (PIN de 6 dígitos) | Fuerza bruta si algún día escucha fuera de `127.0.0.1` | Bloqueo progresivo por usuario (5 intentos → espera) | — |
| D-05 | P1 | Nombres de clientes y deudas viajan a NVIDIA NIM en el contexto | Transferencia de datos personales a un tercero (Ley 29733) | Seudonimizar en `ia/`; consentimiento; modelo local | ADR-034 |
| D-06 | P3 | `asistente` importa `modules.dashboard.router` (dependencia cruzada) | Si cae Dashboard, cae Asistente | Extraer `obtener_resumen` a un servicio compartido | AGENTS.md |
| D-07 | P3 | El PIN generado se imprime una vez en consola | Si stdout se redirige a un log, el PIN queda en disco | Mostrarlo en la UI de primer arranque; `*.log` ya ignorado | ADR-030 |
| D-08 | P2 | El registro de proyectos (`proyectos.py`) tiene el nombre de un negocio real en código público | Exposición de identidad del cliente; alta de negocios exige release | Mover el registro a la carpeta de datos (`proyectos.json`, ignorado) | ADR-030 |
| D-09 | P2 | `MI_PUESTITO_SECRETO` aleatorio por arranque | En nube, cada reinicio cierra todas las sesiones | Obligatorio en `production`; fallar al arrancar si falta | `config/.env.example` |
| D-10 | P3 | `starlette.testclient` avisa deprecación de `httpx` | Tests rotos en una versión futura de Starlette | Fijar versiones o migrar cuando se estabilice | — |
| D-11 | P2 | `monto_total` de venta es un dato derivado guardado | Divergencia con Σ items si alguien escribe fuera del servicio | Calcular siempre en servidor; test de conciliación | 01-logica §1 |
| D-12 | P2 | Sin escaneo de secretos en el remoto | Un `git add -f` se detecta en CI, pero ya estaría publicado | Activar *Secret scanning + Push protection* en GitHub (Settings → Code security) y hook `pre-commit` con gitleaks | ADR-030 |

## 2. Resueltos en esta auditoría (verificados en Staging)

| Hallazgo | Evidencia | Arreglo |
|---|---|---|
| `.exe` moría al arrancar: `ruta_base_datos()` sin proyecto | Test nuevo falló con `TypeError` antes del arreglo | `escritorio.py` informa `directorio_datos()` |
| `.exe` con **todos** los módulos degradados (`/api/salud` → `ok`) | Build local: `modulos_degradados: [asistente, auth, compras, dashboard, ventas]` | `collect_submodules` + `sys.path` en el spec → `[]` |
| Dashboard/Asistente degradados en Windows (falta `tzdata`) | `ZoneInfoNotFoundError: America/Lima` al correr pytest en Windows | `tzdata` en runtime + CI backend en Windows |
| Humo de CI nunca podía ver el puerto (proceso hijo) ni detectar degradación | Mismo fallo reproducido al probar localmente | Lee `puerto.txt` y exige `modulos_degradados == []` |
| `MI_PUESTITO_SECRETO=` vacío firmaba tokens con llave HMAC vacía (falsificables) | `os.environ.get(k, default)` devuelve `""` si k existe vacía; token forjado con `hmac.new(b'')` → `401` en Staging tras el arreglo | `_secreto_de_firma()` usa `or`; test de regresión |
| `.obsidian/workspace.json` versionado | `test_higiene_repo.py` lo detectó | `git rm --cached` + ignorado |

Resultado Staging: `pytest` 42/42 · `vitest` 14/14 · `npm run build` ok · `.exe` construido y probado (login demo/anita, 401 sin token, SPA en `/ventas`).

## 3. Estado de `.gitignore`

| Categoría | Patrones | Control automático |
|---|---|---|
| Secretos / entorno | `.env`, `.env.*`, `*.env`, `config/*`, `secrets/` (excepto `*.env.example`) | ✅ test |
| Llaves y certificados | `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `id_rsa*`, `id_ed25519*` | ✅ test + regex de contenido |
| Credenciales de la app | `usuarios.json` | ✅ test |
| Base de datos del vendedor | `*.db`, `*.db-wal`, `*.db-shm`, `*.db-journal`, `*.sqlite*`, `*.dump`, `backups/` | ✅ test |
| Datos de negocio | `data/raw/`, `data/processed/`, `data/vector_store/`, `*.csv`, `*.xlsx` | ✅ test (carpetas) |
| Actas y acuerdos internos | `docs/meetings/`, `docs/privado/`, `docs/acuerdos/`, `.ai-context/privado/`, `*.private.md`, `*-privado.md` | ✅ test |
| Logs | `*.log`, `logs/` | ✅ test |
| Herramientas locales | `.claude/settings.local.json`, `.obsidian/workspace*.json`, `.vscode/`, `.idea/` | ✅ test (las 2 primeras) |
| Build / dependencias | `node_modules/`, `frontend/dist/`, `backend/build/`, `backend/dist/`, cachés Python | — |
| SO / Google Drive | `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*.gdoc`, `*.gsheet` | — |

Escaneo del historial completo (`git log --all -p`) el 2026-09-27: **sin** archivos sensibles ni patrones de llaves.

## 4. Reglas para `.ai-context/`

- ✅ Arquitectura, flujos, esquema, ADRs, deuda técnica.
- ❌ Actas de reunión, acuerdos comerciales, precios pactados con clientes, datos reales de ventas o clientes, PINs, llaves, URLs con credenciales.
- Lo privado del equipo va en `.ai-context/privado/` (ignorado por git).
