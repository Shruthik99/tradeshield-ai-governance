"""
TradeShield API — FastAPI wrapper for the ADK agent.

Provides a simple /chat endpoint for the frontend.
Includes CORS middleware for local development.

Usage: uvicorn api:app --reload --port 8000
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import root_agent

app = FastAPI(title="TradeShield API", version="1.0")

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# ADK runner + session (created once)
runner = None
session = None


async def get_runner():
    global runner, session
    if runner is None:
        runner = InMemoryRunner(agent=root_agent, app_name="tradeshield")
        session = await runner.session_service.create_session(
            app_name="tradeshield",
            user_id="web_user"
        )
    return runner, session


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "TradeShield API is running. Frontend not found at /frontend/index.html"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the TradeShield agent and get a response."""
    r, s = await get_runner()

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=request.message)]
    )

    response_text = ""
    async for event in r.run_async(
        user_id="web_user",
        session_id=s.id,
        new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    if not response_text:
        response_text = "I couldn't generate a response. Please try again."

    return ChatResponse(response=response_text)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "tradeshield", "tools": 7}
