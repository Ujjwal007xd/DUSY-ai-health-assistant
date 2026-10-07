"""Authentication API routes."""

from fastapi import APIRouter, Depends

from app.models.user import UserRegister, UserLogin, TokenResponse, UserResponse
from app.services.auth_service import register_user, login_user
from app.middleware.auth_middleware import get_current_user


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserRegister):
    """Register a new user account.
    
    Creates a new user with the provided details and returns a JWT token.
    """
    return await register_user(user_data)


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login with email and password.
    
    Returns a JWT access token for authenticating future requests.
    """
    return await login_user(login_data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return UserResponse(
        id=current_user["_id"],
        name=current_user["name"],
        email=current_user["email"],
        date_of_birth=current_user.get("date_of_birth"),
        gender=current_user.get("gender"),
        created_at=current_user["created_at"]
    )
