"""
Health check routes.
"""
from fastapi import APIRouter

from api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    """
    return HealthResponse(
        status="healthy",
        service="itinerary-generator-api",
    )


@router.get("/api/v1/health", response_model=HealthResponse)
async def health_check_v1():
    """
    Health check endpoint (versioned).
    """
    return HealthResponse(
        status="healthy",
        service="itinerary-generator-api",
    )
