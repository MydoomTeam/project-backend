# Tutorial: Hola Mundo Backend con FastAPI + PostgreSQL

Este tutorial muestra como construir un backend minimo desde cero usando FastAPI, SQLAlchemy y PostgreSQL en Docker. El objetivo es validar conexion a BD, crear una entidad y probarla con Postman.

## Stack seleccionado

- Lenguaje: Python 3.12+ (probado en 3.14.3)
- Framework: FastAPI 0.115
- ORM: SQLAlchemy 2.0
- Base de datos: PostgreSQL 16 (Docker)
- Driver BD: psycopg2-binary
- Entorno: virtualenv + Docker Compose

## Archivos clave del proyecto

- `docker-compose.yml`: levanta PostgreSQL y carga el SQL automaticamente.
- `arenasyncdbv2.sql`: esquema de la base de datos.
- `.env.example`: ejemplo de conexion a la BD.
- `requirements.txt`: dependencias del backend.
- `src/app`: codigo de la aplicacion por capas.

## Contenido de archivos .yml

### docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    container_name: arenasync-postgres
    environment:
      POSTGRES_USER: arenasync
      POSTGRES_PASSWORD: arenasync
      POSTGRES_DB: arenasyncdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./arenasyncdbv2.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U arenasync -d arenasyncdb"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

> Nota: el SQL se ejecuta solo la primera vez, cuando el volumen esta vacio.

## Flujo sin automatizacion (paso a paso)

1) Abrir la carpeta del proyecto
- Abrir VS Code y seleccionar `project-backend`.

2) Crear el entorno virtual

Windows (PowerShell):
```
py -3.14 -m venv .venv
```

Linux/macOS:
```
python3.14 -m venv .venv
```

3) Activar el entorno

Windows (PowerShell):
```
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:
```
source .venv/bin/activate
```

4) Instalar dependencias

```
python -m pip install -r requirements.txt
```

5) Crear el archivo .env

Windows:
```
copy .env.example .env
```

Linux/macOS:
```
cp .env.example .env
```

6) Levantar la base de datos

```
docker compose up -d
```

7) Ejecutar FastAPI

```
uvicorn app.main:app --reload --app-dir src
```

8) Verificar en navegador
- `http://localhost:8000/docs`

## Flujo con automatizacion

Windows:
```
setup.bat
```

Linux/macOS:
```
./setup.sh
```

Esto levanta la BD, crea el entorno virtual, instala dependencias y crea `.env` si no existe.

Luego se ejecuta FastAPI manualmente:

```
uvicorn app.main:app --reload --app-dir src
```

## Hola Mundo con BD (solo backend)

### 1) Conexion a la BD
El endpoint `GET /hola` valida la conexion usando el ORM (SQLAlchemy), consultando la entidad `Jugador`.

### 2) Entidad minima
Se usa la entidad `Jugador` con tabla `JUGADOR` (del SQL). Ejemplo de la clase:

```python
class Jugador(Base):
    __tablename__ = "jugador"

    id = Column(Integer, primary_key=True, autoincrement=False)
    nombre_usuario = Column(Text, nullable=False)
    correo_electronico = Column(Text, nullable=False)
    contrasena_hash = Column(Text, nullable=False)
    rol = Column(Text, nullable=False)
    fecha_ultimo_acceso = Column(Date, nullable=False)
    elo_global = Column(Integer, nullable=False)
```

Cuando haces el POST, se instancia esta clase y se guarda en la BD desde el servicio:

```python
jugador = Jugador(
    id=data.id,
    nombre_usuario=data.nombre_usuario,
    correo_electronico=data.correo_electronico,
    contrasena_hash=data.contrasena_hash,
    rol=data.rol,
    fecha_ultimo_acceso=data.fecha_ultimo_acceso,
    elo_global=data.elo_global,
)
```

### 3) Prueba desde Postman (o Thunder Client)

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

Luego consultar:

GET `http://localhost:8000/api/jugadores/1`

Si el GET devuelve 404, primero crea el jugador con POST.

## Problemas comunes

- Error de conexion a BD: revisar que `DATABASE_URL` en `.env` coincida con `docker-compose.yml`.
- SQL no se ejecuta: borrar el volumen y levantar de nuevo:
```
docker compose down -v
```