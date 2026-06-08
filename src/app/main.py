from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.controllers.admin_controller import router as admin_router
from app.controllers.torneo_controller import router as torneo_router
from app.controllers.alerta_controller import router as alerta_router
from app.tasks.scheduler import start_scheduler
from app.core.database import SessionLocal
from app.repositories.admin_repository import AdminRepository
from app.domain.constants import SYSTEM_ADMIN_ID


def _initialize_system_admin_for_audit_logs() -> None:
    db = SessionLocal()
    try:
        admin_repo = AdminRepository(db)
        admin_repo.ensure_system_admin(SYSTEM_ADMIN_ID)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_system_admin_for_audit_logs()
    start_scheduler()
    yield


app = FastAPI(title="ArenaSync Backend", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request, exc: RequestValidationError):
    details = [f"{error['loc'][-1]}: {error['msg']}" for error in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={"detail": {"error": "validation_error", "details": details}},
    )

app.include_router(admin_router, prefix="/api")
app.include_router(torneo_router, prefix="/api")
app.include_router(alerta_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "ArenaSync Backend"}
