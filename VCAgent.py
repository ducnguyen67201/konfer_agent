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
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from utils.load_prompt import load_prompt
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VCAgent(Agent):
    """This agent will act as VC, that will provide feedback to the user also generated the script"""

    # Loading the prompt for VC Agent
    project_root = Path(__file__).parent.resolve()
    prompt_path = project_root / "prompt.md"
    prompt = load_prompt(str(prompt_path))

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(
            instructions=self.prompt,
            stt=deepgram.STT(),
            llm=openai.LLM(model=model),
            tts=deepgram.TTS(),
            turn_detection=MultilingualModel(),
        )

    async def on_enter(self):
        # The agent should be polite and greet the user when it joins :)
        self.session.generate_reply(
            instructions=(
                "Thank you for coming in today. I’m Alex, a partner at Pinnacle Ventures. "
                "Please go ahead with your pitch — I may ask a few questions along the way."
            ),
            allow_interruptions=True,
        )
