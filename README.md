# ArenaSync Backend

Backend monolítico con FastAPI + SQLAlchemy y PostgreSQL 16 en Docker. Gestión de torneos con múltiples formatos de eliminación, sistema de ELO adaptativo, registro y login de jugadores.

> **Convención de idioma:** todo el contrato técnico (rutas, parámetros, claves JSON, tablas y columnas) está en **inglés**. Los **valores de negocio** (estados, formatos, roles, mensajes) permanecen en **español** porque son contenido visible para el usuario. El frontend se encarga de presentarlos.

## Stack

- Python 3.12+
- FastAPI 0.115
- SQLAlchemy 2.0
- PostgreSQL 16 (Docker)
- Driver: psycopg2-binary
- Migraciones: Alembic

## Estructura

```
project-backend/
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
├── setup.bat / setup.sh
├── alembic/            # Migraciones de esquema
├── scripts/            # Helpers (reset_db.py, seed_overdue_postgres.py)
└── src/
    └── app/
        ├── api/            # Endpoints de torneos y partidas
        ├── controllers/    # Endpoints de auth, admin, jugadores y alertas
        ├── core/           # Base de datos, auth, configuración
        ├── domain/         # Modelos y schemas del stack de jugadores/alertas
        ├── models/         # Modelos ORM (tournaments, matches, registrations, audit_logs)
        ├── repositories/   # Acceso a base de datos (ORM, sin SQL crudo)
        ├── schemas/        # Schemas Pydantic de request/response
        ├── services/       # Lógica de negocio
        └── tasks/          # Scheduler de alertas
tests/
├── e2e/          # Tests HTTP end-to-end con TestClient
├── integration/  # Tests con base de datos SQLite en memoria
└── unit/         # Tests unitarios con monkey-patching (sin BD)
```

## Configuración de entorno

Copiar `.env.example` a `.env` y ajustar:

```
DATABASE_URL=postgresql+psycopg2://arenasync:arenasync@localhost:5432/arenasyncdb
```

> Los valores de `docker-compose.yml` deben coincidir con `DATABASE_URL`.
> `.env` **no** se versiona (está en `.gitignore`): cada quien crea el suyo desde `.env.example`.

## Arranque

### Opción A — Script automático (recomendado, primera vez)

El script levanta Docker, crea el venv, instala dependencias, copia `.env` y **aplica las migraciones** (`alembic upgrade head`):

```bash
# Windows
.\setup.bat

# Linux/macOS
./setup.sh
```

Luego, con el venv activado, arranca el servidor:

```bash
uvicorn app.main:app --reload --app-dir src
```

### Opción B — Manual (paso a paso)

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows (PowerShell)
source .venv/bin/activate        # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar .env desde el ejemplo
copy .env.example .env           # Windows
cp .env.example .env             # Linux/macOS

# 4. Levantar la base de datos (PostgreSQL en Docker)
docker compose up -d

# 5. Crear/actualizar el esquema con Alembic  (OBLIGATORIO)
alembic upgrade head

# 6. Ejecutar el servidor
uvicorn app.main:app --reload --app-dir src
```

Docs interactivos (Swagger): `http://localhost:8000/docs`

> ### ¿Qué hace `alembic upgrade head` y por qué es obligatorio?
> **Alembic** es la herramienta de **migraciones** de SQLAlchemy: lleva el control de versiones del **esquema de la base de datos** (tablas y columnas) mediante archivos en `alembic/versions/`, cada uno con un `upgrade()` (aplicar) y un `downgrade()` (revertir).
>
> En este proyecto, la app **ya no crea las tablas sola** (`create_all` está desactivado a propósito): la **única fuente de verdad del esquema es Alembic**. Por eso, sobre una base de datos vacía **debes ejecutar `alembic upgrade head`** una vez; si no, el servidor arranca pero **no existen las tablas** y toda operación de BD falla.
>
> - `alembic upgrade head` → aplica todas las migraciones pendientes hasta la última.
> - `alembic downgrade -1` → revierte la última migración.
> - `alembic current` → muestra en qué versión está tu BD.
>
> Solo necesitas volver a correrlo cuando se agreguen nuevas migraciones (cambios de esquema).

## Ejecutar tests

```bash
pytest
```

---

## Guía de uso de la API

### Autenticación

La mayoría de endpoints requieren un token. Cada request debe incluir:

```
Authorization: Bearer <token>
```

El token se obtiene al hacer login. No hay roles separados — cualquier jugador puede crear torneos. El que crea el torneo se convierte en su administrador (solo él puede generar el bracket, iniciar el torneo, registrar resultados y cancelarlo).

---

### Módulo 1 — Registro y Login

#### 1. Registrar un jugador

```
POST /users
```

```json
{
  "username": "carlos99",
  "email": "carlos@gmail.com",
  "password": "MiClave2026!"
}
```

**Reglas de `username`:** solo letras y números, entre 3 y 30 caracteres.

**Reglas de `password`:** mínimo 8 caracteres, con al menos una letra, un número y un símbolo (`! @ # $ % ^ & ( ) - _ + = [ ] { } ; : . , < > / ?`).

**Respuesta — 201:**

```json
{
  "id": 1,
  "username": "carlos99",
  "email": "carlos@gmail.com",
  "role": "JUGADOR",
  "last_access_date": "2026-06-08",
  "global_elo": 0
}
```

---

#### 2. Hacer login (crear sesión)

```
POST /sessions
```

```json
{
  "identifier": "carlos99",
  "password": "MiClave2026!"
}
```

> En `identifier` puedes poner el `username` **o** el `email`.

**Respuesta — 200:**

```json
{
  "access_token": "eyJ1c2VyX2lkIjox...",
  "token_type": "bearer",
  "player": {
    "id": 1,
    "username": "carlos99",
    "email": "carlos@gmail.com",
    "role": "JUGADOR",
    "last_access_date": "2026-06-08",
    "global_elo": 0
  }
}
```

> Usa el `access_token` en los demás requests: `Authorization: Bearer <access_token>`.

---

### Módulo 2 — Torneos

> Requieren `Authorization: Bearer <token>`.

#### 3. Ver torneos disponibles

```
GET /tournaments/available
```

Sin body. Devuelve los torneos en estado `"Pendiente"`.

#### 4. Crear un torneo

```
POST /tournaments
```

```json
{
  "name": "Copa Semestral 2026",
  "elimination_type": "Eliminación Sencilla",
  "rounds": 3
}
```

**Valores válidos de `elimination_type`:** `"Eliminación Sencilla"`, `"Eliminación Doble"`, `"Round Robin"`, `"Swiss"`.

**Límites:**

| Formato | Mín. jugadores | Máx. rondas |
|---|---|---|
| Eliminación Sencilla | 2 | 7 |
| Eliminación Doble | 4 | 5 |
| Round Robin | 3 | 3 |
| Swiss | 4 | 7 |

**Respuesta — 201:**

```json
{
  "id": 5,
  "name": "Copa Semestral 2026",
  "elimination_type": "Eliminación Sencilla",
  "rounds": 3,
  "status": "Pendiente",
  "creator_id": 1
}
```

#### 5. Ver detalle de un torneo

```
GET /tournaments/5
```

```json
{
  "id": 5,
  "name": "Copa Semestral 2026",
  "elimination_type": "Eliminación Sencilla",
  "rounds": 3,
  "status": "Pendiente",
  "creator_id": 1,
  "creator_name": "carlos99",
  "total_participants": 0
}
```

#### 6. Inscribirse en un torneo

```
POST /tournaments/5/registrations
```

Sin body — el `tournament_id` va en la ruta y el jugador se identifica por su token. El creador no puede inscribirse en su propio torneo.

**Respuesta — 201:**

```json
{
  "id": 12,
  "tournament_id": 5,
  "player_id": 2,
  "status": "Confirmado"
}
```

#### 7. Cancelar tu inscripción

```
DELETE /tournaments/5/registrations
```

Solo si el torneo está en `"Pendiente"`. Sin body. Devuelve **204**.

> Si te vuelves a inscribir en el mismo torneo, el sistema reutiliza tu inscripción anterior.

#### 8. Cancelar un torneo (solo el creador)

```
DELETE /tournaments/5
```

Solo el creador, y solo si está en `"Pendiente"` o `"Listo para iniciar"`. Sin body. Devuelve **204**.

> Al cancelar, el torneo se borra junto con sus inscripciones y matches. El nombre queda libre.

---

### Módulo 3 — Bracket y Partidas

> Generar, iniciar, registrar resultados y cancelar: solo el **creador**.

#### 9. Generar el bracket (solo el creador)

```
POST /tournaments/5/bracket
```

El torneo debe estar en `"Pendiente"` con suficientes jugadores. Pasa a `"Listo para iniciar"`.

**Respuesta — 201:**

```json
{
  "tournament_id": 5,
  "tournament_status": "Listo para iniciar",
  "matches": [
    {
      "id": 10,
      "tournament_id": 5,
      "round": 1,
      "position": 0,
      "bracket_type": "ganadores",
      "player1_id": 1,
      "player2_id": 3,
      "winner_id": null,
      "status": "Programado"
    }
  ]
}
```

#### 10. Iniciar el torneo (solo el creador)

```
POST /tournaments/5/start
```

El torneo debe estar en `"Listo para iniciar"`. Sin body. Pasa a `"En curso"` y activa la primera ronda. Los BYEs se resuelven solos. Si lo intenta alguien que no es el creador → **403**.

#### 11. Ver todos los matches

```
GET /tournaments/5/bracket
```

Devuelve un `BracketResponse` (mismo formato que el punto 9).

#### 12. Registrar el resultado de un match (solo el creador)

```
POST /tournaments/5/matches/10/result
```

```json
{
  "winner_id": 1
}
```

`winner_id` debe ser uno de los dos participantes; si no, **400**.

**Respuesta — 200:**

```json
{
  "match": {
    "id": 10,
    "tournament_id": 5,
    "round": 1,
    "position": 0,
    "bracket_type": "ganadores",
    "player1_id": 1,
    "player2_id": 3,
    "winner_id": 1,
    "status": "Finalizado"
  },
  "winner_new_elo": 1016,
  "loser_new_elo": 984,
  "tournament_finished": false
}
```

**Automático al registrar un resultado:**
- El match pasa a `"Finalizado"` y se actualiza el ELO de ambos.
- **Eliminación Sencilla:** el ganador avanza solo.
- **Eliminación Doble:** el ganador sube en el bracket de ganadores; el perdedor baja al de perdedores.
- **Swiss:** al cerrar todos los matches de una ronda, se genera la siguiente.
- Cuando no hay más matches, el torneo pasa a `"Finalizado"` solo (`tournament_finished: true`).

#### 13. Ver el ranking

```
GET /tournaments/5/ranking
```

```json
{
  "tournament_id": 5,
  "elimination_type": "Swiss",
  "status": "Finalizado",
  "ranking": [
    { "position": 1, "player_id": 1, "wins": 4, "global_elo": 1048 },
    { "position": 2, "player_id": 3, "wins": 3, "global_elo": 1024 }
  ]
}
```

#### 14. Ver el historial de un jugador

```
GET /tournaments/5/players/1/history
```

Devuelve una lista de matches (formato `MatchResponse`). Disponible en cualquier estado.

---

### Flujo completo de ejemplo (4 jugadores)

```
1. Registrar 4 jugadores        POST /users
2. Login de cada uno            POST /sessions          → guardar access_token e id
3. Jugador 1 crea el torneo     POST /tournaments       → guardar tournament_id (ej: 5)
4. Jugadores 2,3,4 se inscriben POST /tournaments/5/registrations   (cada uno con su token)
5. Jugador 1 genera el bracket  POST /tournaments/5/bracket
6. Jugador 1 inicia el torneo   POST /tournaments/5/start
7. Ver matches y sus IDs        GET  /tournaments/5/bracket
8. Registrar resultados         POST /tournaments/5/matches/{match_id}/result  body: { "winner_id": 1 }
9. Ver ranking final            GET  /tournaments/5/ranking
10. Ver historial               GET  /tournaments/5/players/1/history
```

---

### Errores comunes

| Código | Significado | Causa probable |
|---|---|---|
| `401` | No autenticado | Falta `Authorization` o token inválido |
| `403` | Sin permiso | Acción reservada al creador del torneo |
| `404` | No existe | `tournament_id`, `match_id` o `player_id` inexistente |
| `400` | Datos incorrectos | Ya inscrito, estado incorrecto, `winner_id` no participante, rondas fuera de límite |
| `409` | Conflicto | `username` o `email` ya registrado |
| `422` | Validación | Falta un campo o `password`/`username` no cumple las reglas |

---

### Formatos de eliminación

- **Eliminación Sencilla:** una derrota elimina. Bracket en potencia de 2; los mejores por ELO reciben BYE.
- **Eliminación Doble:** dos brackets (ganadores/perdedores); se elimina al perder dos veces; Gran Final entre el último de cada bracket.
- **Round Robin:** todos contra todos (`n*(n-1)/2` partidas); desempate por ELO; sin BYEs.
- **Swiss:** mismo número de rondas; ronda 1 por ELO, siguientes por victorias evitando repetir rivales; BYE si hay número impar.

**BYE:** match con `player2_id = null` → se cierra solo (`winner_id = player1_id`, `status = "Finalizado"`), el ganador avanza sin jugar y no hay cambio de ELO.

### Sistema ELO (factor K adaptativo)

| ELO actual | Factor K |
|---|---|
| < 1000 | 40 |
| 1000 – 2000 | 32 |
| > 2000 | 16 |

```
E_winner = 1 / (1 + 10 ^ ((loser_elo - winner_elo) / 400))
winner_new_elo = winner_elo + K * (1 - E_winner)
loser_new_elo  = loser_elo  + K * (0 - E_winner)
```

---

### Otros endpoints

#### Ver datos de un jugador

```
GET /players/1
```

No requiere token. Devuelve un `PlayerRead`.

#### Actualizar contraseña

```
POST /admins/password
```

```json
{
  "current_password": "ClaveActual123!",
  "password": "NuevaClave123!",
  "password_confirm": "NuevaClave123!"
}
```

El jugador objetivo se identifica por el token (`Authorization: Bearer`).

#### Actualizar avatar por URL

```
PUT /players/me/avatar
```

```json
{
  "avatar_url": "https://cdn.ejemplo.com/perfiles/user1.jpg"
}
```

Para limpiar el avatar, enviar `avatar_url: null`.

#### Subir avatar por archivo (multipart)

```
POST /players/me/avatar-file
Content-Type: multipart/form-data
```

Campo del formulario:
- `avatar`: archivo de imagen (`.jpg`, `.png`, `.webp`, máximo 2 MB)

La API guarda el archivo en `uploads/avatars` y retorna el perfil con la `avatar_url` final.

#### Ver alertas de matches vencidos

```
GET /alerts
```

```json
{
  "items": [
    {
      "id": 3,
      "event_type": "match_overdue",
      "message": "Enfrentamiento 7 vencido.",
      "created_at": "2026-06-12",
      "status": "nueva"
    }
  ]
}
```

#### Reconocer una alerta

```
PATCH /alerts/3/ack
```

Devuelve `{ "message": "acknowledged" }`.

#### Health check

```
GET /health
```

Responde `{ "status": "ok" }`.
</content>
