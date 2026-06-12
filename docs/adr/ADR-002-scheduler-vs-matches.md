# ADR-002 — Resolver F-3: scheduler de "vencidos" vs consolidación de `matches`

**Estado:** Aprobada (refina la decisión 4 de [ADR-001](./ADR-001-consolidacion-etapa-4.md))
**Fecha:** 2026-06-12

---

## Contexto / Análisis

### Qué usa hoy `scheduler.py`
- Consulta **`Enfrentamiento`** (modelo legado, tabla `enfrentamiento`) filtrando `estado_match == "Pendiente"` y `fecha_hora_programada <= today`.
- Por cada vencido crea una `Alerta` (`tipo="match_overdue"`) y escribe `LogAuditoria` (`CREATE_ALERTA`); si no hay vencidos escribe `CHECK_OVERDUE_OK`.
- Depende de campos que solo existen en `enfrentamiento`: **`fecha_hora_programada`** (datetime) y **`estado_match`**, además de `ronda_id` (para el mensaje).

### Qué información existe en `matches` (`MatchModel`)
`id, torneo_id, ronda, posicion, bracket_tipo, jugador1_id, jugador2_id, ganador_id, estado`.
- **No tiene fecha/hora programada ni deadline.** `estado` usa el ciclo del bracket (`Pendiente/Programado/En curso/Finalizado`), no una semántica temporal.

### Hecho clave (F-3): la feature está **muerta en producción**
Ningún flujo productivo crea filas en `enfrentamiento` (el stack activo usa `matches`). El scheduler escanea una tabla que en prod siempre está vacía. **Solo los tests** la pueblan (vía `tests/helpers.seed_overdue_enfrentamiento`). Es decir: hoy el scheduler nunca dispara una alerta real.

### Tests que cubren la funcionalidad
`tests/integration/test_uc02_alertas.py` (5 tests), todos vía `seed_overdue_enfrentamiento` + `check_overdue_events`:
1. crea alerta para match vencido,
2. `/alerts` muestra la alerta,
3. no duplica alerta,
4. sin eventos → `CHECK_OVERDUE_OK`,
5. `PATCH /alerts/{id}/ack`.

Las aserciones son sobre `Alerta`/`LogAuditoria` y los endpoints de alertas; **dependen de `Enfrentamiento` + `fecha_hora_programada` solo a través del helper de seed.**

---

## Evaluación de opciones

| Opción | Riesgo código | Riesgo producto | Desbloquea borrar `enfrentamiento` | Conserva feature/tests |
|---|---|---|---|---|
| **A — `scheduled_at` en `matches` + poblarlo** | **Alto** | Bajo | Sí | Requiere reescribir helper + scheduler |
| **B — retirar "vencidos"** | Bajo | **Alto** | Sí | Elimina la feature y deja `/alerts` sin productor |
| **C — desacoplar: renombrar a modelo inglés propio** | **Bajo-medio** | Bajo | Sí (se renombra, no se borra) | Sí, con cambio mínimo |

**Por qué A es alto riesgo:** `matches` es un *slot* abstracto del bracket; "vencido" necesita un deadline real. Poblar `scheduled_at` exige nueva lógica de negocio y una fuente de duración que el `TournamentModel` inglés **no tiene** (la `duracion_ronda` vivía en el `torneo` legado). Cambia la semántica de `estado` y obliga a reescribir scheduler, helper y mensaje (`ronda_id`→`ronda`).

**Por qué B es alto riesgo de producto:** `gestionar alertas` es objetivo explícito en `PROJECT_CONTEXT`. `/alerts` y `ack` quedarían sin ningún productor; habría que rehacer el seeding de 4 de 5 tests por otra vía artificial. Se elimina capacidad documentada.

**Por qué C es el menor riesgo neto:** reconoce que "fixture programada con deadline" y "slot de bracket" son **conceptos distintos**, no duplicados. Mantiene la feature exactamente igual (solo se renombra a inglés), conserva los 5 tests con cambio mínimo, y permite que la consolidación de `matches` avance sin tocar el scheduler.

---

## Decisión: **Opción C (desacoplar + renombrar a inglés)**

Renombrar `Enfrentamiento` → **`ScheduledMatch`** (tabla `scheduled_matches`), con columnas en inglés (`status`, `scheduled_at`, `round_id`, …), referenciando opcionalmente `matches.id`. El scheduler sigue operando sobre este modelo. **No** se fuerza la semántica temporal dentro de `matches`.

Esto cumple ADR-001 (consolidar la competencia en `matches`, inglés) **sin** borrar una capacidad: `enfrentamiento` no era un duplicado funcional de `matches`, sino el portador de datos de agenda que `matches` no tiene.

**Decisión de seguimiento (separada, de producto):** definir si "match overdue" debe volverse **real en producción**:
- Si **sí** → historia futura: poblar `ScheduledMatch` cuando un match del bracket se vuelve jugable (en `iniciar_torneo`/avance), reintroduciendo una fuente de duración en el modelo inglés (variante A sobre el modelo desacoplado).
- Si **no/aplazado** → queda como feature inglesa coherente pero dormida (igual que hoy), sin deuda de idioma ni dependencia legada.

---

## Impacto

- **Código:** `scheduler.py` (import + nombres de campos), modelo renombrado, `repositories` de alerta/audit sin cambios. Sin nueva lógica de negocio.
- **API:** ninguno (la feature no expone rutas nuevas; `/alerts` y `ack` intactos).
- **Producto:** se preserva la capacidad de alertas; comportamiento externo idéntico.
- **Consolidación:** desbloquea la eliminación del concepto legado "enfrentamiento" como duplicado de `matches`, separándolo como concepto de agenda.

## Migraciones necesarias (Alembic) — *a diseñar en ejecución, no ahora*

1. `ALTER TABLE enfrentamiento RENAME TO scheduled_matches`.
2. Renombrar columnas a inglés usadas por el scheduler: `estado_match→status`, `fecha_hora_programada→scheduled_at`, `ronda_id→round_id` (las demás se pueden renombrar en el mismo lote por consistencia).
3. (Opcional, recomendado) FK `scheduled_matches.match_id → matches.id` para enlazar agenda con el slot de bracket.
4. Sin migración de datos (la tabla está vacía en prod).
5. Congelar `create_all` y versionar el cambio (alineado con ADR-001, decisión de migración).

## Compatibilidad con tests

- `tests/helpers.py`: `seed_overdue_enfrentamiento` → `seed_overdue_scheduled_match`, usando `ScheduledMatch(status="Pendiente", scheduled_at=past, …)`. **Único cambio sustantivo.**
- `tests/integration/test_uc02_alertas.py`: actualizar el import del helper; las **aserciones no cambian** (siguen sobre `Alerta`/`LogAuditoria`/`/alerts`).
- `tests/conftest.py`: el `# noqa: F401` de `Enfrentamiento` pasa a `ScheduledMatch` (registro de tabla).
- Resultado esperado: los 5 tests de UC-02 permanecen verdes con cambios solo de nombre/estructura, sin ocultar regresiones.
