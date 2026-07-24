from fastapi import FastAPI

from app.core.config import settings
from app.database.session import engine
from app.routers.match_router import router as match_router
from app.routers.news_router import router as news_router
from app.routers.player_router import router as player_router
from app.routers.standing_router import router as standing_router
from app.routers.statistics_router import router as statistics_router
from app.routers.team_router import router as team_router
from app.routers.world_cup_router import router as world_cup_router


app = FastAPI(title=settings.APP_NAME)

app.include_router(team_router)
app.include_router(world_cup_router)
app.include_router(player_router)
app.include_router(match_router)
app.include_router(news_router)
app.include_router(standing_router)
app.include_router(statistics_router)


@app.get("/")
def root():
    return {
        "message": "World Cup Information API"
    }


@app.get("/health")
def health_check():
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")

    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
