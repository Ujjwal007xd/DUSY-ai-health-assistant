"""Health profile API routes."""

from fastapi import APIRouter, Depends

from app.models.health_profile import HealthProfileCreate, HealthProfileResponse
from app.services.health_service import (
    create_or_update_health_profile,
    get_health_profile,
    get_health_summary
)
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/health", tags=["Health Profile"])


@router.post("/profile", response_model=HealthProfileResponse, status_code=201)
async def create_profile(
    profile_data: HealthProfileCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update the user's health profile.
    
    If a profile already exists, it will be updated with the new data.
    BMI is automatically calculated if height and weight are provided.
    """
    user_id = current_user["_id"]
    return await create_or_update_health_profile(profile_data, user_id)


@router.get("/profile", response_model=HealthProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get the current user's health profile."""
    user_id = current_user["_id"]
    return await get_health_profile(user_id)


@router.put("/profile", response_model=HealthProfileResponse)
async def update_profile(
    profile_data: HealthProfileCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update the user's health profile."""
    user_id = current_user["_id"]
    return await create_or_update_health_profile(profile_data, user_id)


@router.get("/summary")
async def health_summary(current_user: dict = Depends(get_current_user)):
    """Get a health summary with insights and profile completion status.
    
    Returns BMI analysis, condition tracking info, and personalized insights.
    """
    user_id = current_user["_id"]
    return await get_health_summary(user_id)
