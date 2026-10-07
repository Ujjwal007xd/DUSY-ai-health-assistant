"""General utility functions for the Health Assistant."""

from datetime import datetime
from bson import ObjectId


def calculate_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    """Calculate BMI and return the value with its category.
    
    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.
    
    Returns:
        Tuple of (bmi_value, bmi_category)
    """
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0, "Invalid"
    
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    
    if bmi < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi < 25:
        category = "Normal weight"
    elif 25 <= bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    
    return bmi, category


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict.
    
    Converts ObjectId to string and handles datetime fields.
    """
    if doc is None:
        return None
    
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [
                serialize_doc(item) if isinstance(item, dict) else
                str(item) if isinstance(item, ObjectId) else item
                for item in value
            ]
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        else:
            result[key] = value
    return result


def generate_conversation_title(first_message: str) -> str:
    """Generate a short title from the first message of a conversation."""
    # Take first 50 chars and clean up
    title = first_message.strip()[:50]
    if len(first_message) > 50:
        title += "..."
    return title
