"""Preventive Health Engine API routes.

These endpoints are the UNIQUE DIFFERENTIATORS of this project:
1. /risk-profile — Multi-factor preventive risk analysis
2. /top-changes — Personalized highest-impact changes
3. /projection — Future health trajectory ("what if" comparison)
"""

from fastapi import APIRouter, Depends

from app.models.preventive import (
    PreventiveAnalysisRequest, PreventiveRiskResponse,
    ImpactPredictorResponse,
    ProjectionRequest, ProjectionResponse,
)
from app.services.preventive_service import (
    analyze_preventive_risk,
    predict_highest_impact,
    generate_projection,
)
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/preventive", tags=["Preventive Health Engine"])


@router.post("/risk-profile", response_model=PreventiveRiskResponse)
async def get_risk_profile(
    request: PreventiveAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze your lifestyle and health data to produce a preventive risk profile.
    
    This analyzes your age, BMI, sleep, diet, exercise, family history,
    blood pressure, glucose, and lifestyle patterns to generate risk scores
    across 5 categories:
    
    - Metabolic Risk
    - Cardiovascular Risk
    - Sleep-Related Risk
    - Physical Inactivity Risk
    - Nutrition-Related Risk
    
    Each category includes a score (0-100), risk level, contributing factors,
    and preventive screening recommendations.
    
    **This is NOT a diagnosis** — it identifies modifiable risk factors for prevention.
    """
    return await analyze_preventive_risk(request, current_user)


@router.post("/top-changes", response_model=ImpactPredictorResponse)
async def get_top_changes(
    request: PreventiveAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get the TOP 3 lifestyle changes that would produce the biggest 
    health improvement for YOU specifically.
    
    Instead of generic advice like "eat healthy, exercise, sleep well",
    this endpoint analyzes YOUR specific risk profile and identifies:
    
    - Which 3 changes matter MOST for your situation
    - Your current value vs. recommended target
    - Expected impact level (high, medium-high, medium)
    - Which risk categories each change improves
    - Estimated risk score reduction
    
    **Example response:**
    1. Increase sleep by 60 min (Impact: HIGH)
    2. Add 3,000 daily steps (Impact: MEDIUM-HIGH)
    3. Reduce sugary drinks (Impact: MEDIUM)
    """
    return await predict_highest_impact(request, current_user)


@router.post("/projection", response_model=ProjectionResponse)
async def get_projection(
    request: ProjectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a future health trajectory projection.
    
    Shows TWO projected paths over the next 24 months:
    
    **Path A — Current Lifestyle (no changes):**
    What happens to your risk scores if you continue as-is.
    Risk scores gradually increase due to compounding effects.
    
    **Path B — With Recommended Changes:**
    What happens if you adopt the recommended lifestyle improvements.
    Shows gradual risk reduction over 3, 6, 12, and 24 months.
    
    This visually demonstrates: "What happens if I continue vs. if I change?"
    
    Data points are provided at: Now, 3 months, 6 months, 12 months, 24 months.
    Use these data points to render trajectory charts on the frontend.
    """
    return await generate_projection(request, current_user)
