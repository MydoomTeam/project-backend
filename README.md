# ArenaSync Backend (Hola Mundo)

Backend monolitico con FastAPI + SQLAlchemy y PostgreSQL 16 en Docker. Incluye un flujo minimo para validar conexion a BD y crear una entidad.

## Stack

- Python 3.12+ (probado en 3.14.3)
- FastAPI 0.115
- SQLAlchemy 2.0
- PostgreSQL 16 (Docker)
- Driver: psycopg2-binary

## Estructura

```
project-backend/
├── .env.example
├── arenasyncdbv2.sql
├── docker-compose.yml
├── requirements.txt
├── setup.bat
├── setup.sh
└── src/
    └── app/
        ├── controllers/
        ├── core/
        ├── domain/
        ├── repositories/
        └── services/
```

## Configuracion de entorno

Crear un archivo `.env` desde el ejemplo:

```
DATABASE_URL=postgresql+psycopg2://arenasync:arenasync@localhost:5432/arenasyncdb
```

> Nota: Los valores de `docker-compose.yml` (usuario, password, db) deben coincidir con `DATABASE_URL`.

## Flujo sin automatizacion (paso a paso)

1) Crear y activar entorno virtual

Windows (PowerShell):
```
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:
```
python3.14 -m venv .venv
source .venv/bin/activate
```

2) Instalar dependencias

```
python -m pip install -r requirements.txt
```

3) Crear `.env`

Windows:
```
copy .env.example .env
```

Linux/macOS:
```
cp .env.example .env
```

4) Levantar la base de datos

```
docker compose up -d
```

> El SQL `arenasyncdbv2.sql` se ejecuta automaticamente la primera vez. Si quieres reejecutarlo, elimina el volumen: `docker compose down -v`.

5) Ejecutar FastAPI

```
uvicorn app.main:app --reload --app-dir src
```

6) Probar endpoints

- Docs: `http://localhost:8000/docs`
- Hola Mundo (conexion BD): `GET /hola`
- Crear jugador: `POST /api/jugadores`
- Consultar jugador: `GET /api/jugadores/{id}`

## Flujo con automatizacion

Windows:
```
setup.bat
```

Linux/macOS:
```
./setup.sh
```

Estos scripts:
- Levantan la BD en Docker.
- Crean y activan el entorno virtual.
- Instalan dependencias.
- Crean `.env` desde `.env.example` si no existe.

Luego ejecuta FastAPI manualmente:

```
uvicorn app.main:app --reload --app-dir src
```

## Prueba rapida (Postman o Thunder Client)

POST `http://localhost:8000/api/jugadores`

```json
{
  "id": 1,
  "nombre_usuario": "demo",
  "correo_electronico": "demo@demo.com",
  "contrasena_hash": "hash",
  "rol": "JUGADOR",
  "fecha_ultimo_acceso": "2026-05-07",
  "elo_global": 1200
}
```

Luego:

GET `http://localhost:8000/api/jugadores/1`