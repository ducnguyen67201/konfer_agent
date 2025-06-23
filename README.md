Glimpse Voice Agent
Glimpse is a Python voice agent built on LiveKit Agents.
It listens to a founder’s spoken pitch, uses an LLM to respond like a seasoned VC partner, and speaks its replies back in real time.

Environment setup (.env.local)
Create a file named .env.local in the project root and add the keys you obtained from the respective services:

env
Copy
Edit
# LiveKit server
LIVEKIT_URL=https://your-livekit-server
LIVEKIT_API_KEY=lk_api_key
LIVEKIT_API_SECRET=lk_api_secret

# OpenAI (LLM)
OPENAI_API_KEY=sk-...

# Deepgram (STT + TTS)
DEEPGRAM_API_KEY=dg_...

# Optional – if you enabled additional plugins
# CARTESIA_API_KEY=...
That’s it—run the agent with python agent.py console (local mic) or python agent.py dev (with a LiveKit web frontend).

![image](https://github.com/user-attachments/assets/28bdf02d-65e8-47d1-9952-3255eff5d332)

![image](https://github.com/user-attachments/assets/bb4aa2e5-c121-48c3-b55b-24e003cb395f)
