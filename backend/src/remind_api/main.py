from fastapi import FastAPI
from sqlalchemy import text

from remind_api import models  # noqa: F401 - register tables with SQLAlchemy metadata
from remind_api.db import engine
from remind_api.routes import router

app = FastAPI(
    title="ReMind API",
    summary="Phase 1 API for account setup and caregiver–patient linking",
    version="0.1.0",
)
app.include_router(router)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
