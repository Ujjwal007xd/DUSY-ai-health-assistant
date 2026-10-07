"""AI Health Assistant — Main Application Entry Point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import connect_to_database, close_database_connection
from app.routes import auth, health, chat, symptoms, reminders, preventive, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    print("[*] Starting AI Health Assistant...")
    await connect_to_database()
    print("[OK] Application ready!")
    yield
    # Shutdown
    await close_database_connection()
    print("[*] Application shut down.")


# Initialize FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    **AI-Powered Personalized Health Assistant API**
    
    An intelligent health assistant that provides:
    - AI-powered health conversations (Gemini)
    - Symptom analysis and triage
    - Personalized health profile management
    - Medication & appointment reminders
    - Health insights and summaries
    
    **Disclaimer**: This is an AI-based health guidance system, NOT a substitute 
    for professional medical advice, diagnosis, or treatment.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(symptoms.router)
app.include_router(reminders.router)
app.include_router(preventive.router)
app.include_router(agent.router)


@app.get("/", tags=["Health Check"])
async def root():
    """Root endpoint — API health check."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "message": "Welcome to the AI Health Assistant API! Visit /docs for the interactive API documentation."
    }


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}
