"""Symptom analysis API routes."""

from fastapi import APIRouter, Depends

from app.models.symptom import SymptomInput, SymptomAnalysisResponse
from app.services.symptom_service import analyze_symptoms, get_symptom_history
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/symptoms", tags=["Symptom Analysis"])


@router.post("/analyze", response_model=SymptomAnalysisResponse)
async def analyze(
    symptom_data: SymptomInput,
    current_user: dict = Depends(get_current_user)
):
    """Analyze reported symptoms using AI.
    
    Provide a list of symptoms along with optional duration and severity.
    The AI will provide a preliminary assessment with possible conditions,
    urgency level, and recommendations.
    
    ⚠️ This is NOT a medical diagnosis. Always consult a healthcare professional.
    """
    return await analyze_symptoms(symptom_data, current_user)


@router.get("/history")
async def symptom_history(current_user: dict = Depends(get_current_user)):
    """Get past symptom analysis results."""
    user_id = current_user["_id"]
    return await get_symptom_history(user_id)
