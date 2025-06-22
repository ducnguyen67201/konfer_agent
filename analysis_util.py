from nltk.sentiment import SentimentIntensityAnalyzer
from transformers import T5Tokenizer, T5ForConditionalGeneration
import asyncio
import torch

# Load once globally if you're calling this multiple times
tokenizer = T5Tokenizer.from_pretrained("t5-base")
model = T5ForConditionalGeneration.from_pretrained("t5-base")


async def generate_summary(transcript):
    """
    Summarize the user's pitch from the transcript.
    transcript: list of user utterances (strings)
    Returns: summary string
    """
    # Join user utterances into a single input string
    text = " ".join(transcript)
    input_text = "summarize: " + text.strip()

    # Run tokenization and model inference in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()

    # Tokenize input
    inputs = await loop.run_in_executor(
        None,
        lambda: tokenizer(
            input_text, return_tensors="pt", max_length=512, truncation=True
        ),
    )

    # Generate summary
    summary_ids = await loop.run_in_executor(
        None,
        lambda: model.generate(
            inputs["input_ids"], max_length=100, num_beams=4, early_stopping=True
        ),
    )

    # Decode and return
    summary = await loop.run_in_executor(
        None, lambda: tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    )
    return summary


async def get_agent_interest_score(agent_turns):
    """
    Analyze agent sentiment to estimate interest.
    agent_turns: list of agent utterances (strings)
    Returns: average compound sentiment score (-1 to 1)
    """
    if not agent_turns:
        return 0.0

    sia = SentimentIntensityAnalyzer()
    loop = asyncio.get_event_loop()

    # Run sentiment analysis in thread pool since it's CPU-bound
    scores = await asyncio.gather(
        *[
            loop.run_in_executor(
                None, lambda turn=turn: sia.polarity_scores(turn)["compound"]
            )
            for turn in agent_turns
        ]
    )

    return sum(scores) / len(scores)
