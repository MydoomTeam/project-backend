# ArenaSync Backend

Backend monolítico con FastAPI + SQLAlchemy y PostgreSQL 16 en Docker. Gestión de torneos con múltiples formatos de eliminación, sistema de ELO adaptativo, registro y login de jugadores.

## Stack

- Python 3.12+
- FastAPI 0.115
- SQLAlchemy 2.0
- PostgreSQL 16 (Docker)
- Driver: psycopg2-binary

## Estructura

```
project-backend/
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── setup.bat / setup.sh
└── src/
    └── app/
        ├── api/            # Endpoints de torneos y partidas
        ├── controllers/    # Endpoints de auth, admin y alertas
        ├── core/           # Base de datos, auth, dependencias
        ├── domain/         # Modelos y schemas del dominio original
        ├── models/         # Modelos ORM (torneos, matches, inscripciones)
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

Crear `.env` desde el ejemplo:

```
DATABASE_URL=postgresql+psycopg2://arenasync:arenasync@localhost:5432/arenasyncdb
```

> Los valores de `docker-compose.yml` deben coincidir con `DATABASE_URL`.

## Arranque

**Con scripts automáticos:**

```bash
# Windows
setup.bat

# Linux/macOS
./setup.sh
```

**Manual:**

```bash
# 1. Crear entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate       # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar .env
copy .env.example .env

# 4. Levantar base de datos
docker compose up -d

# 5. Ejecutar servidor
uvicorn app.main:app --reload --app-dir src
```

Docs interactivos: `http://localhost:8000/docs`

## Ejecutar tests

```bash
pytest tests/
```

---

## Guía de uso de la API

### Cómo funciona la autenticación

La mayoría de endpoints requieren que el servidor sepa quién eres. Cada request debe incluir este header:

```
Authorization: Bearer <token>
```

El token lo obtienes al hacer login. No hay roles separados — cualquier jugador puede crear torneos. El que crea el torneo se convierte automáticamente en su administrador (solo él puede generar el bracket, iniciar el torneo y registrar resultados).

---

### Módulo 1 — Registro y Login

#### 1. Registrar un jugador

```
POST http://localhost:8000/usuarios/registrar
```

```json
{
  "nombre_usuario": "carlos99",
  "correo_electronico": "carlos@gmail.com",
  "contrasena": "MiClave2026!"
}
```

**Reglas del nombre de usuario:** solo letras y números, entre 3 y 30 caracteres. Sin espacios ni símbolos.

**Reglas de la contraseña:** mínimo 8 caracteres y debe tener obligatoriamente las tres cosas:
- Al menos una letra (mayúscula o minúscula)
- Al menos un número
- Al menos un símbolo: `! @ # $ % ^ & ( ) - _ + = [ ] { } ; : . , < > / ?`

Ejemplos válidos: `Arena2026!`, `Password1@`, `mi3Clave#`

**Respuesta exitosa — 201:**

```json
{
  "id": 1,
  "nombre_usuario": "carlos99",
  "correo_electronico": "carlos@gmail.com",
  "rol": "JUGADOR",
  "elo_global": 0,
  "fecha_ultimo_acceso": "2026-06-08"
}
```

> Guarda el `id` — es tu identificador de jugador.

---

#### 2. Hacer login

```
POST http://localhost:8000/usuarios/login
```

```json
{
  "identificador": "carlos99",
  "contrasena": "MiClave2026!"
}
```

> En `identificador` puedes poner el nombre de usuario **o** el correo electrónico.

**Respuesta exitosa — 200:**

```json
{
  "access_token": "eyJ1c2VyX2lkIjoxLCJpYXQiOjE3NDk0MjU2MDB9.Xk2pR9mNvTqLs3fWoA7c",
  "token_type": "bearer",
  "jugador": {
    "id": 1,
    "nombre_usuario": "carlos99",
    "correo_electronico": "carlos@gmail.com",
    "rol": "JUGADOR",
    "elo_global": 0,
    "fecha_ultimo_acceso": "2026-06-08"
  }
}
```

> Copia el `access_token`. Úsalo en todos los demás requests así:
> ```
> Authorization: Bearer eyJ1c2VyX2lkIjoxLCJpYXQiOjE3NDk0MjU2MDB9.Xk2pR9mNvTqLs3fWoA7c
> ```

---

### Módulo 2 — Torneos

> Todos estos endpoints requieren el header `Authorization: Bearer <token>`

#### 3. Ver torneos disponibles para inscribirse

```
GET http://localhost:8000/tournaments/available
```

No lleva body. Devuelve la lista de torneos en estado `"Pendiente"`.

---

#### 4. Crear un torneo

```
POST http://localhost:8000/tournaments
```

```json
{
  "nombre": "Copa Semestral 2026",
  "tipo_eliminacion": "Eliminación Sencilla",
  "rondas": 3
}
```

**Valores válidos para `tipo_eliminacion`:**

| Valor exacto | Descripción |
|---|---|
| `"Eliminación Sencilla"` | Una derrota y quedas fuera |
| `"Eliminación Doble"` | Necesitas perder dos veces para quedar fuera |
| `"Round Robin"` | Todos juegan contra todos |
| `"Swiss"` | Todos juegan la misma cantidad de rondas |

**Límites de rondas:**

| Formato | Mín. jugadores | Máx. rondas |
|---|---|---|
| Eliminación Sencilla | 2 | 7 |
| Eliminación Doble | 4 | 5 |
| Round Robin | 3 | 3 |
| Swiss | 4 | 7 |

**Respuesta exitosa — 201:**

```json
{
  "id": 5,
  "nombre": "Copa Semestral 2026",
  "tipo_eliminacion": "Eliminación Sencilla",
  "rondas": 3,
  "estado": "Pendiente",
  "creador_id": 1
}
```

> Guarda el `id` del torneo.

---

#### 5. Ver detalle de un torneo

```
GET http://localhost:8000/tournaments/5
```

Cambia `5` por el ID del torneo. No lleva body.

---

#### 6. Inscribirse en un torneo

```
POST http://localhost:8000/tournaments/register
```

```json
{
  "torneo_id": 5
}
```

El servidor sabe quién eres por tu token. El creador del torneo no puede inscribirse en su propio torneo.

**Respuesta exitosa — 201:**

```json
{
  "id": 12,
  "torneo_id": 5,
  "jugador_id": 2,
  "estado": "Confirmado"
}
```

---

#### 7. Cancelar tu inscripción

```
DELETE http://localhost:8000/tournaments/5/inscripcion
```

Cambia `5` por el ID del torneo. Solo funciona si el torneo está en estado `"Pendiente"`. No lleva body. Devuelve **204** si fue exitoso.

> Si luego quieres volver a inscribirte en el mismo torneo puedes hacerlo — el sistema reutiliza tu inscripción anterior.

---

#### 8. Cancelar un torneo (solo el creador)

```
POST http://localhost:8000/tournaments/5/cancelar
```

Cambia `5` por el ID del torneo. Solo funciona si tú eres quien creó ese torneo y está en estado `"Pendiente"` o `"Listo para iniciar"`. No lleva body. Devuelve **204**.

> Al cancelar, el torneo se borra completamente junto con todas sus inscripciones y matches. El nombre queda libre para usarlo en un torneo nuevo.

---

### Módulo 3 — Bracket y Partidas

> Generar, iniciar y registrar resultados solo lo puede hacer el **creador del torneo**.

#### 9. Generar el bracket (solo el creador)

```
POST http://localhost:8000/tournaments/5/bracket
```

Cambia `5` por el ID del torneo. El torneo debe estar en `"Pendiente"` y tener suficientes jugadores inscritos. Cambia el estado a `"Listo para iniciar"`.

**Respuesta — 201:**

```json
{
  "torneo_id": 5,
  "estado_torneo": "Listo para iniciar",
  "matches": [
    {
      "id": 10,
      "ronda": 1,
      "posicion": 0,
      "bracket_tipo": "ganadores",
      "jugador1_id": 1,
      "jugador2_id": 3,
      "ganador_id": null,
      "estado": "Programado"
    },
    {
      "id": 11,
      "ronda": 1,
      "posicion": 1,
      "bracket_tipo": "ganadores",
      "jugador1_id": 2,
      "jugador2_id": 4,
      "ganador_id": null,
      "estado": "Programado"
    }
  ]
}
```

> Anota los `id` de los matches — los necesitas para registrar resultados.

---

#### 10. Iniciar el torneo (solo el creador)

```
POST http://localhost:8000/tournaments/5/iniciar
```

El torneo debe estar en `"Listo para iniciar"`. No lleva body. Cambia el estado a `"En curso"` y activa los matches de la primera ronda. Los BYEs se resuelven automáticamente.

---

#### 11. Ver todos los matches del torneo

```
GET http://localhost:8000/tournaments/5/bracket
```

Cambia `5` por el ID del torneo. No lleva body. Útil para ver los IDs de los matches y su estado actual.

---

#### 12. Registrar el resultado de un match (solo el creador)

```
POST http://localhost:8000/tournaments/5/matches/10/resultado
```

Cambia `5` por el ID del torneo y `10` por el ID del match.

```json
{
  "ganador_id": 1
}
```

`ganador_id` debe ser el `jugador_id` de uno de los dos participantes. Si pones un ID que no corresponde a ninguno de los dos, recibes error 400.

**Respuesta exitosa — 200:**

```json
{
  "match": {
    "id": 10,
    "ronda": 1,
    "posicion": 0,
    "bracket_tipo": "ganadores",
    "jugador1_id": 1,
    "jugador2_id": 3,
    "ganador_id": 1,
    "estado": "Finalizado"
  },
  "ganador_nuevo_elo": 1016,
  "perdedor_nuevo_elo": 984,
  "torneo_finalizado": false
}
```

Cuando `torneo_finalizado` sea `true`, el torneo se cerró automáticamente.

**Lo que ocurre automáticamente al registrar un resultado:**
- El match pasa a `"Finalizado"` y el ELO de ambos jugadores se actualiza
- **Eliminación Sencilla:** el ganador avanza al siguiente match automáticamente
- **Eliminación Doble:** el ganador sube en el bracket de ganadores, el perdedor baja al bracket de perdedores automáticamente
- **Swiss:** al terminar todos los matches de una ronda, la siguiente ronda se genera sola
- Cuando no hay más matches, el torneo pasa a `"Finalizado"` solo

---

#### 13. Ver el ranking del torneo

```
GET http://localhost:8000/tournaments/5/ranking
```

Disponible en cualquier estado del torneo (no solo al finalizar). Cambia `5` por el ID del torneo.

**Respuesta:**

```json
{
  "torneo_id": 5,
  "tipo_eliminacion": "Swiss",
  "estado": "Finalizado",
  "ranking": [
    { "posicion": 1, "jugador_id": 1, "victorias": 4, "elo_global": 1048 },
    { "posicion": 2, "jugador_id": 3, "victorias": 3, "elo_global": 1024 },
    { "posicion": 3, "jugador_id": 2, "victorias": 1, "elo_global": 976 },
    { "posicion": 4, "jugador_id": 4, "victorias": 0, "elo_global": 952 }
  ]
}
```

---

#### 14. Ver el historial de partidas de un jugador

```
GET http://localhost:8000/tournaments/5/jugadores/1/historial
```

Cambia `5` por el ID del torneo y `1` por el ID del jugador. No lleva body. Disponible en cualquier estado del torneo.

---

### Flujo completo de ejemplo (4 jugadores)

```
Paso 1 — Registrar los 4 jugadores (repetir 4 veces con datos distintos)
         POST /usuarios/registrar
         body: { "nombre_usuario": "...", "correo_electronico": "...", "contrasena": "..." }

Paso 2 — Login de cada jugador (repetir 4 veces)
         POST /usuarios/login
         body: { "identificador": "...", "contrasena": "..." }
         → guardar el access_token y el id de cada jugador

Paso 3 — Jugador 1 crea el torneo (con su token)
         POST /tournaments
         body: { "nombre": "Copa Arena", "tipo_eliminacion": "Swiss", "rondas": 3 }
         → guardar el id del torneo (ej: 5)

Paso 4 — Jugadores 2, 3 y 4 se inscriben (cada uno con su propio token)
         POST /tournaments/register
         body: { "torneo_id": 5 }

Paso 5 — Jugador 1 genera el bracket (con su token)
         POST /tournaments/5/bracket

Paso 6 — Jugador 1 inicia el torneo (con su token)
         POST /tournaments/5/iniciar

Paso 7 — Ver los matches y anotar sus IDs
         GET /tournaments/5/bracket

Paso 8 — Registrar resultados (jugador 1 con su token, para cada match)
         POST /tournaments/5/matches/10/resultado
         body: { "ganador_id": 1 }
         (repetir para cada match hasta que torneo_finalizado sea true)

Paso 9 — Ver el ranking final
         GET /tournaments/5/ranking

Paso 10 — Ver historial de cualquier jugador
          GET /tournaments/5/jugadores/1/historial
```

---

### Errores comunes

| Código | Qué significa | Causa más probable |
|---|---|---|
| `401` | No autenticado | Falta el header `Authorization` o el token es incorrecto |
| `403` | Sin permiso | Intentas hacer algo que solo puede hacer el creador del torneo |
| `404` | No existe | El `torneo_id`, `match_id` o `jugador_id` no existe |
| `400` | Datos incorrectos | Jugador ya inscrito, torneo en estado incorrecto, ganador no es participante del match, rondas fuera de límite |
| `409` | Ya existe | Nombre de usuario o correo ya registrado |
| `422` | Validación fallida | Falta un campo, contraseña sin símbolo/número/letra, nombre de usuario con caracteres inválidos |

---

### Tipos de eliminación

#### Eliminación Sencilla
Una derrota = eliminado. El bracket se arma en potencia de 2 (2, 4, 8, 16...). Si hay 6 jugadores, el bracket es de 8 → 2 BYEs. Los mejores por ELO reciben los BYEs.

#### Eliminación Doble
Necesitas perder dos veces para quedar eliminado. Hay dos brackets paralelos: ganadores (WB) y perdedores (LB). Al perder en WB bajas al LB. Al perder en LB quedas eliminado. El último del WB y el último del LB se enfrentan en la Gran Final. También usa potencia de 2 y BYEs igual que la sencilla.

#### Round Robin
Todos juegan contra todos. Con n jugadores hay `n*(n-1)/2` partidas, todas generadas desde el inicio. Gana quien más victorias acumule; empate desempata por ELO. Sin BYEs.

#### Swiss
Todos juegan el mismo número de rondas (configurable). Ronda 1: emparejados por ELO. Rondas siguientes: emparejados por victorias acumuladas, evitando repetir rivales. Las rondas se generan una a una al terminar la anterior. Si hay número impar de jugadores hay BYE.

#### BYE — cómo actúa
Un BYE es un match donde `jugador2 = null`. Ocurre cuando el número de jugadores no es potencia de 2 (Sencilla/Doble) o cuando hay número impar (Swiss).
- El sistema lo cierra automáticamente: `ganador = jugador1`, `estado = "Finalizado"`
- El ganador avanza al siguiente match sin jugar
- No hay cambio de ELO — solo una victoria automática en el registro

---

### Sistema ELO

El ELO usa el algoritmo estándar con factor K adaptativo:

| ELO actual | Factor K |
|---|---|
| < 1000 | 40 (aprende más rápido) |
| 1000 – 2000 | 32 (estándar) |
| > 2000 | 16 (cambia poco) |

```
E_ganador = 1 / (1 + 10 ^ ((ELO_perdedor - ELO_ganador) / 400))
nuevo_ELO_ganador  = ELO_ganador  + K * (1 - E_ganador)
nuevo_ELO_perdedor = ELO_perdedor + K * (0 - E_ganador)
```

Los BYEs no calculan ELO.

---

### Otros endpoints

#### Ver datos de un jugador

```
GET http://localhost:8000/jugadores/1
```

Cambia `1` por el ID del jugador. No requiere token. Devuelve los datos públicos del jugador.

---

#### Actualizar contraseña de administrador

```
POST http://localhost:8000/admins/password
```

```json
{
  "admin_id": 1,
  "password": "NuevaClave123!",
  "password_confirm": "NuevaClave123!"
}
```

#### Ver alertas de matches vencidos

```
GET http://localhost:8000/alerts
```

#### Reconocer una alerta

```
PATCH http://localhost:8000/alerts/3/ack
```

Cambia `3` por el ID de la alerta.

#### Health check

```
GET http://localhost:8000/health
```

Responde `{ "status": "ok" }` si el servidor está corriendo.
