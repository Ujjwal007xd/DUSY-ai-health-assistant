"""Medication and appointment reminder service."""

from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database


# Pydantic models for reminders (defined inline for simplicity)
from pydantic import BaseModel, Field
from typing import Optional


class ReminderCreate(BaseModel):
    """Schema for creating a reminder."""
    title: str = Field(..., min_length=1, max_length=200, description="Reminder title")
    description: Optional[str] = Field(None, description="Additional details")
    reminder_type: str = Field(..., description="Type: medication, appointment, checkup, exercise, water, custom")
    frequency: str = Field("once", description="Frequency: once, daily, weekly, monthly")
    scheduled_time: str = Field(..., description="Scheduled time (ISO format or HH:MM)")
    scheduled_date: Optional[str] = Field(None, description="Scheduled date (YYYY-MM-DD) for one-time reminders")
    is_active: bool = Field(True, description="Whether the reminder is active")


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""
    title: Optional[str] = None
    description: Optional[str] = None
    reminder_type: Optional[str] = None
    frequency: Optional[str] = None
    scheduled_time: Optional[str] = None
    scheduled_date: Optional[str] = None
    is_active: Optional[bool] = None


class ReminderResponse(BaseModel):
    """Reminder response model."""
    id: str
    title: str
    description: Optional[str] = None
    reminder_type: str
    frequency: str
    scheduled_time: str
    scheduled_date: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


async def create_reminder(reminder_data: ReminderCreate, user_id: str) -> ReminderResponse:
    """Create a new reminder.
    
    Args:
        reminder_data: Reminder details.
        user_id: The authenticated user's ID.
    
    Returns:
        ReminderResponse with the created reminder.
    """
    db = get_database()
    now = datetime.utcnow()
    
    reminder_doc = {
        "user_id": user_id,
        **reminder_data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    
    result = await db.reminders.insert_one(reminder_doc)
    
    return ReminderResponse(
        id=str(result.inserted_id),
        **reminder_data.model_dump(),
        created_at=now,
        updated_at=now
    )


async def get_reminders(user_id: str, active_only: bool = False) -> list[ReminderResponse]:
    """Get all reminders for a user.
    
    Args:
        user_id: The authenticated user's ID.
        active_only: If True, only return active reminders.
    
    Returns:
        List of ReminderResponse objects.
    """
    db = get_database()
    
    query = {"user_id": user_id}
    if active_only:
        query["is_active"] = True
    
    cursor = db.reminders.find(query).sort("scheduled_time", 1)
    
    reminders = []
    async for doc in cursor:
        reminders.append(ReminderResponse(
            id=str(doc["_id"]),
            title=doc["title"],
            description=doc.get("description"),
            reminder_type=doc["reminder_type"],
            frequency=doc["frequency"],
            scheduled_time=doc["scheduled_time"],
            scheduled_date=doc.get("scheduled_date"),
            is_active=doc["is_active"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        ))
    
    return reminders


async def update_reminder(
    reminder_id: str,
    update_data: ReminderUpdate,
    user_id: str
) -> ReminderResponse:
    """Update an existing reminder.
    
    Args:
        reminder_id: The reminder's MongoDB ID.
        update_data: Fields to update.
        user_id: The authenticated user's ID.
    
    Returns:
        Updated ReminderResponse.
        
    Raises:
        HTTPException: If reminder not found.
    """
    db = get_database()
    
    # Only update fields that were provided (not None)
    update_fields = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_fields["updated_at"] = datetime.utcnow()
    
    result = await db.reminders.find_one_and_update(
        {"_id": ObjectId(reminder_id), "user_id": user_id},
        {"$set": update_fields},
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found."
        )
    
    return ReminderResponse(
        id=str(result["_id"]),
        title=result["title"],
        description=result.get("description"),
        reminder_type=result["reminder_type"],
        frequency=result["frequency"],
        scheduled_time=result["scheduled_time"],
        scheduled_date=result.get("scheduled_date"),
        is_active=result["is_active"],
        created_at=result["created_at"],
        updated_at=result["updated_at"]
    )


async def delete_reminder(reminder_id: str, user_id: str) -> dict:
    """Delete a reminder.
    
    Args:
        reminder_id: The reminder's MongoDB ID.
        user_id: The authenticated user's ID.
    
    Returns:
        Success message dict.
    
    Raises:
        HTTPException: If reminder not found.
    """
    db = get_database()
    
    result = await db.reminders.delete_one({
        "_id": ObjectId(reminder_id),
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found."
        )
    
    return {"message": "Reminder deleted successfully."}


async def get_upcoming_reminders(user_id: str) -> list[ReminderResponse]:
    """Get upcoming active reminders for a user."""
    return await get_reminders(user_id, active_only=True)
