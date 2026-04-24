import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1-chat")

NUM_REACTORS = int(os.getenv("NUM_REACTORS", "15"))
W_ENGAGEMENT = float(os.getenv("W_ENGAGEMENT", "0.5"))
W_SENTIMENT = float(os.getenv("W_SENTIMENT", "0.5"))
NUM_PAST_POSTS = int(os.getenv("NUM_PAST_POSTS", "5"))

DATABASE_URL = "sqlite:///./social_sim.db"