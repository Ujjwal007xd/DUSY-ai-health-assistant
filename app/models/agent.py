"""Pydantic data models for the AI Health Agent."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any


class AgentActionItem(BaseModel):
    """An interactive action offered by the AI Agent."""
    action_type: str = Field(..., description="Type: 'health_log', 'create_goal', 'screening_alert', 'lifestyle_tweak'")
    title: str = Field(..., description="Short title of the action")
    description: str = Field("", description="Details about the action")
    payload: dict = Field(default_factory=dict, description="Action payload data")


class AgentInteractRequest(BaseModel):
    """Request payload for communicating with the AI Health Agent."""
    message: str = Field(..., min_length=1, max_length=3000, description="User query or answer")
    task_type: Optional[str] = Field("symptom_assessment", description="Task: 'symptom_assessment', 'health_assessment', 'lifestyle_analysis', 'risk_analysis', 'health_goals'")
    consultation_id: Optional[str] = Field(None, description="Active consultation ID for multi-turn continuity")


class AgentThoughtStep(BaseModel):
    """Reflective thought step showing the agentic pipeline execution."""
    stage: str = Field(..., description="Stage: RETRIEVE, VERIFY, PROBE, ANALYZE, SAFETY_CHECK, ACT")
    detail: str = Field(..., description="What the agent evaluated")


class AgentResponse(BaseModel):
    """Structured response from the AI Health Agent."""
    consultation_id: str
    task_type: str
    message: str
    thought_pipeline: list[AgentThoughtStep] = Field(default_factory=list)
    missing_questions: list[str] = Field(default_factory=list)
    quick_replies: list[str] = Field(default_factory=list, description="Interactive choice chips for the user to click")
    stage: Optional[str] = Field(None, description="Stage in conversational flow: intake, safety_screen, guidance, goals, completed")
    red_flags_detected: list[str] = Field(default_factory=list)
    suggested_actions: list[AgentActionItem] = Field(default_factory=list)
    context_used: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disclaimer: str = "AI Health Agent provides context-aware guidance and health optimization strategies, NOT a clinical diagnosis or prescription. Always consult a qualified medical professional."


class AgentContextResponse(BaseModel):
    """Aggregated health context available for the user."""
    user_id: str
    user_name: str
    completion_percentage: int
    has_profile: bool
    has_medical_conditions: bool
    has_medications: bool
    has_lifestyle: bool
    has_history: bool
    profile_summary: dict = Field(default_factory=dict)
    lifestyle_summary: dict = Field(default_factory=dict)
    recent_consultations_count: int = 0


class AgentActionExecutionRequest(BaseModel):
    """Request to execute an action offered by the Agent."""
    consultation_id: str
    action_type: str
    title: str
    data: dict = Field(default_factory=dict)


class AgentConsultationSummary(BaseModel):
    """Summary of a past consultation."""
    id: str
    task_type: str
    title: str
    preview: str
    created_at: datetime
    updated_at: datetime
    message_count: int
