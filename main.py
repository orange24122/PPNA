from fastapi import FastAPI

from app.config.logging_config import setup_logging
from app.config.settings import get_settings
from app.routers import auth, detection

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(detection.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {"message": settings.app_name}

