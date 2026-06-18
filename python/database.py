"""MongoDB client setup and shared collection handles for the SGarden API."""
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client = AsyncIOMotorClient(settings.database_url)

# Extract database name from URL, default to "sgarden"
if "/" in settings.database_url:
    DB_NAME = settings.database_url.rsplit("/", 1)[-1].split("?")[0]
else:
    DB_NAME = "sgarden"
db = client[DB_NAME]

users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]


async def init_indexes():
    """Create database indexes on startup."""
    await users_collection.create_index("username", unique=True)
    await users_collection.create_index("email", unique=True)
