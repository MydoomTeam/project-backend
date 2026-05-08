#!/usr/bin/env bash
set -e

# Block: run from repo root
cd "$(dirname "$0")"

# Block: start database container
# Requires Docker Desktop / Docker Engine

docker compose up -d

# Block: create and activate virtual environment
python3.14 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Block: install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Block: environment file (optional)
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

# Block: basic check (testing placeholder)
python -m pip --version

# Block: run the API (manual step)
# uvicorn app.main:app --reload --app-dir src
