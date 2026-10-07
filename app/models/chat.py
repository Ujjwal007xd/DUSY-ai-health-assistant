"""Chat and conversation data models."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ChatRequest(BaseModel):
    """User's chat message input."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID (None for new conversation)")


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    """AI assistant's chat response."""
    conversation_id: str
    message: str = Field(..., description="AI assistant's response")
    disclaimer: str = "This is AI-generated health guidance, not medical advice. Please consult a healthcare professional for diagnosis and treatment."


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    conversation_id: str
    title: str
    message_count: int
    last_message_at: datetime
    created_at: datetime
