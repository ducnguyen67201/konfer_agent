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
)
from livekit.plugins import (
    openai,
    deepgram,
    silero,
)

from utils.load_prompt import load_prompt
from pathlib import Path
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VCAgent(Agent):
    def __init__(self, prompt: str, model: str = "gpt-4o-mini"):
        super().__init__(
            instructions=prompt,
            stt=deepgram.STT(),
            llm=openai.LLM(model=model),
            tts=deepgram.TTS(),
        )

    @classmethod
    async def create(cls, model: str = "gpt-4o-mini"):
        project_root = Path(__file__).parent.resolve()
        prompt_path = project_root / "prompt.md"
        prompt = await load_prompt(str(prompt_path))
        return cls(prompt=prompt, model=model)

    async def on_enter(self):
        await asyncio.sleep(0.5)
        await self.session.generate_reply(
            instructions=(
                "Thank you for coming in today. I'm Alex, a partner at Pinnacle Ventures. "
                "Please go ahead with your pitch — I may ask a few questions along the way."
            ),
            allow_interruptions=True,
        )
