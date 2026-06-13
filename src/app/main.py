from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.tournaments import router as tournaments_router
from app.controllers.admin_controller import router as admin_router
from app.controllers.alert_controller import router as alert_router
from app.controllers.health_controller import router as health_router
from app.controllers.player_controller import router as player_router
from app.core.database import SessionLocal
from app.domain.constants import SYSTEM_ADMIN_ID
from app.repositories.player_repository import PlayerRepository
from app.tasks.scheduler import start_scheduler


def _initialize_system_actor_for_audit_logs() -> None:
    db = SessionLocal()
    try:
        # Actor de sistema (Player): satisface audit_logs.usuario_id -> jugador.id (ADR-005, 5a).
        PlayerRepository(db).ensure_system_user(SYSTEM_ADMIN_ID)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_system_actor_for_audit_logs()
    start_scheduler()
    yield


app = FastAPI(title="ArenaSync Backend", lifespan=lifespan)

# El esquema lo gestiona Alembic (única fuente de verdad). Ejecutar `alembic upgrade head`.


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request, exc: RequestValidationError):
    details = [f"{error['loc'][-1]}: {error['msg']}" for error in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": {"error": "validation_error", "details": details}},
    )

app.include_router(admin_router)
app.include_router(tournaments_router)
app.include_router(alert_router)
app.include_router(health_router)
app.include_router(player_router)


@app.get("/")
def root():
    return {"message": "ArenaSync Backend"}
