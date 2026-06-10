"""
Day 7 Test — Verify explain_decision tool works.

Sends 1 test message (conserving rate limit):
- "Why did the model sell NVDA?" — should return traced explanation

Usage: python scripts/test_tool2.py
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


async def test_tool2():
    """Test the explain_decision tool."""

    print("=" * 60)
    print("TradeShield — Day 7 Tool 2 Test")
    print("=" * 60)
    print()
    print("Testing explain_decision (1 Gemini request).")
    print()

    runner = InMemoryRunner(agent=root_agent, app_name="tradeshield")
    session = await runner.session_service.create_session(
        app_name="tradeshield",
        user_id="test_user"
    )

    message = "Why did the model recommend selling NVDA? Show me the evidence."

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
    print("1. Did the response include traced decision history?")
    print("2. Did it show evidence lineage (data source, model version)?")
    print("3. Did it show outcomes (correct/incorrect)?")
    print("4. Did it mention accuracy for this ticker?")
    print()
    print("If yes: Day 7 is COMPLETE ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tool2())
