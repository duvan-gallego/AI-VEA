from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    environment: str
    service: str
    status: Literal["ok"]
    version: str


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        environment=settings.app_env,
        service=settings.app_name,
        status="ok",
        version=settings.app_version,
    )
