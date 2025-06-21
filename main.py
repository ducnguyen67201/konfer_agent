from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from dotenv import load_dotenv
import os
import json

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
