"""Health profile management service."""

from datetime import datetime
from fastapi import HTTPException, status

from app.database import get_database
from app.models.health_profile import HealthProfileCreate, HealthProfileResponse
from app.utils.helpers import calculate_bmi


async def create_or_update_health_profile(
    profile_data: HealthProfileCreate,
    user_id: str
) -> HealthProfileResponse:
    """Create or update the user's health profile.
    
    Args:
        profile_data: Health profile data from the request.
        user_id: The authenticated user's ID.
    
    Returns:
        HealthProfileResponse with the saved profile data.
    """
    db = get_database()
    
    # Calculate BMI if height and weight are provided
    bmi = None
    bmi_category = None
    if profile_data.height_cm and profile_data.weight_kg:
        bmi, bmi_category = calculate_bmi(profile_data.weight_kg, profile_data.height_cm)
    
    # Build the profile document
    profile_doc = {
        "user_id": user_id,
        **profile_data.model_dump(),
        "bmi": bmi,
        "bmi_category": bmi_category,
        "updated_at": datetime.utcnow()
    }
    
    # Upsert: create if not exists, update if exists
    await db.health_profiles.update_one(
        {"user_id": user_id},
        {"$set": profile_doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    
    return HealthProfileResponse(
        user_id=user_id,
        **profile_data.model_dump(),
        bmi=bmi,
        bmi_category=bmi_category,
        updated_at=profile_doc["updated_at"]
    )


async def get_health_profile(user_id: str) -> HealthProfileResponse:
    """Get the user's health profile.
    
    Args:
        user_id: The authenticated user's ID.
    
    Returns:
        HealthProfileResponse with the profile data.
        
    Raises:
        HTTPException: If profile not found.
    """
    db = get_database()
    
    profile = await db.health_profiles.find_one({"user_id": user_id})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found. Please create one first."
        )
    
    return HealthProfileResponse(
        user_id=profile["user_id"],
        blood_group=profile.get("blood_group"),
        height_cm=profile.get("height_cm"),
        weight_kg=profile.get("weight_kg"),
        medical_conditions=profile.get("medical_conditions", []),
        allergies=profile.get("allergies", []),
        current_medications=profile.get("current_medications", []),
        lifestyle_habits=profile.get("lifestyle_habits"),
        family_history=profile.get("family_history", []),
        emergency_contacts=profile.get("emergency_contacts", []),
        bmi=profile.get("bmi"),
        bmi_category=profile.get("bmi_category"),
        updated_at=profile.get("updated_at", datetime.utcnow())
    )


async def get_health_summary(user_id: str) -> dict:
    """Get a health summary with insights.
    
    Returns a summary of the user's health profile with BMI analysis
    and general health insights.
    """
    db = get_database()
    
    profile = await db.health_profiles.find_one({"user_id": user_id})
    user = await db.users.find_one({"_id": __import__("bson").ObjectId(user_id)})
    
    if not profile:
        return {
            "status": "incomplete",
            "message": "Please create your health profile to get personalized insights.",
            "completion_percentage": 0
        }
    
    # Calculate profile completion percentage
    fields = ["blood_group", "height_cm", "weight_kg", "medical_conditions", 
              "allergies", "current_medications", "lifestyle_habits", "emergency_contacts"]
    filled = sum(1 for f in fields if profile.get(f))
    completion = round((filled / len(fields)) * 100)
    
    # Build insights
    insights = []
    if profile.get("bmi"):
        bmi = profile["bmi"]
        category = profile.get("bmi_category", "Unknown")
        insights.append(f"Your BMI is {bmi} ({category}).")
        
        if category == "Underweight":
            insights.append("Consider consulting a nutritionist for a balanced diet plan.")
        elif category == "Overweight":
            insights.append("Regular exercise and a balanced diet can help manage weight.")
        elif category == "Obese":
            insights.append("Please consult a healthcare provider for personalized weight management.")
    
    if profile.get("medical_conditions"):
        insights.append(f"Active conditions being tracked: {', '.join(profile['medical_conditions'])}.")
    
    if not profile.get("emergency_contacts"):
        insights.append("⚠️ No emergency contacts added. Consider adding at least one.")
    
    return {
        "status": "complete" if completion == 100 else "partial",
        "completion_percentage": completion,
        "user_name": user.get("name", "User") if user else "User",
        "bmi": profile.get("bmi"),
        "bmi_category": profile.get("bmi_category"),
        "conditions_count": len(profile.get("medical_conditions", [])),
        "medications_count": len(profile.get("current_medications", [])),
        "allergies_count": len(profile.get("allergies", [])),
        "has_emergency_contacts": len(profile.get("emergency_contacts", [])) > 0,
        "insights": insights,
        "last_updated": profile.get("updated_at")
    }
