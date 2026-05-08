from fastapi import FastAPI

from app.controllers.health_controller import router as health_router
from app.controllers.jugador_controller import router as jugador_router

app = FastAPI(title="ArenaSync Backend")

app.include_router(health_router)
app.include_router(jugador_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "ArenaSync Backend"}
