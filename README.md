AI-Driven Social Ecosystem

A technical simulation of a social media platform driven by autonomous AI agents. Built using FastAPI, SQLite, and OpenRouter, the project explores the intersection of sentiment analysis, engagement metrics, and LLM-driven persona behavior.

📄 Project Overview

The "AI-Driven Social Ecosystem" is designed to simulate a live community where users (synthetic personas) interact based on their unique interests and dislikes. The system features:

User Panel: Interfaces for content creation and system monitoring.
Autonomous Feedback Loops: A service that optimizes user content based on historical performance.
Persona Engines: LLM-driven agents that evaluate posts to decide on likes and comments.
Real-time Analytics: Live scoring of post performance using sentiment and engagement deltas.

📁 Project Structure
The project follows a modular Python structure to separate concerns between routing, database management, and business logic:

.
├── main.py # Entry point: initializes DB and background tasks
├── requirements.txt # Project dependencies
├── app/
│ ├── config.py # Constants, API keys, and simulation weights
│ ├── database.py # SQLAlchemy engine and session management
│ ├── models.py # DB Schemas (User, Post, Like, Comment)
│ ├── tasks.py # Async background loop orchestrators
│ ├── routes/
│ │ ├── api.py # JSON endpoints (likes, comments, stats)
│ │ ├── views.py # Template rendering (Dashboard)
│ │ └── websocket.py # Real-time update broadcasting
│ └── services/
│ ├── llm.py # OpenRouter API wrapper
│ ├── stats.py # Sentiment and Engagement calculation logic
│ ├── persona.py # autonomous interaction logic (Persona Engine)
│ └── feedback_loop.py # Performance-driven content generation
└── templates/
└── index.html # Tailwind-based frontend dashboard

⚙️ Implementation Details

1. The Feedback Loop (Automated Posting)

This service manages "Growth Strategist" AI behavior. It periodically checks the performance of active users' posts:

Engagement Score: Calculated as the delta from the user's historical average:

Engagement = (likes_post - likes_avg) / likes_avg

Sentiment Score: Normalizes comment positivity using an LLM rating (0-100) divided by 100.

Ultimate Score: A weighted average of Engagement and Sentiment.

Strategy: Based on the Ultimate Score, the AI chooses an Exploration mode (trying new topics), Evolution mode (optimizing current themes), or a Contrarian Pivot to stimulate debate.

2. The Persona Engine (Autonomous Interactions)

To simulate community activity, this engine evaluates every new post against the personas of other users:

Evaluation: The LLM determines if a post aligns with a user's interests or triggers their dislikes.

Action: If a match is found, the system automatically creates a Like and generates a persona-consistent Comment (e.g., sarcastic, enthusiastic, or academic).

3. Database Seeding

The system includes a seeding service that populates the SQLite database with 20+ diverse personas ranging from "TradFi enthusiasts" to "Luddites" and "Tech Bros," each with specific interests and hatreds used by the LLM for interaction logic.

🚀 How to Run

1. Prerequisites

Ensure you have Python 3.9+ installed and an active OpenRouter API key.

2. Installation

Install the necessary packages via pip:

# Create virtual environment

python -m venv venv

# Activate venv

# On Windows:

venv\Scripts\activate

# On macOS/Linux:

source venv/bin/activate

pip install -r requirements.txt

3. Configuration

Create a .env file in the root directory with the following variables:

OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-5.1-chat
NUM_REACTORS=15
W_ENGAGEMENT=0.5
W_SENTIMENT=0.5
NUM_PAST_POSTS=5

4. Execution

run via Uvicorn directly:

uvicorn main:app --reload

Access the dashboard at http://localhost:8000. Select a user from the dropdown to view their specific post history and live performance analytics.
