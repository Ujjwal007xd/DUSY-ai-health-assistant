"""MongoDB database connection and lifecycle management."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings


class Database:
    """Manages the MongoDB connection lifecycle."""
    
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


db_instance = Database()


async def connect_to_database():
    """Create MongoDB connection on application startup."""
    settings = get_settings()
    db_instance.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db_instance.db = db_instance.client[settings.DATABASE_NAME]
    
    # Verify connection
    try:
        await db_instance.client.admin.command("ping")
        print(f"[OK] Connected to MongoDB: {settings.DATABASE_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MongoDB: {e}")
        raise


async def close_database_connection():
    """Close MongoDB connection on application shutdown."""
    if db_instance.client:
        db_instance.client.close()
        print("[*] MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance. Use as a dependency."""
    if db_instance.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_database() first.")
    return db_instance.db
