# ADR-004 — Estrategia de adopción de Alembic para el stack canónico

**Estado:** Propuesta (recomendación; resuelve el bloqueo #1 del plan del Lote Alembic)
**Fecha:** 2026-06-12
**ADRs relacionadas:** [ADR-001](./ADR-001-consolidacion-etapa-4.md), [ADR-002](./ADR-002-scheduler-vs-matches.md), [ADR-003](./ADR-003-scheduled-match-columns.md)

---

## Contexto

El plan del Lote Alembic detectó un **bloqueo crítico (#1)**: el stack canónico inglés (`tournaments`, `matches`, `registrations`, `audit_logs`) **nunca entró en Alembic**. La cabeza Alembic (`002`) solo conoce las 9 tablas legadas en español. El esquema real se ha gestionado de facto con `Base.metadata.create_all` (`main.py`), que crea las tablas inglesas al importar.

Estado:
- **Migración `001`** crea el legado español (`administrador, jugador, torneo, ronda, inscripcion, enfrentamiento, historialelo, logauditoria, alerta`).
- **Migración `002`** sincroniza secuencias de esas 9 tablas (solo PostgreSQL).
- **Sin migración** para el stack inglés ni para el drift de los Lotes 4.1–4.4 ni ADR-003.
- Una BD de dev existente tiene un esquema **mixto**: tablas legadas (de `001/002`) + tablas inglesas (de `create_all`), con `alembic_version = 002`.

Necesitamos elegir cómo adoptar Alembic como **fuente única de esquema** antes de generar la migración del lote.

---

## Opción 1 — Baseline + `alembic stamp`

Mantener `001/002` en el historial. Añadir una revisión `003` que lleve el esquema al estado canónico (incorporar el stack inglés + aplicar deltas 4.1–4.4 + ADR-003 + dropear legado). En BDs existentes (que ya tienen las tablas inglesas por `create_all`), usar `alembic stamp` para no recrearlas, y aplicar solo el delta in-place.

- **Ventajas:**
  - Preserva el historial de migraciones (linaje `001→002→003`).
  - Permite migración **in-place** que **conserva datos** (ALTER/DROP sobre tablas existentes).
  - Cambio incremental, menor disrupción para entornos ya desplegados.
- **Desventajas:**
  - Complejidad alta: hay que conciliar el esquema mixto (las tablas inglesas existen pero Alembic no las "conoce"); requiere `stamp` + ops condicionales/idempotentes.
  - El historial arrastra tablas legadas que se crean en `001` y se dropean en `003` (ruido).
  - `002` sincroniza secuencias de tablas que luego se eliminan (inconsistencia histórica).
- **Impacto BD existente:** medio — `stamp` para reconocer lo creado por `create_all`, luego delta in-place (rename, add/drop columnas, drop tablas legadas). Conserva datos.
- **Impacto entornos nuevos:** subóptimo — `001` crea 9 tablas legadas que `003` desmonta parcialmente (crear-para-luego-dropear).
- **Riesgo de pérdida de datos:** **bajo** si se ejecuta el delta in-place (preserva lo existente; solo dropea legado descartable).
- **Compatibilidad 4.1–4.4:** los deltas se aplican como operaciones explícitas en `003`.
- **Compatibilidad ADR-003:** `match_id` + drops de columnas se aplican in-place sobre `scheduled_matches`.

## Opción 2 — Squash (baseline único canónico)

Reemplazar `001/002` (y el `003` planeado) por **una sola migración baseline** que representa **únicamente el esquema canónico post-4.x** (autogenerada contra los modelos actuales). En BDs nuevas, esa migración crea todo correctamente. En BDs existentes (solo dev), recrear desde el baseline o `stamp` tras conciliación manual.

- **Ventajas:**
  - **Fuente única limpia:** una migración que coincide exactamente con los modelos canónicos; sin legado en el historial.
  - Elimina de raíz el split legado/inglés y el drift de `create_all`.
  - Entornos nuevos: un único `upgrade head` produce el esquema correcto sin crear-para-dropear.
  - Alinea con el objetivo de ADR-001 (una sola fuente de verdad).
- **Desventajas:**
  - **Pierde el historial** de migraciones (linaje legado).
  - En BDs existentes con datos requiere reconciliación manual / recreación → no apto si hay datos productivos a preservar.
- **Impacto BD existente:** alto si hay datos (hay que recrear o conciliar a mano); trivial si la BD es desechable (dev).
- **Impacto entornos nuevos:** **óptimo** — baseline directo y coherente con los modelos.
- **Riesgo de pérdida de datos:** **alto si existieran datos productivos**; nulo en entornos dev desechables.
- **Compatibilidad 4.1–4.4:** los cambios quedan **ya reflejados** en el baseline (no como deltas), porque el baseline se autogenera del estado actual de los modelos.
- **Compatibilidad ADR-003:** el baseline incluye `scheduled_matches` ya con `match_id` (FK→`matches.id`) y **sin** `ronda_id/inscripcion_a_id/inscripcion_b_id`.

---

## Factor decisivo: ¿hay datos productivos?

El bloqueo #2 del plan (¿existen datos en `torneo/ronda/inscripcion/logauditoria`?) determina el peso del riesgo:
- Este es un proyecto **académico/dev**; `create_all` ha sido el gestor de esquema y no hay evidencia de un despliegue productivo con datos a preservar.
- Las tablas legadas a eliminar ya están **desacopladas** (Lotes 4.3–4.4) y `scheduled_matches` está **vacía en prod** (F-3).

Si no hay datos productivos, el principal beneficio de la Opción 1 (preservación in-place) **no aporta valor**, y solo deja su desventaja (complejidad + historial ruidoso).

---

## Recomendación (única): **Opción 2 — Squash a un baseline canónico único**

Reemplazar `001`/`002` por **una migración baseline** autogenerada contra los modelos canónicos actuales, y **congelar `create_all`** (`main.py` deja de crear tablas; Alembic pasa a ser la fuente única).

### Justificación
1. El historial Alembic actual describe un **mundo legado en desmantelamiento** y nunca reflejó el stack inglés real → preservarlo aporta ruido, no valor.
2. `create_all` ha sido el gestor de facto: **no existe un linaje Alembic significativo que conservar**.
3. Contexto **dev/académico sin datos productivos** → la preservación in-place (única ventaja real de la Opción 1) es innecesaria.
4. Un baseline único es la materialización directa de **ADR-001** (fuente única de verdad) y deja los Lotes 4.1–4.4 y ADR-003 **ya incorporados** en el esquema, sin deltas frágiles sobre una cadena legada.
5. Entornos nuevos quedan correctos con un solo `upgrade head`, sin crear-para-dropear.

### Condición de seguridad (gate del bloqueo #2)
La recomendación **asume que se confirma la ausencia de datos productivos a preservar**. Si el bloqueo #2 revelara una BD con datos reales:
- **Cambiar a Opción 1** (baseline + `stamp` + delta in-place) para no destruir datos, **o**
- Hacer squash **solo tras** export/backup y un script de reconciliación de datos.

### Procedimiento previsto (a ejecutar en el Lote Alembic, NO aquí)
1. Confirmar bloqueo #2 (sin datos a preservar) + backup de cualquier BD existente.
2. Congelar `create_all` en `main.py`.
3. Reemplazar `alembic/versions/001`,`002` por un baseline canónico autogenerado de los modelos (incluye stack inglés, `scheduled_matches` post-ADR-003, `audit_logs.descripcion_cambio`; excluye `torneo/ronda/inscripcion/logauditoria`).
4. BDs existentes de dev: recrear desde el baseline (o `stamp` tras drop manual del legado).
5. Validar `alembic upgrade head` en PostgreSQL limpio + import smoke. (La suite SQLite sigue usando `create_all` desde modelos y no valida la migración.)

---

## Consecuencias
- **Positivas:** esquema y modelos convergen en una sola fuente; se elimina el drift `create_all`; el legado desaparece del historial; entornos nuevos reproducibles.
- **Negativas:** se pierde el historial de migraciones legado (aceptable); BDs existentes requieren recreación (trivial en dev).
- **Dependencia:** ejecutar **solo después** de cerrar el bloqueo #2.
