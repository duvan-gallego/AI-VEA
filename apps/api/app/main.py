from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.engagement_analyses import router as engagement_analyses_router
from app.api.health import router as health_router
from app.config import Settings, get_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    def get_settings_override() -> Settings:
        return resolved_settings

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.dependency_overrides[get_settings] = get_settings_override

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(engagement_analyses_router, prefix="/api")

    return app


app = create_app()
