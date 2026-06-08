# ArenaSync Backend

Backend monolitico con FastAPI + SQLAlchemy y PostgreSQL 16 en Docker. Implementa los casos de uso de administración de contraseñas, creación de torneos y alertas de eventos.

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
- Actualizar contraseña de administrador: `POST /api/admins/password`
- Crear torneo: `POST /api/tournaments`
- Obtener torneo: `GET /api/tournaments/{id}`
- Listar alertas: `GET /api/alerts`
- Reconocer alerta: `PATCH /api/alerts/{id}/ack`

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

POST `http://localhost:8000/api/admins/password`

```json
{
  "password": "Password123",
  "password_confirm": "Password123"
}
```

POST `http://localhost:8000/api/tournaments`

```json
{
  "nombre": "Torneo Ejemplo",
  "tipo_eliminacion": "simple",
  "duracion_ronda_min": 30,
  "participantes_max": 8
}
```

GET `http://localhost:8000/api/tournaments/{id}`

GET `http://localhost:8000/api/alerts`