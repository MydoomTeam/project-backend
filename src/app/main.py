from fastapi import FastAPI

from app.api.tournaments import router as tournaments_router
from app.core.database import Base, engine
from app.controllers.health_controller import router as health_router
from app.controllers.jugador_controller import router as jugador_router
from app.models import audit_log, registration, tournament

app = FastAPI(title="ArenaSync Backend")

Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(jugador_router, prefix="/api")
app.include_router(tournaments_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "ArenaSync Backend"}
