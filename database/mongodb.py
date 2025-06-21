from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "voice_logs")


class MongoConnector:
    def __init__(self, uri: str = MONGO_URI, db_name: str = MONGO_DB_NAME):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    def get_collection(self, name: str):
        return self.db[name]

    async def close(self):
        self.client.close()
