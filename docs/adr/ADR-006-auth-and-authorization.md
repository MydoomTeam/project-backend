# ADR-006 — Autenticación y Autorización

**Estado:** Propuesta (prerequisito de ADR-005)
**Fecha:** 2026-06-12
**ADRs relacionadas:** [ADR-001](./ADR-001-consolidacion-etapa-4.md), [ADR-004](./ADR-004-alembic-adoption-strategy.md), [ADR-005](./ADR-005-user-identity.md)

---

## Contexto

ADR-005 unifica la identidad en `Jugador`. Antes de implementar sus sub-lotes (5a–5d) hay que cerrar tres decisiones transversales para no reescribir trabajo: **hashing**, **modelo de auth** de los endpoints administrativos/alertas, y **estrategia de rutas REST**.

Estado actual verificado:
- **Token propio** (no JWT): `base64({"sub":id,"iat":...}).hmac_sha256(AUTH_SECRET)`. `get_current_user` (Bearer) devuelve `jugador.id`. **No hay `exp`** → los tokens no expiran.
- **Hashing dual:** `Jugador` usa **pbkdf2_hmac-sha256** (100k iters, formato `salt$hash` **sin metadatos** de algoritmo/coste); `Administrador` usa **bcrypt** (rounds=12). `bcrypt>=4.1.2` ya es dependencia.
- **Auth admin/alertas = stub:** `get_current_admin_id() → return 1` (sin autenticación real). El stack de torneos usa auth real (`get_current_user`).

---

## 1. Esquema de hashing definitivo → **bcrypt**

**Decisión:** estandarizar **toda** contraseña de `Jugador` en **bcrypt** (rounds=12); eliminar pbkdf2.

- **Ventajas:** formato **autodescriptivo** (`$2b$12$…` lleva algoritmo+coste → actualizable sin romper hashes existentes), recomendado por OWASP, **ya es dependencia**. pbkdf2 actual (100k) está por debajo de la guía OWASP y su formato `salt$hash` **no versiona** algoritmo/iteraciones → callejón sin salida evolutivo.
- **Friccion:** cambiar `jugador_service._hash_password`/`_verificar_password` a bcrypt. **Sin datos productivos** (ADR-004) → no hay re-hash de credenciales reales.
- **Descartado:** mantener pbkdf2 (formato no versionado, iteraciones bajas); mantener ambos (dualidad innecesaria al desaparecer `Administrador`).

## 2. Modelo de autenticación (endpoints admin/alertas) → **auth real única (`get_current_user`)**

**Decisión:** eliminar el stub `get_current_admin_id`; **todos** los endpoints usan `get_current_user` (Bearer → `jugador.id`). Sin admin global ni rol permanente (regla de dominio ADR-005).

- **`POST /admins/password`** → "el **usuario autenticado** cambia su **propia** contraseña". Opera sobre `jugador.id` del token (sin id de destino → sin IDOR).
- **`GET /alerts` y `PATCH /alerts/{id}/ack`** → requieren **usuario autenticado** (cualquier `Jugador`). Las alertas son eventos de sistema (scheduler) y hoy **no** están ligadas a un torneo (`Alerta` no tiene `torneo_id`).
  - **Diferido (no en este ADR):** acotar alertas **por torneo** (visibles solo al creador) cuando se active la feature de "vencidos" (F-3) y se añada el vínculo `alerta → torneo/match`. Por ahora, "autenticado" sustituye al stub sin inventar jerarquía.
- **"Administrador" = contexto**, derivado de `tournaments.creador_id == jugador.id` (ya implementado en el stack de torneos). **Prohibido** un rol global.

## 3. Estrategia de rutas REST → **mantener paths ahora; renombrar en el lote de inglés**

**Decisión:** durante ADR-005 **no** se renombran las rutas. Se conservan `/admins/password`, `/alerts`, `/alerts/{id}/ack` (cambia su **handler** y su **auth**, no su URL). El renombrado a inglés/identidad (`/users/...`, `/sessions`, etc.) se hace en el **lote de migración REST** (ADR-001 #6) con capa de compatibilidad.

- **Razón:** no mezclar dos breaking changes (unificación de identidad + cambio de contrato de URL) en el mismo lote → validación y rollback más simples.
- **Matiz aceptado:** `/admins/password` cambia de "stub (cualquiera→admin 1)" a "requiere Bearer y opera sobre el usuario autenticado". Es un cambio de contrato **de seguridad** (deseable), con la URL estable.

## 4. Compatibilidad con ADRs
| ADR | Compatibilidad |
|---|---|
| **ADR-001** | ✅ Hashing y auth únicos refuerzan la fuente única; renombrado de rutas se mantiene en su lote diferido. |
| **ADR-002 / ADR-003** | ✅ Ortogonales (agenda/bracket no afectados). |
| **ADR-004** | ✅ Hashing/auth son cambios de **código**; ADR-006 **no añade migración**. La única migración (drop `administrador`) vive en ADR-005. |
| **ADR-005** | ✅ ADR-006 fija los prerequisitos (1)–(3) que 5a–5d necesitan. |

## 5. Impacto en tests
- **Hashing:** `test_uc01_password` y `test_admin_service_unit` ya usan bcrypt → migran a `Jugador` casi sin cambios de hashing. `jugador_service` (registro/login) pasa de pbkdf2 a bcrypt; `test_auth` (e2e) **monkeypatchea** `registrar_usuario`/`iniciar_sesion`, así que no prueba el hashing directamente → no se rompe.
- **Auth:** `conftest` debe **quitar** el override de `get_current_admin_id` y apoyarse en el de `get_current_user` (ya presente, `→1`). Endpoints admin/alertas pasan a exigir token (cubierto por el override en tests).
- **FK de auditoría:** **recomendado activar `PRAGMA foreign_keys=ON`** en el `engine` de tests para que la suite detecte el riesgo crítico de ADR-005 (hoy SQLite lo enmascara).

## 6. Impacto en seguridad
- **Mejora mayor:** eliminar el stub convierte `/admins/password` y `/alerts` (hoy **efectivamente sin auth**) en endpoints autenticados.
- **bcrypt** > pbkdf2-100k (coste embebido, actualizable).
- **Sin IDOR:** el cambio de contraseña opera sobre el id del token, no sobre un id arbitrario.
- **Deuda de seguridad reportada (fuera de alcance de ADR-006, recomendada para un ADR-007 de tokens):** el token **no expira** (`exp` ausente) y es un esquema propio (no JWT). Mitigación futura: añadir `exp` y/o rotación. **No bloquea** ADR-005/006.

## 7. Impacto en migraciones
- **ADR-006 no genera migración alguna** (hashing y auth son código).
- En dev no hay credenciales que re-hashear. La única migración asociada (drop `administrador`, ajuste `alerta`) pertenece a ADR-005 como **nueva revisión sobre el baseline** (no re-squash; respeta ADR-004).

## 8. Estrategia de transición sin romper funcionalidades
1. **bcrypt en `Jugador`** dentro del sub-lote de password (5c). Sin datos → sin esquema dual. *(Si hubiera datos: verificar ambos formatos y re-hashear en login.)*
2. **Auth real** (5b): sustituir `get_current_admin_id` por `get_current_user`; **conservar URLs**; actualizar overrides de `conftest`.
3. **Comportamiento preservado:** endpoints de torneo intactos (ya con auth real); `/alerts` sirve los mismos datos, ahora autenticado.
4. **Validación por sub-lote:** `pytest` + (recomendado) FK activa en SQLite + `alembic upgrade head` en Postgres tras 5d.

---

## Recomendación única (síntesis)
1. **Hashing:** **bcrypt** (rounds=12) como esquema único; eliminar pbkdf2.
2. **Auth:** **`get_current_user` único**; sin admin global; `/admins/password` = auto-servicio; `/alerts` = autenticado (scoping por torneo **diferido**).
3. **Rutas:** **conservar paths** en ADR-005; renombrar en el lote REST (ADR-001).

## Orden de ejecución recomendado
1. **Aprobar ADR-006** (cierra hashing/auth/rutas).
2. **(Opcional) Endurecer tests:** activar `PRAGMA foreign_keys=ON` para detectar la FK de auditoría antes de migrar.
3. **5a** — `Jugador` de sistema (`ensure_system_user`) → cierra el riesgo crítico de la FK.
4. **5b** — auth real en admin/alertas (stub fuera; URLs estables).
5. **5c** — password de `Jugador` en bcrypt (UC-01 sobre `jugador`).
6. **5d** — eliminar `Administrador` (modelo/repo/service) + nueva revisión Alembic.
7. **(Posterior)** lote de rutas REST en inglés (ADR-001) + ADR-007 de tokens (`exp`).

---

## Bloqueos arquitectónicos
**No hay bloqueo estructural duro.** Decisiones de diseño quedan cerradas por este ADR. Se reportan dos **deudas no bloqueantes**:
- 🔶 **Token sin expiración** (`exp` ausente) → recomendado ADR-007 (tokens) tras ADR-005; no impide la unificación.
- 🔶 **Autorización de alertas "autenticado"** es interina; el scoping por torneo depende de ligar `Alerta` a torneo/match (feature dormida F-3) → diferido, documentado.
