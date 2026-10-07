"""Symptom analysis service using Gemini AI."""

import json
from datetime import datetime
from bson import ObjectId

from google import genai
from google.genai import types
from fastapi import HTTPException, status

from app.config import get_settings
from app.database import get_database
from app.models.symptom import SymptomInput, SymptomAnalysisResponse, PossibleCondition


# Load health knowledge base
import os
KNOWLEDGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge", "health_data.json")

def _load_health_knowledge() -> dict:
    """Load the medical knowledge base for context."""
    try:
        with open(KNOWLEDGE_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


SYMPTOM_ANALYSIS_PROMPT = """You are a medical symptom analysis AI. Analyze the given symptoms and provide a structured assessment.

IMPORTANT: You are NOT diagnosing. You are providing a preliminary AI-based assessment to help users understand 
their symptoms better and decide on appropriate next steps.

Based on the symptoms provided, respond ONLY with a valid JSON object in this exact format (no markdown, no extra text):
{{
    "urgency_level": "low|moderate|high|emergency",
    "possible_conditions": [
        {{
            "condition": "Condition name",
            "likelihood": "high|moderate|low",
            "description": "Brief description of the condition"
        }}
    ],
    "recommendations": ["Recommendation 1", "Recommendation 2"],
    "when_to_see_doctor": "Clear guidance on when to seek medical attention"
}}

Consider the user's health profile when available for more personalized analysis.
Always err on the side of caution — if in doubt, recommend seeing a doctor.
Limit possible conditions to the top 3 most likely.
"""


async def analyze_symptoms(symptom_data: SymptomInput, user: dict) -> SymptomAnalysisResponse:
    """Analyze user-reported symptoms using Gemini AI.
    
    Args:
        symptom_data: The user's reported symptoms, duration, and severity.
        user: The authenticated user's document.
    
    Returns:
        SymptomAnalysisResponse with analysis results.
    """
    settings = get_settings()
    db = get_database()
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured."
        )
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    user_id = user["_id"] if isinstance(user["_id"], str) else str(user["_id"])
    
    # Get user's health profile for context
    health_profile = await db.health_profiles.find_one({"user_id": user_id})
    
    # Build the analysis prompt
    prompt = SYMPTOM_ANALYSIS_PROMPT + "\n\nSYMPTOMS REPORTED:\n"
    prompt += f"- Symptoms: {', '.join(symptom_data.symptoms)}\n"
    
    if symptom_data.duration:
        prompt += f"- Duration: {symptom_data.duration}\n"
    if symptom_data.severity:
        prompt += f"- Severity: {symptom_data.severity}\n"
    if symptom_data.additional_notes:
        prompt += f"- Additional notes: {symptom_data.additional_notes}\n"
    
    # Add health profile context
    if health_profile:
        prompt += "\nUSER HEALTH PROFILE:\n"
        if health_profile.get("medical_conditions"):
            prompt += f"- Existing conditions: {', '.join(health_profile['medical_conditions'])}\n"
        if health_profile.get("allergies"):
            prompt += f"- Allergies: {', '.join(health_profile['allergies'])}\n"
        if health_profile.get("current_medications"):
            prompt += f"- Current medications: {', '.join(health_profile['current_medications'])}\n"
    
    # Add knowledge base context
    knowledge = _load_health_knowledge()
    if knowledge.get("emergency_signs"):
        prompt += f"\nKNOWN EMERGENCY SIGNS: {json.dumps(knowledge['emergency_signs'])}\n"
    
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        response_text = response.text.strip()
        
        # Clean up response — remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]  # Remove first line
            response_text = response_text.rsplit("```", 1)[0]  # Remove last ```
        
        analysis = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback if AI doesn't return valid JSON
        analysis = {
            "urgency_level": "moderate",
            "possible_conditions": [{
                "condition": "Unable to determine",
                "likelihood": "moderate",
                "description": "The AI was unable to provide a structured analysis. Please consult a healthcare professional."
            }],
            "recommendations": ["Please consult a healthcare professional for proper evaluation."],
            "when_to_see_doctor": "Since we couldn't fully analyze your symptoms, please see a doctor soon."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Symptom analysis failed: {str(e)}"
        )
    
    # Store the analysis in the database
    analysis_doc = {
        "user_id": user_id,
        "symptoms": symptom_data.symptoms,
        "duration": symptom_data.duration,
        "severity": symptom_data.severity,
        "additional_notes": symptom_data.additional_notes,
        "result": analysis,
        "analyzed_at": datetime.utcnow()
    }
    result = await db.symptom_analyses.insert_one(analysis_doc)
    
    # Build response
    possible_conditions = [
        PossibleCondition(**condition)
        for condition in analysis.get("possible_conditions", [])
    ]
    
    return SymptomAnalysisResponse(
        analysis_id=str(result.inserted_id),
        urgency_level=analysis.get("urgency_level", "moderate"),
        possible_conditions=possible_conditions,
        recommendations=analysis.get("recommendations", []),
        when_to_see_doctor=analysis.get("when_to_see_doctor", "Please consult a doctor."),
        analyzed_at=analysis_doc["analyzed_at"]
    )


async def get_symptom_history(user_id: str) -> list[dict]:
    """Get past symptom analyses for a user."""
    db = get_database()
    
    cursor = db.symptom_analyses.find(
        {"user_id": user_id}
    ).sort("analyzed_at", -1).limit(20)
    
    history = []
    async for analysis in cursor:
        history.append({
            "analysis_id": str(analysis["_id"]),
            "symptoms": analysis["symptoms"],
            "urgency_level": analysis["result"].get("urgency_level", "unknown"),
            "analyzed_at": analysis["analyzed_at"]
        })
    
    return history
