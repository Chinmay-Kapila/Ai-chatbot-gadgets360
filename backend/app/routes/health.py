"""Health check endpoint."""

from fastapi import APIRouter

from app.config.settings import settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple liveness/readiness check."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )
