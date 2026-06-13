@echo off
setlocal

rem Block: run from repo root
cd /d %~dp0

rem Block: start database container
rem Requires Docker Desktop

docker compose up -d

rem Block: create and activate virtual environment
py -3.14 -m venv .venv
call .venv\Scripts\activate.bat

rem Block: install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

rem Block: environment file (optional)
if not exist .env copy .env.example .env

rem Block: wait for PostgreSQL to be ready, then apply DB migrations
rem Alembic crea/actualiza el esquema (create_all esta congelado).
timeout /t 10 /nobreak
alembic upgrade head

rem Block: basic check (testing placeholder)
python -m pip --version

rem Block: run the API (manual step)
rem uvicorn app.main:app --reload --app-dir src

endlocal
