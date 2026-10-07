"""Symptom analysis data models."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SymptomInput(BaseModel):
    """User's symptom input for analysis."""
    symptoms: list[str] = Field(..., min_length=1, description="List of symptoms")
    duration: Optional[str] = Field(None, description="How long symptoms have been present (e.g., '3 days')")
    severity: Optional[str] = Field(None, description="Severity: mild, moderate, severe")
    additional_notes: Optional[str] = Field(None, description="Any additional context")


class PossibleCondition(BaseModel):
    """A possible condition identified from symptoms."""
    condition: str
    likelihood: str = Field(..., description="high, moderate, or low")
    description: str


class SymptomAnalysisResponse(BaseModel):
    """Result of symptom analysis."""
    analysis_id: str
    urgency_level: str = Field(..., description="low, moderate, high, or emergency")
    possible_conditions: list[PossibleCondition]
    recommendations: list[str]
    when_to_see_doctor: str
    disclaimer: str = "This is an AI-based preliminary assessment, NOT a medical diagnosis. Always consult a qualified healthcare professional."
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
