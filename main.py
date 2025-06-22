from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from dotenv import load_dotenv
import os
import json
from database.mongodb import MongoConnector
from bson import json_util, ObjectId
from datetime import datetime

load_dotenv(dotenv_path=".env.local")

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_HOST = os.getenv("LIVEKIT_HOST")

# Create transcripts directory if it doesn't exist
os.makedirs("transcripts", exist_ok=True)

app = FastAPI()

# Enable CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/get-token")
async def get_token(identity: str = Query(...), room: str = Query(...)):
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name("LiveKit User")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    )
    return {
        "token": token.to_jwt(),
        "url": os.getenv("LIVEKIT_URL"),
    }


@app.get("/transcript/{room_name}")
async def get_transcript_on_room(room_name: str):
    """Get the transcript for a specific room"""
    # Create the transcript directory if it doesn't exist
    os.makedirs("transcripts", exist_ok=True)

    transcript_file = f"{room_name}_transcript.json"
    transcript_path = os.path.join("transcripts", transcript_file)

    if not os.path.exists(transcript_path):
        raise HTTPException(status_code=404, detail="Transcript not found")

    try:
        with open(transcript_path, "r") as f:
            transcript_data = json.load(f)
        return transcript_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid transcript data")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading transcript: {str(e)}"
        )


@app.post("/transcript/test")
async def test_transcript(room_name: str = Query(...), transcript: dict = Body(...)):
    """Test the transcript endpoint

    Args:
        room_name: The name of the room for the transcript
        transcript: The transcript data to store
    """
    print(f"Storing transcript for room: {room_name}")  # Debug log
    mongo = MongoConnector()
    transcript_collection = mongo.get_collection("transcripts")

    # Add timestamp if not present
    if "timestamp" not in transcript:
        transcript["timestamp"] = datetime.utcnow()

    result = await transcript_collection.insert_one(transcript)
    inserted_id = result.inserted_id
    print(f"Inserted document with ID: {inserted_id}")  # Debug log

    # Verify the document was stored
    stored_doc = await transcript_collection.find_one({"_id": inserted_id})
    print(f"Retrieved document with ID: {stored_doc.get('_id')}")  # Debug log

    return {"message": "Transcript endpoint is working", "id": str(result.inserted_id)}


@app.get("/transcripts")
async def get_all_transcripts():
    """Get all transcripts from the database (only id, call_id, and timestamp)"""
    mongo = MongoConnector()
    transcript_collection = mongo.get_collection("transcripts")

    # Project only _id, call_id, and timestamp fields
    cursor = transcript_collection.find({}, {"_id": 1, "call_id": 1, "timestamp": 1})
    transcripts = await cursor.to_list(length=100)

    # Clean up and reformat
    cleaned = [
        {
            "id": str(item["_id"]),
            "call_id": item.get("call_id"),
            "timestamp": (
                item.get("timestamp").isoformat() if item.get("timestamp") else None
            ),
        }
        for item in transcripts
    ]
    return cleaned


# @app.get("/transcript_by_id/{id}")
# async def get_transcript_by_id(id: str):
#     """Get a single transcript, cleaned for UI display"""
#     try:
#         object_id = ObjectId(id)
#     except:
#         raise HTTPException(status_code=400, detail="Invalid transcript ID format")

#     mongo = MongoConnector()
#     transcript_collection = mongo.get_collection("transcripts")

#     document = await transcript_collection.find_one({"_id": object_id})
#     if not document:
#         raise HTTPException(status_code=404, detail="Transcript not found")

#     # Cleaned response
#     return {
#         "id": str(document["_id"]),
#         "call_id": document.get("call_id"),
#         "timestamp": (
#             document.get("timestamp").isoformat() if document.get("timestamp") else None
#         ),
#         "messages": [
#             {"role": item.get("role"), "text": " ".join(item.get("content", []))}
#             for item in document.get("transcript", {}).get("items", [])
#             if item.get("type") == "message"
#         ],
#     }


@app.get("/analysis-result")
async def get_transcript_analysis_by_room(room: str):
    """Get the analysis for a specific transcript by room name via query parameter"""
    mongo = MongoConnector()
    transcript_collection = mongo.get_collection("transcript_analysis")

    document = await transcript_collection.find_one({"call_id": room})
    if not document:
        raise HTTPException(status_code=404, detail="Transcript analysis not found")

    # Convert ObjectId to string before returning
    if "_id" in document:
        document["_id"] = str(document["_id"])

    # Convert any other ObjectId fields that might be nested in the document
    def convert_objectid(obj):
        if isinstance(obj, dict):
            return {k: convert_objectid(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_objectid(item) for item in obj]
        elif isinstance(obj, ObjectId):
            return str(obj)
        return obj

    document = convert_objectid(document)
    return document
