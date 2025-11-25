from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db_instance = Database()


async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db_instance.client = AsyncIOMotorClient(settings.MONGO_URL)
    db_instance.db = db_instance.client[settings.DB_NAME]
    
    # Create indexes
    await db_instance.db.users.create_index("email", unique=True)
    await db_instance.db.opportunities.create_index("score")
    await db_instance.db.opportunities.create_index("created_at")
    await db_instance.db.recommendations.create_index("user_id")
    await db_instance.db.raw_signals.create_index("processed")
    
    logger.info("Connected to MongoDB successfully")


async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_instance.client:
        db_instance.client.close()
    logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    return db_instance.db
