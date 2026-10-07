"""AI service: Gemini-powered conversational health assistant."""

import json
from datetime import datetime
from bson import ObjectId

from google import genai
from google.genai import types
from fastapi import HTTPException, status

from app.config import get_settings
from app.database import get_database
from app.models.chat import ChatRequest, ChatResponse, ChatMessage
from app.utils.helpers import generate_conversation_title


# System prompt that defines the AI agent's behavior
HEALTH_ASSISTANT_PROMPT = """You are an AI-powered Personalized Health Assistant. Your role is to provide helpful, 
accurate, and empathetic health guidance to users. 

IMPORTANT GUIDELINES:
1. You are NOT a doctor. Always remind users that your advice is informational and they should consult 
   healthcare professionals for medical decisions.
2. Never diagnose conditions definitively. Use phrases like "this could be", "you might want to consider".
3. If a user describes emergency symptoms (chest pain, difficulty breathing, signs of stroke, severe bleeding, 
   loss of consciousness), IMMEDIATELY advise them to call emergency services.
4. Be empathetic, warm, and supportive in your responses.
5. Provide evidence-based health information.
6. Consider the user's health profile when giving personalized advice.
7. For mental health concerns, be extra sensitive and always recommend professional support.
8. Keep responses clear, organized, and easy to understand.
9. When discussing medications, always advise consulting a doctor or pharmacist.
10. Encourage healthy lifestyle habits: balanced diet, regular exercise, adequate sleep, stress management.

When you have access to the user's health profile, personalize your advice based on their:
- Medical conditions
- Allergies
- Current medications
- Age and gender
- Lifestyle habits
"""


def _get_gemini_client():
    """Get the Gemini API client."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _build_user_context(health_profile: dict | None, user: dict) -> str:
    """Build a context string from the user's health profile."""
    context = f"\n\nUSER CONTEXT:\n- Name: {user.get('name', 'User')}\n"
    
    if user.get("date_of_birth"):
        context += f"- Date of Birth: {user['date_of_birth']}\n"
    if user.get("gender"):
        context += f"- Gender: {user['gender']}\n"
    
    if health_profile:
        if health_profile.get("blood_group"):
            context += f"- Blood Group: {health_profile['blood_group']}\n"
        if health_profile.get("height_cm") and health_profile.get("weight_kg"):
            context += f"- Height: {health_profile['height_cm']}cm, Weight: {health_profile['weight_kg']}kg\n"
        if health_profile.get("medical_conditions"):
            context += f"- Medical Conditions: {', '.join(health_profile['medical_conditions'])}\n"
        if health_profile.get("allergies"):
            context += f"- Allergies: {', '.join(health_profile['allergies'])}\n"
        if health_profile.get("current_medications"):
            context += f"- Current Medications: {', '.join(health_profile['current_medications'])}\n"
        if health_profile.get("lifestyle_habits"):
            habits = health_profile["lifestyle_habits"]
            context += f"- Lifestyle: {json.dumps(habits)}\n"
    else:
        context += "- Health profile: Not yet created\n"
    
    return context


async def chat_with_ai(chat_request: ChatRequest, user: dict) -> ChatResponse:
    """Process a chat message and return an AI response.
    
    Args:
        chat_request: The user's chat message and optional conversation ID.
        user: The authenticated user's document.
    
    Returns:
        ChatResponse with the AI's reply and conversation ID.
    """
    db = get_database()
    client = _get_gemini_client()
    user_id = user["_id"] if isinstance(user["_id"], str) else str(user["_id"])
    
    # Fetch user's health profile for context
    health_profile = await db.health_profiles.find_one({"user_id": user_id})
    user_context = _build_user_context(health_profile, user)
    
    # Load or create conversation
    conversation_id = chat_request.conversation_id
    conversation = None
    
    if conversation_id:
        conversation = await db.conversations.find_one({
            "_id": ObjectId(conversation_id),
            "user_id": user_id
        })
    
    if conversation is None:
        # Create new conversation
        conversation = {
            "user_id": user_id,
            "title": generate_conversation_title(chat_request.message),
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await db.conversations.insert_one(conversation)
        conversation_id = str(result.inserted_id)
        conversation["_id"] = result.inserted_id
    else:
        conversation_id = str(conversation["_id"])
    
    # Build message history for Gemini
    contents = []
    for msg in conversation.get("messages", [])[-20:]:  # Last 20 messages for context window
        contents.append(
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    
    # Add current user message
    full_system_prompt = HEALTH_ASSISTANT_PROMPT + user_context
    
    # If first message, prepend system context
    if not contents:
        user_prompt = f"{full_system_prompt}\n\nUser message: {chat_request.message}"
    else:
        user_prompt = chat_request.message
    
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        )
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )
        ai_response = response.text
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )
    
    # Store messages in conversation
    now = datetime.utcnow()
    user_message = {"role": "user", "content": chat_request.message, "timestamp": now}
    assistant_message = {"role": "assistant", "content": ai_response, "timestamp": now}
    
    await db.conversations.update_one(
        {"_id": conversation["_id"]},
        {
            "$push": {"messages": {"$each": [user_message, assistant_message]}},
            "$set": {"updated_at": now}
        }
    )
    
    return ChatResponse(
        conversation_id=conversation_id,
        message=ai_response
    )


async def get_chat_history(conversation_id: str, user_id: str) -> list[dict]:
    """Get the message history for a conversation."""
    db = get_database()
    
    conversation = await db.conversations.find_one({
        "_id": ObjectId(conversation_id),
        "user_id": user_id
    })
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    return conversation.get("messages", [])


async def get_conversations(user_id: str) -> list[dict]:
    """List all conversations for a user."""
    db = get_database()
    
    cursor = db.conversations.find(
        {"user_id": user_id},
        {"messages": {"$slice": -1}, "title": 1, "created_at": 1, "updated_at": 1}
    ).sort("updated_at", -1)
    
    conversations = []
    async for conv in cursor:
        conversations.append({
            "conversation_id": str(conv["_id"]),
            "title": conv.get("title", "Untitled"),
            "last_message_at": conv.get("updated_at"),
            "created_at": conv.get("created_at")
        })
    
    return conversations


async def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """Delete a conversation and its messages."""
    db = get_database()
    
    result = await db.conversations.delete_one({
        "_id": ObjectId(conversation_id),
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    return True
