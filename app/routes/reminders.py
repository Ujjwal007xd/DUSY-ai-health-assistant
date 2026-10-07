"""Medication and appointment reminder API routes."""

from fastapi import APIRouter, Depends

from app.services.reminder_service import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    create_reminder,
    get_reminders,
    update_reminder,
    delete_reminder,
    get_upcoming_reminders
)
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/reminders", tags=["Reminders"])


@router.post("/", response_model=ReminderResponse, status_code=201)
async def create(reminder_data: ReminderCreate, current_user: dict = Depends(get_current_user)):
    """Create a new reminder.
    
    Supports types: medication, appointment, checkup, exercise, water, custom.
    Frequency options: once, daily, weekly, monthly.
    """
    user_id = current_user["_id"]
    return await create_reminder(reminder_data, user_id)


@router.get("/", response_model=list[ReminderResponse])
async def list_reminders(current_user: dict = Depends(get_current_user)):
    """Get all reminders for the current user."""
    user_id = current_user["_id"]
    return await get_reminders(user_id)


@router.get("/upcoming", response_model=list[ReminderResponse])
async def upcoming(current_user: dict = Depends(get_current_user)):
    """Get upcoming active reminders."""
    user_id = current_user["_id"]
    return await get_upcoming_reminders(user_id)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update(
    reminder_id: str,
    update_data: ReminderUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing reminder."""
    user_id = current_user["_id"]
    return await update_reminder(reminder_id, update_data, user_id)


@router.delete("/{reminder_id}")
async def delete(
    reminder_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a reminder."""
    user_id = current_user["_id"]
    return await delete_reminder(reminder_id, user_id)
