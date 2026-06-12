# ADR-005 — Identidad única de usuario (`Jugador` / `Administrador`)

**Estado:** Propuesta (recomendación; resuelve el riesgo crítico de la Etapa 4)
**Fecha:** 2026-06-12
**ADRs relacionadas:** [ADR-001](./ADR-001-consolidacion-etapa-4.md), [ADR-004](./ADR-004-alembic-adoption-strategy.md)

---

## Contexto

Tras la Etapa 4, el esquema canónico tiene `audit_logs.usuario_id → jugador.id` (FK **enforzada en PostgreSQL**), pero conviven **dos tablas de usuario**: `jugador` y `administrador`. Las auditorías de admin/alertas/scheduler escriben `usuario_id = administrador_id`; como `administrador` y `jugador` son tablas/secuencias **independientes**, el `INSERT` en `audit_logs` **falla en Postgres** si ese id no existe en `jugador`. Los tests (SQLite, FK off) no lo detectan.

### Regla de dominio confirmada
- Existe **un único tipo real de usuario: `Jugador`**.
- `Administrador` **no** es una identidad distinta: es un `Jugador` actuando como **organizador** de un torneo.
- El rol administrador es **contextual y relativo al torneo** (su creador), **no** una jerarquía permanente.
- El creador no puede participar en el torneo que organiza.

---

## 1. Responsabilidades actuales de `Administrador`
1. **UC-01 — cambio de contraseña admin** (`POST /admins/password` → `admin_service.update_password` → `administrador.contrasena_hash`).
2. **Actor de auditoría del sistema** (scheduler/admin/alertas escriben `administrador_id` en `audit_logs`).
3. **Seed de sistema** (`ensure_system_admin(1)` al arranque, para tener un actor de auditoría).
4. **Columna `alerta.administrador_id`** (nullable, sin uso funcional real).

## 2. Inventario de dependencias

| Componente | Dependencia de `Administrador` |
|---|---|
| **Modelo** | `domain/models/admin.py` (tabla `administrador`); `alerta.administrador_id` |
| **Repositorio** | `admin_repository` (`get_by_id`, `update_password`, `ensure_system_admin`) |
| **Servicio** | `admin_service.update_password` (hashing **bcrypt**) |
| **Controller** | `admin_controller` (`POST /admins/password`) vía `get_current_admin_id` |
| **Auth** | `core/dependencies.get_current_admin_id()` → **`return 1` (stub, sin auth real)** |
| **Arranque** | `main.py` → `ensure_system_admin(SYSTEM_ADMIN_ID)` |
| **Auditoría** | `audit_log_repository.log_action(administrador_id=…)` → `usuario_id` (FK→`jugador.id`) |
| **Constante** | `SYSTEM_ADMIN_ID = 1` (usado en `main`, `scheduler`) |
| **Tests** | `conftest` (override `get_current_admin_id→1`, `seed_admin` crea `Administrador`), `test_uc01` |

**Contraste clave:** el **stack de torneos ya cumple la regla de dominio** — creador/administrador es un `Jugador` (`tournaments.creador_id → jugador.id`, auth real `get_current_user`/Bearer). La dualidad solo persiste en el **stack admin** (UC-01 password + alertas + seed), que usa `Administrador` y un auth **stub**.

## 3. Conflictos de mantener dos tablas de usuario
- **FK rota en Postgres** (`audit_logs.usuario_id → jugador.id` con actor `administrador_id`).
- **Doble fuente de verdad de identidad** → contradice ADR-001 y la regla de dominio.
- **Dos esquemas de hashing** de contraseña: `administrador` usa **bcrypt**; `jugador` usa **pbkdf2_hmac** → la "misma persona" tendría credenciales en dos lugares y formatos.
- **Auth incoherente:** torneos usan token real (`get_current_user`); admin usa stub (`return 1`).
- **`SYSTEM_ADMIN_ID=1` ambiguo:** se usa como `administrador.id` y como `audit_logs.usuario_id` (que apunta a `jugador.id`).

## 4. Ventajas y riesgos de unificar en `Jugador`

**Ventajas:**
- Resuelve la FK de auditoría de raíz (actor = `jugador.id` siempre).
- Una sola identidad → cumple ADR-001 y la regla de dominio.
- Elimina la dualidad de hashing/auth a futuro.
- Simplifica seeds y el actor de sistema.

**Riesgos / fricciones (no bloqueantes, pero reales):**
- **Reconciliación de hashing** (bcrypt ↔ pbkdf2): hay que elegir un esquema único y manejar verificación.
- **Auth admin real:** `get_current_admin_id` (stub) debe sustituirse por auth de `Jugador` (Bearer); cambia el contrato de los endpoints admin.
- **Rol contextual:** NO debe introducirse un `rol="administrador"` permanente en `jugador` (violaría la regla). La condición de admin se deriva de **`tournaments.creador_id == jugador.id`**.
- **Autorización de alertas:** sin admin global, falta definir quién lista/reconoce alertas (¿cualquier usuario autenticado? ¿ámbito por torneo?).

## 5. Cómo quedaría `audit_logs`
- `usuario_id → jugador.id` se mantiene y **queda consistente**: todo actor (incl. acciones admin/scheduler) es un `jugador.id` real.
- *(Opcional, fuera de este ADR):* renombrar a `actor_id` en la migración al inglés.

## 6. Cómo quedaría `SYSTEM_ADMIN_ID`
- Pasa a ser el **id de un `Jugador` de sistema** (actor de eventos automáticos del scheduler), garantizando que la FK de auditoría siempre se cumpla.
- Alternativa: permitir actor **nulo** para eventos de sistema (requeriría `audit_logs.usuario_id` nullable) — menos recomendable (pierde trazabilidad del actor).

## 7. Cómo quedaría `ensure_system_admin`
- Se transforma en **`ensure_system_user`**: asegura un `Jugador` de sistema con `id = SYSTEM_ADMIN_ID`. Desaparece `administrador` como destino.

## 8. Cómo quedarían los casos de uso administrativos
- **UC-01 (password):** opera sobre `jugador.contrasena_hash`; el endpoint autentica al `Jugador` real (no stub). Conceptualmente "el usuario cambia su propia contraseña".
- **Crear/iniciar/cancelar torneo, registrar resultado:** **ya** funcionan sobre `Jugador` (creador) — sin cambios de identidad.
- **Alertas (`GET /alerts`, ack):** se redefine su autorización sin admin global (decisión de diseño pendiente).
- **Restricción "creador no participa":** ya implementada en `registration_service` — se conserva.

## 9. Compatibilidad con ADRs
| ADR | Compatibilidad |
|---|---|
| **ADR-001** | ✅ Refuerza la fuente única (una sola identidad de usuario). |
| **ADR-002** | ✅ Ortogonal (agenda vs bracket no se afecta). |
| **ADR-003** | ✅ Ortogonal (`scheduled_matches`/`match_id` no se afecta). |
| **ADR-004** | ✅ La unificación es una **nueva revisión Alembic** sobre el baseline (no un re-squash). |

## 10. Estrategia de migración recomendada
Como la BD es desechable (ADR-004) y no hay datos productivos, una **nueva revisión Alembic** sobre el baseline:
1. (Si hubiera datos) migrar `administrador` → `jugador`; en dev: ninguno.
2. `DROP TABLE administrador`.
3. `alerta.administrador_id` → `jugador_id` (o eliminar la columna si no se usa).
4. Seed: `ensure_system_user(SYSTEM_ADMIN_ID)` crea un `Jugador` de sistema.
5. Auth: reemplazar `get_current_admin_id` (stub) por auth de `Jugador`.
6. Password: unificar a un esquema de hashing.

---

## Opciones arquitectónicas

| Opción | Descripción | Riesgo | Domain rule / ADR-001 |
|---|---|---|---|
| **A — Unificar en `Jugador`** | Eliminar `Administrador`; admin = contexto (`creador_id`) | Medio-alto (auth, hashing, seed) | ✅ Cumple |
| **B — Dos tablas, FK a `administrador`** | `audit_logs.usuario_id → administrador.id` (o polimórfica) | Medio | ❌ Viola (dos identidades) |
| **C — Dos tablas, sin FK** | Relajar/eliminar la FK de auditoría | Bajo (parche) | ❌ No unifica; pierde integridad |
| **D — Mitigación puente** | Garantizar `jugador.id = SYSTEM_ADMIN_ID` | Bajo (temporal) | ❌ No unifica; sólo evita el fallo FK |

## Comparación de riesgos
- **A** concentra el esfuerzo (auth + hashing + seed) pero **resuelve la causa raíz** y cumple el dominio.
- **B/C** perpetúan la dualidad → contradicen la regla confirmada; deuda permanente.
- **D** es un parche válido **solo como puente temporal** si la unificación se difiere.

---

## Recomendación (única): **Opción A — Unificar la identidad en `Jugador`**

Es la única alineada con la regla de dominio confirmada y con ADR-001. `Administrador` se elimina como entidad; la condición de "administrador" es **contextual** (`tournaments.creador_id == jugador.id`), **sin rol permanente**. El actor de auditoría es siempre un `jugador.id` (incluido un `Jugador` de sistema para el scheduler), lo que **resuelve definitivamente** la FK rota.

### Decisión propuesta para ADR-005
1. **Una sola entidad de usuario: `Jugador`.** Eliminar `Administrador` (tabla, modelo, repo, service de password admin migrado a `Jugador`).
2. **"Administrador" = rol contextual**, derivado de ser creador del torneo. **Prohibido** un rol/jerarquía permanente.
3. **Actor de auditoría = `jugador.id`** siempre; `SYSTEM_ADMIN_ID` pasa a ser un **`Jugador` de sistema** (`ensure_system_user`).
4. **Auth admin real:** retirar el stub `get_current_admin_id`; usar auth de `Jugador` (Bearer) en los endpoints administrativos.
5. **Hashing único** de contraseña para `Jugador` (elegir bcrypt **o** pbkdf2 y unificar).
6. **Ejecución por sub-lotes** (auth + UC-01 sobre `jugador` → seed/actor de sistema → drop `administrador` vía nueva revisión Alembic → autorización de alertas), cada uno con `pytest` + validación Postgres.

---

## Bloqueos / prerequisitos (condición de reporte)
No hay **bloqueo estructural duro**, pero sí **dependencias de alta fricción** que deben resolverse **dentro** del lote de unificación, no antes de decidirlo:
- 🔶 **Reconciliación de hashing** bcrypt ↔ pbkdf2 (elegir uno; manejar credenciales existentes — en dev no hay datos).
- 🔶 **Sustitución del auth stub** `get_current_admin_id` por auth real de `Jugador` (cambia el contrato de `/admins/password` y `/alerts`).
- 🔶 **Definir autorización de alertas** sin admin global (¿usuario autenticado? ¿ámbito por torneo?).
- 🔶 **Migración al inglés / rutas** (`/admins/...`) queda **fuera** de este ADR (diferida), pero condiciona el diseño final de endpoints.

Ninguno impide la unificación; todos son resolubles en el lote. Se recomienda un **ADR/itinerario de auth** como primer sub-paso antes de tocar `domain/models/admin.py`.
