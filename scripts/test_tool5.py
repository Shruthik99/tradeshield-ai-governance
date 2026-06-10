"""
Day 10 Test — Verify reliability assessment and combined tool.

Sends 1 test message (conserving rate limit):
- "Analyze NVDA with reliability check" — combined tool

Usage: python scripts/test_tool5.py
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


async def test_tool5():
    print("=" * 60)
    print("TradeShield — Day 10 Tool 5 Test")
    print("=" * 60)
    print()
    print("Testing analyze_with_reliability (1 Gemini request).")
    print()

    runner = InMemoryRunner(agent=root_agent, app_name="tradeshield")
    session = await runner.session_service.create_session(
        app_name="tradeshield",
        user_id="test_user"
    )

    message = "Analyze NVDA with a reliability check. How trustworthy is this recommendation?"

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
    print("1. Did it show a WARNING LEVEL (GREEN/YELLOW/RED)?")
    print("2. Did it show 5 dimensions (evidence, accuracy, confidence gap, drift, consistency)?")
    print("3. Did it show specific reasons for the assessment?")
    print("4. Did it ALSO show the trading analysis (decision, factors)?")
    print("5. Did it include a combined summary?")
    print()
    print("If yes: Day 10 is COMPLETE ✓")
    print("ALL 5 TOOLS ARE NOW OPERATIONAL.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tool5())
