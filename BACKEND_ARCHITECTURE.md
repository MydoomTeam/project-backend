# Arquitectura Backend - ArenaSync (FastAPI)

## 1. Proposito y alcance

Este documento define la arquitectura backend para ArenaSync, un sistema monolitico de gestion de torneos de e-sports. El producto no es un videojuego; es software de gestion con reglas de negocio claras, datos persistentes y flujos auditables.

El backend debe priorizar:

- funcionalidad completa del MVP,
- clean code obligatorio,
- cero sobreingenieria,
- balance entre claridad y rendimiento (sin optimizacion extrema).

## 2. Restricciones del curso (obligatorias)

Basado en Restricciones del proyecto:

- Arquitectura monolitica. No microservicios ni sistemas distribuidos.
- Base de datos relacional (PostgreSQL, MySQL o SQLite).
- APIs externas solo como apoyo, nunca como nucleo del sistema.
- Debe cubrir analisis, diseno, desarrollo, pruebas y documentacion basica.

Separacion de repositorios segun la estructura oficial:

- project-docs: documentacion (este repo).
- project-backend: codigo backend.
- project-frontend: UI.

## 3. Principios de arquitectura

1. Clean code primero
- nombres claros, sin abreviaturas confusas.
- funciones pequenas y con una responsabilidad.
- evitar numeros magicos.
- comentarios solo cuando el codigo no puede explicarse por si mismo.

2. No sobreingenieria
- monolito modular con capas simples.
- patrones solo cuando resuelven un problema real.
- evitar frameworks extra, colas, buses de eventos o cache prematuro.

3. Balance de rendimiento
- optimizar solo donde haya evidencia de cuello de botella.
- primero claridad, despues micro-optimizaciones si son necesarias.

## 4. Stack backend propuesto

- Python 3.12+
- FastAPI (APIRouter para modularidad)
- Uvicorn (ASGI server)
- SQLAlchemy ORM
- Alembic para migraciones
- Pydantic para validacion de entrada/salida
- PostgreSQL
- bcrypt para hashing de contrasenas
- pytest para pruebas
- Ruff (o Flake8) para analisis estatico

## 5. Arquitectura de alto nivel

El equipo eligio arquitectura por capas, coherente con lo visto en el curso:

- Capa de presentacion/API: endpoints, validacion de entrada/salida, manejo de errores.
- Capa de logica de negocio: casos de uso, reglas y coordinacion de operaciones.
- Capa de acceso a datos: repositorios y consultas a la base de datos.
- Base de datos: almacenamiento relacional (PostgreSQL).

Monolito en capas, inspirado en el diagrama de referencia en Documentation/diagrams/Arquitectura.png:

1. API/Controllers (FastAPI APIRouter)
2. Services (casos de uso y reglas de negocio)
3. Repositories (acceso a datos con SQLAlchemy)
4. Domain/Models (entidades)
5. Database (PostgreSQL)

El diagrama de casos de uso esta en Documentation/diagrams/Diagram_CU.png y el modelo de datos en Documentation/diagrams/project_bd.png.

## 6. Estructura de carpetas (backend)

```text
project-backend/
  src/
    main.py
    config/
      settings.py
    api/
      health.py
      auth.py
      tournaments.py
      matches.py
      alerts.py
    services/
      auth_service.py
      tournament_service.py
      match_service.py
      alert_service.py
    repositories/
      user_repository.py
      tournament_repository.py
      match_repository.py
      alert_repository.py
    models/
      user.py
      admin.py
      player.py
      tournament.py
      round.py
      match.py
      registration.py
      alert.py
      elo_history.py
      audit_log.py
    schemas/
      auth.py
      tournament.py
      match.py
      alert.py
    tasks/
      scheduler.py
    db/
      session.py
  tests/
    unit/
    integration/
  alembic/
  requirements.txt
  README.md
```

## 7. Dominio y modelo de datos

Entidades principales (segun el diagrama BD):

- Torneo
- Ronda
- Enfrentamiento
- Inscripcion
- Jugador
- Administrador
- Alerta
- HistorialELO
- LogAuditoria

Reglas clave:

- Torneo tiene estados: Pendiente, Activo, En curso, Finalizado.
- Enfrentamientos generan actualizaciones de ELO y avance de ronda.
- Todas las operaciones criticas usan transacciones ACID.

## 8. Casos de uso (responsabilidad santgm56)

La especificacion completa esta en [USE_CASES_SANTGM56.md](USE_CASES_SANTGM56.md).

## 9. API REST (criterios)

Basado en lineamientos de API REST:

- recursos con sustantivos: /tournaments, /matches, /players
- usar HTTP methods correctos: GET, POST, PATCH, DELETE
- evitar rutas tipo /getTournaments
- soporte de filtros con query params

Ejemplos:

- POST /auth/login
- POST /admins/password
- POST /tournaments
- POST /tournaments/{id}/bracket
- PATCH /tournaments/{id}/status
- POST /matches/{id}/result
- GET /alerts

## 10. Seguridad

- Contrasenas con bcrypt, factor >= 12.
- Nunca almacenar contrasenas en texto plano.
- Validaciones de roles en el backend.
- Errores controlados, sin filtrar datos sensibles.

## 11. Scheduler y alertas

Requisito: alertas en menos de 30 segundos.

Propuesta simple y sin sobreingenieria:

- Scheduler interno en el monolito (APScheduler) con intervalo de 30s.
- Registra alertas en tabla Alerta y las expone en /alerts.
- Si el scheduler falla, la alerta queda persistida y se reintenta.

## 12. Testing y calidad

- Unit tests para servicios y validaciones.
- Integration tests para repositorios y endpoints principales.
- TDD recomendado en funcionalidades criticas.
- Analisis estatico con Ruff/Flake8 y formateo consistente.

## 13. Reglas anti-sobreingenieria (explicitas)

Si:

- usar FastAPI + SQLAlchemy + PostgreSQL.
- separar en capas claras y directas.
- escribir codigo legible antes que optimizado.

No:

- microservicios o multiples apps.
- colas, event bus, CQRS, DDD pesado.
- comentarios para explicar codigo confuso (mejor reescribir).

## 14. Fuentes y trazabilidad

- Restricciones del proyecto.pdf
- Clean code v2.pdf
- Diseno y arquitectura.pdf
- APIREST.pdf
- Documentation/diagrams/Arquitectura.png
- Documentation/diagrams/Diagram_CU.png
- Documentation/diagrams/project_bd.png
