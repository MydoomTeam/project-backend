# ADR-003 — Futuro de las columnas semánticas de `ScheduledMatch`

**Estado:** Aprobada (ejecución diferida al lote Alembic)
**Fecha:** 2026-06-12
**ADRs relacionadas:** [ADR-001](./ADR-001-consolidacion-etapa-4.md) (consolidación), [ADR-002](./ADR-002-scheduler-vs-matches.md) (agenda vs bracket)

---

## Contexto

Tras el Lote 4.4 se eliminaron los modelos legados `Torneo`, `Inscripcion`, `Ronda`. El modelo de **agenda** `ScheduledMatch` (tabla `scheduled_matches`, ADR-002) conserva tres columnas que referenciaban semánticamente a esos conceptos ya inexistentes:

```
ronda_id          Integer NOT NULL   # leído solo en el mensaje de alerta del scheduler
inscripcion_a_id  Integer NOT NULL   # NO leído en ningún punto (metadato muerto)
inscripcion_b_id  Integer NOT NULL   # NO leído en ningún punto (metadato muerto)
```

Hechos verificados:
- **Sin `ForeignKey`** (enteros planos).
- El scheduler solo usa funcionalmente `estado_match` y `fecha_hora_programada` (filtro); `ronda_id` aparece únicamente en un string de mensaje (`scheduler.py:20`); `inscripcion_a_id`/`inscripcion_b_id` no se leen.
- La tabla está **vacía en producción** (F-3: feature de "vencidos" dormida).
- En el stack canónico, esos datos **ya viven autoritativamente en `MatchModel`**: ronda = `matches.ronda`; participantes = `matches.jugador1_id`/`jugador2_id`. Las 3 columnas son **duplicación desnormalizada**.

### Regla de dominio aplicable
- Existe **una sola identidad de usuario: `Jugador`**. `Administrador` no es una entidad independiente: es un `Jugador` actuando como creador/organizador (rol contextual al torneo). El creador no participa en su propio torneo.
- Implicación para este ADR: cualquier representación de "participantes" debe derivarse de `Jugador` (vía la partida), **no** reintroducir un concepto separado de inscripción/administrador.

---

## Opciones

### Opción 1 — Mantener como metadatos (sin FK)
- **Ventajas:** cero esfuerzo; preserva info por si la agenda se reactiva.
- **Desventajas:** perpetúa duplicación desnormalizada y columnas que apuntan a conceptos sin modelo; `NOT NULL` obliga a rellenar valores ficticios (hoy `1,1,2`).
- **Impacto scheduler:** ninguno.
- **Impacto tests:** ninguno.
- **Impacto Alembic:** las columnas se arrastran tal cual en la migración de `scheduled_matches`.
- **Compat. ADR-001:** parcial — contradice "una sola fuente de verdad" (duplica datos de `matches`).
- **Compat. ADR-002:** compatible (no exige FK), pero no aprovecha la FK opcional `match_id`.
- **Compat. unificación Jugador↔Administrador:** neutra (no toca usuarios), pero `inscripcion_*` evoca un concepto de inscripción que enturbia el modelo.

### Opción 2 — Eliminar las tres columnas
- **Ventajas:** elimina metadatos muertos; modelo de agenda honesto; quita duplicación.
- **Desventajas:** `ronda_id` se usa en el mensaje de alerta → hay que ajustar ese string; se pierde el detalle "qué partida/ronda venció" salvo que se reintroduzca por otra vía.
- **Impacto scheduler:** bajo — ajustar el mensaje (no asertado por tests).
- **Impacto tests:** bajo — quitar las columnas del seed simplificado; UC-02 no asserta sobre ellas.
- **Impacto Alembic:** `DROP COLUMN ronda_id, inscripcion_a_id, inscripcion_b_id`.
- **Compat. ADR-001:** alta (elimina duplicación).
- **Compat. ADR-002:** compatible; pero deja la agenda sin ningún enlace al bracket (no sabría a qué partida refiere).
- **Compat. unificación:** positiva (elimina el rastro de "inscripcion").

### Opción 3 — Reemplazar por relaciones reales (a los conceptos que representaban)
- **Ventajas:** integridad referencial.
- **Desventajas:** los referentes originales (`ronda`, `inscripcion`) **ya no existen** y no deben reintroducirse; "participantes" como entidad separada contradice la regla de dominio (los jugadores se derivan de la partida). Reconstruir FKs a `registrations` + un concepto de ronda sería volver al cluster legado.
- **Impacto scheduler:** alto (rediseño).
- **Impacto tests:** alto (seed con FKs válidas; FK activa en Postgres).
- **Impacto Alembic:** alto (FKs nuevas + backfill).
- **Compat. ADR-001:** baja — reintroduce estructura que ADR-001/Lote 4.4 eliminaron.
- **Compat. ADR-002:** desviada — ADR-002 contempla enlazar al bracket (`matches`), no a ronda/inscripcion.
- **Compat. unificación:** **negativa** — un FK a "inscripcion" reintroduce un concepto que la regla de un solo usuario quiere evitar.

### Opción 4 — Introducir `match_id` opcional hacia `matches`
- **Ventajas:** enlaza la agenda con la **entidad canónica** de competencia (`MatchModel`); ronda y participantes se **derivan** de la partida (`matches.ronda`, `matches.jugador1/2_id → jugador.id`); es exactamente la FK opcional que **ADR-002 ya contempla**.
- **Desventajas:** requiere poblar `match_id` cuando la feature de agenda se active (hoy dormida); mientras tanto queda `NULL`.
- **Impacto scheduler:** bajo — sigue filtrando por `estado_match`/`fecha_hora_programada`; el mensaje puede derivar ronda/partida de `match_id` cuando exista.
- **Impacto tests:** bajo — el seed puede dejar `match_id` nulo (la feature está dormida) o enlazar a un match real si se prueba el flujo completo.
- **Impacto Alembic:** `ADD COLUMN match_id INTEGER NULL` + FK opcional `→ matches.id`.
- **Compat. ADR-001:** alta (fuente única: los datos de la partida viven en `matches`).
- **Compat. ADR-002:** **total** (es la FK opcional explícitamente prevista).
- **Compat. unificación Jugador↔Administrador:** **positiva** — los participantes provienen de `matches → jugador`; no hay concepto de inscripción ni de administrador separado; encaja con "un solo usuario, rol contextual".

---

## Recomendación (única): **Opción 4 + Opción 2 combinadas**

**Introducir `match_id` opcional (FK → `matches.id`) como único enlace canónico de la agenda, y eliminar `ronda_id`, `inscripcion_a_id`, `inscripcion_b_id`.**

### Justificación
1. Las tres columnas son **duplicación desnormalizada** de datos que ya viven en `MatchModel` (ronda, participantes). Mantenerlas (Op.1) o relacionarlas a conceptos extintos (Op.3) contradice ADR-001 y la regla de dominio.
2. `scheduled_matches` es **agenda sobre la competencia real** (ADR-002). Su enlace natural y suficiente es `match_id → matches.id`; de ahí se derivan ronda y jugadores. Esto es precisamente la **FK opcional que ADR-002 ya autorizó**.
3. Es **neutral-positivo** para la futura unificación `Jugador↔Administrador`: no reintroduce "inscripcion" ni "administrador"; los participantes se obtienen de `matches → jugador` (una sola identidad de usuario).
4. Riesgo bajo y diferible: como la feature está dormida (F-3), `match_id` queda `NULL` hasta que se decida activar "match overdue"; el scheduler sigue operando con `estado_match`/`fecha_hora_programada`.

### Consecuencia para el scheduler
El mensaje de alerta deja de leer `ronda_id`; se simplifica (o deriva ronda desde `match_id` cuando exista). No hay aserción de test sobre ese string, así que el impacto es mínimo.

### Ejecución (NO en este ADR)
Se materializa en el **lote Alembic** junto al resto del drift (4.1–4.4):
- `ADD COLUMN match_id INTEGER NULL` + FK opcional `→ matches.id`,
- `DROP COLUMN ronda_id, inscripcion_a_id, inscripcion_b_id`,
- ajustar `scheduler.py` (mensaje) y el seed.

### Alternativa mínima si se rechaza tocar el scheduler ahora
Degradar a **Opción 2 pura** (eliminar las 3 columnas) y posponer `match_id` hasta activar la feature. Pierde el enlace al bracket pero no bloquea la limpieza. **No recomendada** frente a 4+2, porque dejaría la agenda sin forma de identificar la partida.

---

## Decisión sobre conflictos de dominio
No se detecta conflicto con la regla "Administrador es un Jugador organizador": la opción recomendada **elimina** el rastro de `inscripcion_*` (que evocaba un concepto separado) y deriva los participantes de `matches → jugador`, reforzando el modelo de **una sola identidad de usuario**.
