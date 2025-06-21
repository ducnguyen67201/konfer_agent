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
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from VCAgent import VCAgent
from utils.transcript import export_transcript
from datetime import datetime
import json
import os
from database.mongodb import MongoConnector

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
        max_endpointing_delay=5.0,
    )

    # Trigger the on_metrics_collected function when metrics are collected
    session.on("metrics_collected", on_metrics_collected)

    await session.start(
        room=ctx.room,
        agent=VCAgent(vc_prompt),
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    """
    Cleaning up after the session is done
    """

    # ? 1. Export the transcript of the entire call
    async def write_transcript():
        current_date = datetime.now().strftime("%Y%m%d_%H%M%S")

        export_dir = os.path.join(os.getcwd(), "transcripts")
        transcript_data = session.history.to_dict()
        os.makedirs(export_dir, exist_ok=True)

        filename = os.path.join(
            export_dir, f"transcript_{ctx.room.name}_{current_date}.json"
        )

        try:
            with open(filename, "w") as f:
                json.dump(session.history.to_dict(), f, indent=2)
            print(f"✅ Transcript for {ctx.room.name} saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to write transcript: {e}")

        # ? 1.2 Write transcript to MongoDB
        try:
            mongo = MongoConnector()
            transcript_collection = mongo.get_collection("transcripts")

            await transcript_collection.insert_one(
                {
                    "call_id": ctx.room.name,
                    "timestamp": datetime.utcnow(),
                    "transcript": transcript_data,  # ✅ structured dict
                }
            )
        except Exception as e:
            logger.error(f"❌ Failed to write transcript: {e}")

    print(f"✅ Full transcript for {ctx.room.name} inserted into MongoDB")

    ctx.add_shutdown_callback(write_transcript)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
