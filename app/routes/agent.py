"""API Routes for the AI Health Agent."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.agent import (
    AgentInteractRequest, AgentResponse, AgentContextResponse,
    AgentActionExecutionRequest, AgentConsultationSummary
)
from app.services.agent_service import (
    get_agent_health_context, interact_with_agent,
    get_user_consultations, get_consultation_details,
    execute_agent_action, get_user_actions
)
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/agent", tags=["AI Health Agent"])


@router.get("/context", response_model=AgentContextResponse)
async def get_health_context(current_user: dict = Depends(get_current_user)):
    """Retrieve aggregated user context (profile, lifestyle, past consultations) 
    and calculate profile completion score.
    """
    user_id = str(current_user["_id"])
    return await get_agent_health_context(user_id, current_user)


@router.post("/interact", response_model=AgentResponse)
async def agent_interact(
    request: AgentInteractRequest,
    current_user: dict = Depends(get_current_user)
):
    """Interact with the personalized AI Health Agent.
    
    Executes the 7-stage pipeline:
    UNDERSTAND -> RETRIEVE -> PROBE -> ANALYZE -> SAFETY CHECK -> ACT -> STORE
    """
    return await interact_with_agent(request, current_user)


@router.get("/consultations", response_model=list[AgentConsultationSummary])
async def list_consultations(current_user: dict = Depends(get_current_user)):
    """List recent consultations/assessments conducted by the AI Agent."""
    user_id = str(current_user["_id"])
    return await get_user_consultations(user_id)


@router.get("/consultations/{consultation_id}")
async def get_consultation(
    consultation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve full consultation transcript, messages, and action state."""
    user_id = str(current_user["_id"])
    return await get_consultation_details(consultation_id, user_id)


@router.post("/action")
async def take_action(
    request: AgentActionExecutionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute an action offered by the Agent (e.g. Save Health Log, Create Goal)."""
    user_id = str(current_user["_id"])
    return await execute_agent_action(request, user_id)


@router.get("/actions")
async def list_actions(current_user: dict = Depends(get_current_user)):
    """List all actions and goals recorded by the Agent for this user."""
    user_id = str(current_user["_id"])
    return await get_user_actions(user_id)

