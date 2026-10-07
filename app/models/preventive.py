"""Preventive health data models."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class LifestyleInput(BaseModel):
    """User's current lifestyle data for preventive analysis."""
    sleep_hours: float = Field(..., ge=0, le=24, description="Average daily sleep in hours")
    exercise_minutes_per_day: float = Field(0, ge=0, description="Average daily exercise in minutes")
    daily_steps: int = Field(0, ge=0, description="Average daily step count")
    water_intake_liters: float = Field(0, ge=0, description="Daily water intake in liters")
    diet_type: Optional[str] = Field(None, description="Diet type: balanced, high-carb, high-protein, vegetarian, vegan, junk-heavy")
    sugary_drinks_per_week: int = Field(0, ge=0, description="Number of sugary drinks per week")
    smoking: bool = Field(False, description="Current smoker")
    alcohol_drinks_per_week: int = Field(0, ge=0, description="Alcoholic drinks per week")
    stress_level: Optional[str] = Field(None, description="Self-reported: low, moderate, high, very-high")
    screen_time_hours: float = Field(0, ge=0, description="Average daily screen time in hours")


class VitalsInput(BaseModel):
    """User's health vitals for risk analysis."""
    systolic_bp: Optional[int] = Field(None, ge=60, le=250, description="Systolic blood pressure (mmHg)")
    diastolic_bp: Optional[int] = Field(None, ge=40, le=150, description="Diastolic blood pressure (mmHg)")
    fasting_glucose: Optional[float] = Field(None, ge=30, le=500, description="Fasting blood glucose (mg/dL)")
    resting_heart_rate: Optional[int] = Field(None, ge=30, le=200, description="Resting heart rate (bpm)")
    cholesterol_total: Optional[float] = Field(None, description="Total cholesterol (mg/dL)")
    cholesterol_hdl: Optional[float] = Field(None, description="HDL cholesterol (mg/dL)")
    cholesterol_ldl: Optional[float] = Field(None, description="LDL cholesterol (mg/dL)")


class PreventiveAnalysisRequest(BaseModel):
    """Full request for preventive health analysis."""
    lifestyle: LifestyleInput
    vitals: Optional[VitalsInput] = None


class RiskCategory(BaseModel):
    """A single risk category assessment."""
    category: str = Field(..., description="Risk category name")
    risk_level: str = Field(..., description="low, moderate, high, very-high")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score 0-100")
    contributing_factors: list[str] = Field(default_factory=list, description="Factors contributing to this risk")
    explanation: str = Field("", description="Brief explanation of the risk")


class PreventiveRiskResponse(BaseModel):
    """Full preventive risk profile response."""
    overall_risk_level: str = Field(..., description="Overall risk: low, moderate, high")
    overall_risk_score: int = Field(..., ge=0, le=100)
    risk_categories: list[RiskCategory]
    screening_recommendations: list[str] = Field(default_factory=list, description="Recommended health screenings to discuss with a doctor")
    summary: str = Field(..., description="Human-readable risk summary")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = "This is an AI-generated preventive risk assessment, NOT a medical diagnosis. Consult a healthcare professional for medical decisions."


class ImpactChange(BaseModel):
    """A single high-impact recommended change."""
    rank: int = Field(..., ge=1, le=5, description="Priority rank")
    change: str = Field(..., description="What to change")
    current_value: str = Field(..., description="Current behavior/value")
    target_value: str = Field(..., description="Recommended target")
    impact_level: str = Field(..., description="high, medium-high, medium")
    affected_risks: list[str] = Field(default_factory=list, description="Which risk categories this improves")
    expected_risk_reduction: str = Field("", description="Estimated risk reduction")
    explanation: str = Field("", description="Why this change matters for YOU")


class ImpactPredictorResponse(BaseModel):
    """Response with top 3 highest-impact changes."""
    top_changes: list[ImpactChange]
    personalization_note: str = Field("", description="Why these specific changes were selected for this user")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = "Recommendations are AI-generated based on your health profile. Consult a healthcare professional before making significant lifestyle changes."


class ProjectionPoint(BaseModel):
    """A single data point in a health trajectory."""
    month: int = Field(..., description="Months from now (0, 3, 6, 12, 24)")
    overall_risk_score: int = Field(..., ge=0, le=100)
    metabolic_risk: int = Field(..., ge=0, le=100)
    cardiovascular_risk: int = Field(..., ge=0, le=100)
    sleep_risk: int = Field(..., ge=0, le=100)
    activity_risk: int = Field(..., ge=0, le=100)


class ProjectionRequest(BaseModel):
    """Request for future health projection."""
    lifestyle: LifestyleInput
    vitals: Optional[VitalsInput] = None
    planned_changes: Optional[list[str]] = Field(None, description="List of planned lifestyle changes for improved trajectory")


class ProjectionResponse(BaseModel):
    """Future health trajectory projection."""
    current_trajectory: list[ProjectionPoint] = Field(..., description="Projected risk if no changes are made")
    improved_trajectory: Optional[list[ProjectionPoint]] = Field(None, description="Projected risk if recommended changes are adopted")
    changes_applied: list[str] = Field(default_factory=list, description="Changes used in the improved trajectory")
    key_insight: str = Field("", description="Most important takeaway")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = "Projections are AI-estimated trends, not medical predictions. Individual outcomes may vary. Consult a healthcare professional."
