"""
Day 9 Test — Verify detect_drift tool works.

Sends 1 test message (conserving rate limit):
- "Has the model's behavior changed recently?"

Usage: python scripts/test_tool4.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app.agent import root_agent


async def test_tool4():
    print("=" * 60)
    print("TradeShield — Day 9 Tool 4 Test")
    print("=" * 60)
    print()
    print("Testing detect_drift (1 Gemini request).")
    print()

    runner = InMemoryRunner(agent=root_agent, app_name="tradeshield")
    session = await runner.session_service.create_session(
        app_name="tradeshield",
        user_id="test_user"
    )

    message = "Has the model's behavior changed recently? Detect any drift."

    print(f"--- Test: \"{message}\" ---")
    print()

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)]
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    print(f"Agent response:\n{response_text}")
    print()
    print("=" * 60)
    print("CHECK:")
    print("1. Did it compare 3 time periods?")
    print("2. Did it show changes in accuracy (11.1% → 30.6%)?")
    print("3. Did it flag significant changes (>15%)?")
    print("4. Did it provide a trend assessment?")
    print()
    print("If yes: Day 9 is COMPLETE ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tool4())
