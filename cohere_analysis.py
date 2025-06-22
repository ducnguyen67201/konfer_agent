import cohere
import os
import json
import asyncio
from typing import Dict, Any, List, Tuple
import aiohttp


# Load Cohere API key from environment variable or replace with your actual key
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY)


async def generate_improvement_points(founder_lines: List[str]) -> List[str]:
    """Generate specific improvement points based on founder's pitch"""
    combined_text = "\n".join(founder_lines)

    prompt = f"""
    As an experienced VC, analyze this founder's pitch and provide 3 specific, actionable improvement points.
    Format each point as a clear, direct recommendation that would make the pitch stronger.
    
    Founder's Pitch:
    {combined_text}
    
    Respond with exactly 3 improvement points in this JSON format:
    {{
        "improvements": [
            "First specific improvement point",
            "Second specific improvement point",
            "Third specific improvement point"
        ]
    }}
    """

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: co.generate(
                model="command-r-plus",
                prompt=prompt,
                max_tokens=300,
                temperature=0.7,
                stop_sequences=["\n\n"],
            ),
        )

        result = json.loads(response.generations[0].text.strip())
        return result["improvements"]
    except Exception as e:
        print("❌ Error generating improvements:", e)
        return [
            "Focus on clarifying your unique value proposition",
            "Provide more specific market size data",
            "Elaborate on your go-to-market strategy",
        ]


async def get_agent_interest_score(vc_lines: List[str]) -> float:
    """Calculate VC's interest level based on their responses"""
    combined_text = "\n".join(vc_lines)

    prompt = f"""
    Analyze these VC responses from a pitch meeting and determine their level of interest.
    Consider factors like:
    - Engagement level in questions
    - Depth of follow-ups
    - Tone and language used
    - Types of concerns raised
    
    VC Responses:
    {combined_text}
    
    Respond with only a float between 0.0 (completely uninterested) and 1.0 (highly interested).
    """

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: co.generate(
                model="command-r-plus",
                prompt=prompt,
                max_tokens=50,
                temperature=0.3,
                stop_sequences=["\n"],
            ),
        )

        score = float(response.generations[0].text.strip())
        return min(max(score, 0.0), 1.0)  # Ensure score is between 0 and 1
    except Exception as e:
        print("❌ Error calculating interest score:", e)
        return 0.5


async def analyze_transcript_with_cohere(
    transcript_doc: Dict[str, Any],
) -> Dict[str, Any]:
    call_id = transcript_doc["call_id"]
    timestamp = transcript_doc["timestamp"]
    items = transcript_doc["transcript"]["items"]

    # Separate messages by role
    user_turns = [" ".join(i["content"]) for i in items if i["role"] == "user"]
    assistant_turns = [
        " ".join(i["content"]) for i in items if i["role"] == "assistant"
    ]

    # Calculate average words per turn
    user_word_count = sum(len(turn.split()) for turn in user_turns)
    assistant_word_count = sum(len(turn.split()) for turn in assistant_turns)

    user_avg_words_per_turn = (
        round(user_word_count / len(user_turns), 2) if user_turns else 0
    )
    agent_avg_words_per_turn = (
        round(assistant_word_count / len(assistant_turns), 2) if assistant_turns else 0
    )

    # Build transcript text
    combined_text = "\n".join(
        f"{item['role'].capitalize()}: {' '.join(item['content'])}" for item in items
    )

    # Build prompt for summary
    prompt = f"""
    You are a startup pitch evaluator. Below is a full transcript of a pitch between a founder and a simulated VC.

    Analyze the transcript and respond with this exact JSON format:
    {{
    "summary": "short summary of the pitch..."
    }}

    Transcript:
    {combined_text}
    """

    # Run Cohere API calls in parallel
    loop = asyncio.get_event_loop()
    try:
        # Get summary
        summary_response = await loop.run_in_executor(
            None,
            lambda: co.generate(
                model="command-r-plus",
                prompt=prompt,
                max_tokens=500,
                temperature=0.5,
                stop_sequences=["\n\n"],
            ),
        )

        summary_data = json.loads(summary_response.generations[0].text.strip())

        # Get improvements and interest score concurrently
        improvements, interest_score = await asyncio.gather(
            generate_improvement_points(user_turns),
            get_agent_interest_score(assistant_turns),
        )

    except Exception as e:
        print("❌ Error in analysis:", e)
        summary_data = {"summary": "Failed to generate analysis."}
        improvements = [
            "Clarify value proposition",
            "Provide market data",
            "Detail execution plan",
        ]
        interest_score = 0.5

    return {
        "call_id": call_id,
        "timestamp": timestamp,
        "user_avg_words_per_turn": user_avg_words_per_turn,
        "agent_avg_words_per_turn": agent_avg_words_per_turn,
        "summary": summary_data["summary"],
        "improvements": improvements,
        "agent_interest_score": interest_score,
    }
