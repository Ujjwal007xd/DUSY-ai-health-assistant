"""AI Chat API routes."""

from fastapi import APIRouter, Depends

from app.models.chat import ChatRequest, ChatResponse
from app.services.ai_service import (
    chat_with_ai,
    get_chat_history,
    get_conversations,
    delete_conversation
)
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to the AI health assistant.
    
    The AI considers your health profile for personalized responses.
    Include a conversation_id to continue an existing conversation,
    or omit it to start a new one.
    """
    return await chat_with_ai(chat_request, current_user)


@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """List all chat conversations for the current user."""
    user_id = current_user["_id"]
    return await get_conversations(user_id)


@router.get("/history/{conversation_id}")
async def get_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the message history for a specific conversation."""
    user_id = current_user["_id"]
    return await get_chat_history(conversation_id, user_id)


@router.delete("/history/{conversation_id}")
async def delete_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation and all its messages."""
    user_id = current_user["_id"]
    await delete_conversation(conversation_id, user_id)
    return {"message": "Conversation deleted successfully."}
