"""Health profile data models."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EmergencyContact(BaseModel):
    """Emergency contact details."""
    name: str
    relationship: str
    phone: str


class HealthProfileCreate(BaseModel):
    """Schema for creating/updating a health profile."""
    blood_group: Optional[str] = Field(None, description="Blood group (A+, B-, O+, etc.)")
    height_cm: Optional[float] = Field(None, description="Height in centimeters")
    weight_kg: Optional[float] = Field(None, description="Weight in kilograms")
    medical_conditions: list[str] = Field(default_factory=list, description="Existing medical conditions")
    allergies: list[str] = Field(default_factory=list, description="Known allergies")
    current_medications: list[str] = Field(default_factory=list, description="Medications currently taking")
    lifestyle_habits: Optional[dict] = Field(None, description="Lifestyle info (smoking, exercise, diet type, etc.)")
    family_history: list[str] = Field(default_factory=list, description="Family medical history")
    emergency_contacts: list[EmergencyContact] = Field(default_factory=list, description="Emergency contacts")


class HealthProfileResponse(HealthProfileCreate):
    """Health profile response with computed fields."""
    user_id: str
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    updated_at: datetime
