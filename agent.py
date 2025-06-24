import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    metrics,
    RoomInputOptions,
    RoomOutputOptions,
)
from livekit.plugins import (
    openai,
    deepgram,
    silero,
)
from VCAgent import VCAgent
from utils.transcript import export_transcript
from datetime import datetime
import json
import os
from database.mongodb import MongoConnector
from cohere_analysis import analyze_transcript_with_cohere
import asyncio
from typing import Optional

load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")


def prewarm(proc: JobProcess):
    from utils.load_prompt import load_prompt
    from pathlib import Path
    import asyncio

    # Load VAD
    proc.userdata["vad"] = silero.VAD.load()

    # Load Prompt (Safe for threaded context)
    project_root = Path(__file__).parent.resolve()
    prompt_path = project_root / "prompt.md"
    prompt = asyncio.run(load_prompt(str(prompt_path)))

    proc.userdata["prompt"] = prompt


async def write_transcript_to_file(
    transcript_data: dict, room_name: str
) -> Optional[str]:
    """Write transcript to file system"""
    try:
        current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = os.path.join(os.getcwd(), "transcripts")
        os.makedirs(export_dir, exist_ok=True)

        filename = os.path.join(
            export_dir, f"transcript_{room_name}_{current_date}.json"
        )

        with open(filename, "w") as f:
            json.dump(transcript_data, f, indent=2)
        logger.info(f"✅ Transcript for {room_name} saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"❌ Failed to write transcript to file: {e}")
        return None


async def write_transcript_to_db(
    transcript_data: dict, room_name: str, user_id: str
) -> bool:
    """Write transcript to MongoDB and generate analysis"""
    mongo = None
    try:
        mongo = MongoConnector()
        transcript_collection = mongo.get_collection("transcripts")

        # Add document to MongoDB
        doc = {
            "call_id": room_name,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "transcript": transcript_data,
        }

        result = await transcript_collection.insert_one(doc)
        logger.info(f"Inserted transcript with ID: {result.inserted_id}")

        # Verify the document was stored
        stored_doc = await transcript_collection.find_one({"_id": result.inserted_id})
        if not stored_doc:
            raise Exception("Failed to verify stored transcript")

        # Generate and store analysis
        transcript_analysis_doc = await analyze_transcript_with_cohere(stored_doc)

        transcript_analysis_collection = mongo.get_collection("transcript_analysis")
        analysis_result = await transcript_analysis_collection.insert_one(
            transcript_analysis_doc
        )

        logger.info(
            f"✅ Analysis for {room_name} inserted with ID: {analysis_result.inserted_id}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Failed to process transcript in MongoDB: {e}")
        return False
    finally:
        if mongo:
            await mongo.close()


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    usage_collector = metrics.UsageCollector()

    # Log metrics and collect usage data
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)

    # Getting the prompt for VC Agent from prewarm function
    vc_prompt = ctx.proc.userdata["prompt"]
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        # minimum delay for endpointing, used when turn detector believes the user is done with their turn
        min_endpointing_delay=0.5,
        # maximum delay for endpointing, used when turn detector does not believe the user is done with their turn
        max_endpointing_delay=15,
    )

    # Trigger the on_metrics_collected function when metrics are collected
    session.on("metrics_collected", on_metrics_collected)

    await session.start(
        room=ctx.room,
        agent=VCAgent(vc_prompt),
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    # Cleanup function
    async def cleanup():
        transcript_data = session.history.to_dict()

        # Write to file system
        # await write_transcript_to_file(transcript_data, ctx.room.name)

        # Write to MongoDB and generate analysis
        await write_transcript_to_db(
            transcript_data, ctx.room.name, participant.identity
        )

    # Register async cleanup
    ctx.add_shutdown_callback(lambda: asyncio.create_task(cleanup()))


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
