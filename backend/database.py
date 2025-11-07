"""Database connection module."""
from motor.motor_asyncio import AsyncIOMotorClient
from config import config
from utils.logging import get_logger

logger = get_logger(__name__)

# MongoDB connection
client = AsyncIOMotorClient(
    config.MONGO_URL,
    serverSelectionTimeoutMS=8000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
    retryWrites=True,
)
db = client[config.DB_NAME]

logger.info(f"MongoDB client initialized for database: {config.DB_NAME}")


async def close_db_connection():
    """Close database connection."""
    client.close()
    logger.info("MongoDB connection closed")
