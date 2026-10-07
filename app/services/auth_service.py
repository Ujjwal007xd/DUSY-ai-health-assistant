"""Authentication service: user registration, login, and JWT management."""

from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from bson import ObjectId
from fastapi import HTTPException, status

from app.config import get_settings
from app.database import get_database
from app.models.user import UserRegister, UserLogin, UserResponse, TokenResponse


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    """Create a JWT access token for the given user ID.
    
    Args:
        user_id: The user's MongoDB ObjectId as a string.
        
    Returns:
        Encoded JWT token string.
    """
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def register_user(user_data: UserRegister) -> TokenResponse:
    """Register a new user.
    
    Args:
        user_data: Registration data (name, email, password, etc.).
    
    Returns:
        TokenResponse with JWT token and user info.
        
    Raises:
        HTTPException: If email is already registered.
    """
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )
    
    # Create user document
    user_doc = {
        "name": user_data.name,
        "email": user_data.email.lower(),
        "password_hash": hash_password(user_data.password),
        "date_of_birth": user_data.date_of_birth,
        "gender": user_data.gender,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert into database
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    # Create JWT token
    access_token = create_access_token(user_id)
    
    # Build response
    user_response = UserResponse(
        id=user_id,
        name=user_doc["name"],
        email=user_doc["email"],
        date_of_birth=user_doc["date_of_birth"],
        gender=user_doc["gender"],
        created_at=user_doc["created_at"]
    )
    
    return TokenResponse(
        access_token=access_token,
        user=user_response
    )


async def login_user(login_data: UserLogin) -> TokenResponse:
    """Authenticate a user and return a JWT token.
    
    Args:
        login_data: Login credentials (email, password).
    
    Returns:
        TokenResponse with JWT token and user info.
        
    Raises:
        HTTPException: If credentials are invalid.
    """
    db = get_database()
    
    # Find user by email
    user = await db.users.find_one({"email": login_data.email.lower()})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id)
    
    user_response = UserResponse(
        id=user_id,
        name=user["name"],
        email=user["email"],
        date_of_birth=user.get("date_of_birth"),
        gender=user.get("gender"),
        created_at=user["created_at"]
    )
    
    return TokenResponse(
        access_token=access_token,
        user=user_response
    )
