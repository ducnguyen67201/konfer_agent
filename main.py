from livekit.agents import AgentSession, WorkerOptions, cli, JobContext
from livekit.plugins import silero, deepgram, openai, turn_detector


def prewarm(ctx: JobContext):
    """Load silero VAD model"""


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
