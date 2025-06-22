from pymongo import MongoClient
from collections import defaultdict
import re
from analysis_util import generate_summary, get_agent_interest_score
from dotenv import load_dotenv
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from database.mongodb import MongoConnector


async def connect_to_db(uri, db_name, collection_name):
    connector = MongoConnector(uri=uri, db_name=db_name)
    return connector.get_collection(collection_name)


def clean_text(text):
    """
    Lowercase and remove punctuation except question marks.
    You can customize filler word removal here if needed.
    """
    text = text.lower()
    # Remove punctuation except question marks to preserve questions
    text = re.sub(r"[^\w\s\?]", "", text)
    # Optionally remove filler words - example list
    filler_words = {"um", "uh", "like", "you know", "so", "actually", "basically"}
    # Remove filler words by splitting and filtering
    words = text.split()
    filtered_words = [w for w in words if w not in filler_words]
    return " ".join(filtered_words)


def preprocess_transcript(doc):
    """
    Input: MongoDB doc (dict)
    Output: dict with normalized turns and metadata
    """
    transcript_items = doc.get("transcript", {}).get("items", [])

    # Separate user and assistant turns
    user_turns = []
    agent_turns = []
    user_interruptions = 0
    agent_interruptions = 0

    for item in transcript_items:
        role = item.get("role")
        content_list = item.get("content", [])
        # Join list of strings into one utterance string
        utterance_raw = " ".join(content_list).strip()
        utterance = clean_text(utterance_raw)
        interrupted = item.get("interrupted", False)

        if role == "user":
            user_turns.append(utterance)
            if interrupted:
                user_interruptions += 1
        elif role == "assistant":
            agent_turns.append(utterance)
            if interrupted:
                agent_interruptions += 1
        else:
            # If role unknown or other, skip or log
            pass

    # Basic Metadata
    def count_words(text_list):
        return sum(len(t.split()) for t in text_list)

    user_word_count = count_words(user_turns)
    agent_word_count = count_words(agent_turns)
    user_turn_count = len(user_turns)
    agent_turn_count = len(agent_turns)

    user_avg_words_per_turn = (
        user_word_count / user_turn_count if user_turn_count else 0
    )
    agent_avg_words_per_turn = (
        agent_word_count / agent_turn_count if agent_turn_count else 0
    )

    # Call timestamp (top-level)
    timestamp_field = doc.get("timestamp", None)
    if isinstance(timestamp_field, dict):
        timestamp = timestamp_field.get("$date", None)
    else:
        timestamp = timestamp_field

    result = {
        "call_id": doc.get("call_id"),
        "timestamp": timestamp,
        "user_turns": user_turns,
        "agent_turns": agent_turns,
        "user_word_count": user_word_count,
        "agent_word_count": agent_word_count,
        "user_turn_count": user_turn_count,
        "agent_turn_count": agent_turn_count,
        "user_avg_words_per_turn": user_avg_words_per_turn,
        "agent_avg_words_per_turn": agent_avg_words_per_turn,
        "user_interruptions": user_interruptions,
        "agent_interruptions": agent_interruptions,
    }

    return result


async def process_transcripts(collection, room_name):
    # Query for the specific room's transcript
    cursor = collection.find({"call_id": room_name})

    async for doc in cursor:
        processed = preprocess_transcript(doc)
        summary = await generate_summary(processed["user_turns"])
        agent_interest_score = await get_agent_interest_score(processed["agent_turns"])

        # Create analysis document
        analysis = {
            "call_id": processed["call_id"],
            "timestamp": processed["timestamp"],
            "user_avg_words_per_turn": processed["user_avg_words_per_turn"],
            "agent_avg_words_per_turn": processed["agent_avg_words_per_turn"],
            "summary": summary,
            "agent_interest_score": agent_interest_score,
        }

        # Store analysis in transcript_analysis collection
        analysis_collection = collection.database.get_collection("transcript_analysis")
        await analysis_collection.update_one(
            {"call_id": room_name}, {"$set": analysis}, upsert=True
        )

        print("______analysis", analysis)


async def run_transcript_summary(room_name: str):
    # Setup connection info
    load_dotenv()  # Load environment variables from .env file if needed
    uri = os.getenv("MONGODB_URI")  # Replace with your MongoDB URI
    db_name = "transcripts"  # Replace this
    collection_name = "transcripts"  # Replace this

    # Create MongoDB connector
    connector = MongoConnector(uri=uri, db_name=db_name)
    collection = connector.get_collection(collection_name)

    try:
        await process_transcripts(collection, room_name)
    finally:
        # Close the MongoDB connection
        await connector.close()
