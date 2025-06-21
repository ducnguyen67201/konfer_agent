from livekit.agents import AgentSession, JobContext
import os
import json
import logging

logger = logging.getLogger("voice-agent")


async def export_transcript(ctx: JobContext, session: AgentSession):
    """Export the transcript of the call to a file"""

    transcript_data = session.history.to_dict()

    file_name = f"{ctx.room.name}_transcript.json"
    filepath = os.path.join("transcripts", file_name)

    os.makedirs("transcripts", exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(transcript_data, f, indent=2)

    logger.info(f"Transcript exported to {filepath}")
