# ADR-001 — Consolidación estructural (Etapa 4)

**Estado:** Propuesta (requiere aprobación antes de ejecutar)
**Fecha:** 2026-06-12
**ADRs relacionadas:** [ADR-002 — scheduler vs matches](./ADR-002-scheduler-vs-matches.md) (refina la decisión 4)

**Contexto:** ArenaSync mantiene dos stacks que comparten BD: `models/` (inglés, SQLAlchemy 2.0, tablas `tournaments/matches/registrations/audit_logs`) y `domain/models/` (español, estilo clásico, tablas `torneo/enfrentamiento/inscripcion/logauditoria/jugador/administrador/alerta/ronda/historialelo`). Hay doble fuente de verdad, auditoría en dos tablas activas, y entidades legado vivas solo por tests. Las Fases 1–5 lo documentaron; Etapas 1–3 saldaron lo no disruptivo. Etapa 4 es la consolidación con breaking changes.

---

## Decisiones

### 1. Stack canónico → `models/` (inglés)
El stack de torneos (`models/`, SQLAlchemy 2.0) es el activo y cumple `ENGLISH_STANDARD`. **Las entidades vivas de `domain/models/` (`Jugador`, `Administrador`, `Alerta`, `LogAuditoria`, `Enfrentamiento`) se migran a `models/` en inglés**; `domain/models/` se elimina. `domain/schemas/` se consolida en `schemas/`.
*Nota:* `Jugador` es la tabla de usuarios compartida (destino de FKs); su migración es la de mayor impacto.

### 2. Tabla canónica de auditoría → `audit_logs` (única, superset)
Se unifica en **`audit_logs`** (inglés, stack nuevo) con columnas superset: `id, actor_id, action, occurred_at, change_description (nullable)`. `logauditoria` se elimina; `AuditRepository` (admin/alerta/scheduler) se reapunta a `audit_logs`/`AuditLogRepository`. Resuelve **F-1** y deja un único dueño de escritura (ya logrado parcialmente en Etapa 1).

### 3. `HistorialElo` → **Eliminar** (código muerto)
Sin consumidores ni escritura; PROJECT_CONTEXT menciona "historiales" pero no hay implementación. Se **elimina la entidad y su tabla**. Si "historial de ELO" se confirma como requisito, se implementa de cero como feature nueva con modelo inglés y escritura en `registrar_resultado` — fuera del alcance de la consolidación.

### 4. Partidas → separar competencia de agenda (refinada por ADR-002)
`enfrentamiento` **no** es un duplicado funcional de `matches`: `matches` es el slot abstracto del bracket y `enfrentamiento` porta datos de agenda (`fecha_hora_programada`, deadline) que `matches` no tiene. Por tanto:

- **Tabla canónica de bracket y competencia → `matches`.**
- **Modelo canónico de agenda/programación → `scheduled_matches`** (renombrado de `enfrentamiento` a inglés; ver ADR-002).
- **`matches` y `scheduled_matches` representan conceptos distintos y NO deben consolidarse en una sola entidad.**
- **`scheduled_matches` podrá referenciar opcionalmente `matches.id` mediante FK.**

No se introduce un campo `scheduled_at` ni semántica temporal dentro de `matches`. `ronda` (huérfana) se elimina; `torneo`/`inscripcion` legados se eliminan tras desacoplar `tests/helpers.py`.

### 5. Estrategia de migración al inglés → incremental, identificadores antes que rutas
1. Identificadores técnicos primero (clases, métodos, variables, columnas nuevas) en lotes pequeños con `pytest` entre cada uno.
2. Tablas: migraciones **Alembic** explícitas (no confiar en `create_all`; hoy hay drift entre `create_all` y `alembic/versions`).
3. Campos de payload (`torneo_id→tournament_id`, etc.) y **rutas** al final, con **capa de compatibilidad temporal** (rutas/alias duales documentados) y período de deprecación, según exige `REST_API.md`.
4. Textos de cara al usuario permanecen en español (política de idioma).

### 6. Impacto REST (breaking, con compatibilidad)
Renombres: `/usuarios/registrar→/users`, `/usuarios/login→/sessions`, `/jugadores/{id}→/users/{id}`, `…/iniciar`→transición de estado, `…/cancelar`→`DELETE`, `/tournaments/register→/tournaments/{id}/registrations`, `…/resultado→…/result`, `…/jugadores/.../historial→…/players/.../history`, `POST /admins/password→PUT`. Campos de request/response a inglés. **REST-11** (contrato de error único) entra aquí. Todo detrás de capa de compatibilidad para no romper clientes de golpe.

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Migración de datos de dos tablas de auditoría con esquemas distintos | Alta | Migración Alembic con backfill de `change_description`/`actor_id`; validar conteos. |
| Renombrar rutas/campos rompe el frontend | Alta | Capa de compatibilidad dual + deprecación documentada. |
| FK sobre `jugador.id` (tabla compartida) al renombrar | Alta | Migrar `jugador→players` con renombrado de FKs en una sola migración atómica. |
| Renombrar `enfrentamiento→scheduled_matches` (ADR-002) | Baja | Tabla vacía en prod; solo rename de tabla/columnas + import del scheduler y helper de test. |
| Drift `create_all` vs Alembic | Media | Congelar `create_all`, mover todo a migraciones versionadas. |
| Churn masivo de tests (fakes, patches, asserts de payload) | Media | Lotes pequeños, `pytest` por lote, adaptar tests solo a estructura interna. |
| `SYSTEM_ADMIN_ID=1` usado en `jugador` y `administrador` | Media | Definir actor canónico único al unificar auditoría. |

*Eliminado del registro de riesgos:* la incorporación de `scheduled_at` dentro de `matches` y la lógica de poblado asociada — ADR-002 descarta esa vía (la agenda vive en `scheduled_matches`, no en `matches`).

## Consecuencias
- **Positivas:**
  - Una sola fuente de verdad por concepto y auditoría única.
  - **Se elimina el legado de idioma** (identificadores y tablas en inglés).
  - **Se preserva la funcionalidad de alertas** (vía `scheduled_matches`, sin pérdida de capacidad).
  - **No se introduce lógica temporal artificial dentro de `matches`** (competencia y agenda quedan como conceptos separados).
  - Eliminación de legado/código muerto (`HistorialElo`, `torneo`, `inscripcion`, `ronda`).
- **Negativas:** breaking changes de API, ventana de migración con compatibilidad, migraciones de datos irreversibles si no se versionan bien.

## Orden de ejecución (Etapa 4)
1. Congelar `create_all` y definir **Alembic como fuente única de esquema**.
2. Aplicar **ADR-002** (`ScheduledMatch`: renombrar `enfrentamiento → scheduled_matches`).
3. Unificar auditoría en **`audit_logs`**.
4. Consolidar entidades vivas de `domain/models` hacia `models` (inglés).
5. Resolver **`HistorialElo`** según decisión de producto (eliminar, salvo que se confirme como feature).
6. Migrar identificadores técnicos al inglés.
7. Migrar rutas y contratos REST mediante **compatibilidad temporal** (incluye REST-11).
8. Retirar la capa de compatibilidad cuando corresponda (tras deprecación).
