"""
Day 8 Test — Verify audit_fairness tool works.

Sends 1 test message (conserving rate limit):
- "Is the model fair across sectors?" — should return disparate impact analysis

Usage: python scripts/test_tool3.py
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


async def test_tool3():
    print("=" * 60)
    print("TradeShield — Day 8 Tool 3 Test")
    print("=" * 60)
    print()
    print("Testing audit_fairness (1 Gemini request).")
    print()

    runner = InMemoryRunner(agent=root_agent, app_name="tradeshield")
    session = await runner.session_service.create_session(
        app_name="tradeshield",
        user_id="test_user"
    )

    message = "Is the model fair across sectors? Check for bias."

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
    print("1. Did it show per-sector stats (accuracy, BUY/SELL/HOLD rates)?")
    print("2. Did it calculate disparate impact ratios?")
    print("3. Did it flag sectors below 0.80 threshold?")
    print("4. Did it include the caveat about simplified comparison?")
    print()
    print("If yes: Day 8 is COMPLETE ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tool3())
