from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

# Default to authenticated connection if no URI provided
DEFAULT_MONGO_URI = "mongodb://admin:pass123@localhost:27017"
MONGO_URI = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "transcripts")


class MongoConnector:
    def __init__(self, uri: str = MONGO_URI, db_name: str = MONGO_DB_NAME):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    def get_collection(self, name: str):
        return self.db[name]

    async def close(self):
        self.client.close()
