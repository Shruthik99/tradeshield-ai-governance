"""
Verify real analyze_trade tool works end-to-end.

Sends 2 test messages (conserving Gemini rate limit — 20/day):
1. "Analyze NVDA" — should return REAL analysis with 7 factors
2. "Analyze BANANA" — should handle invalid ticker gracefully

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

# Import agent (this also sets up tracing)
from app.agent import root_agent


async def test_tool1():
    """Test the real analyze_trade tool."""

    print("=" * 60)
    print("TradeShield — Day 5 Tool 1 Test")
    print("=" * 60)
    print()
    print("Testing REAL analyze_trade (not placeholder).")
    print("Uses 2 Gemini requests. Rate limit: 20/day.")
    print()

    runner = InMemoryRunner(agent=root_agent, app_name="tradeshield")
    session = await runner.session_service.create_session(
        app_name="tradeshield",
        user_id="test_user"
    )

    test_messages = [
        ("Analyze NVDA", "Should return real 7-factor analysis"),
        ("Analyze BANANA", "Should handle invalid ticker gracefully"),
    ]

    for message, expected in test_messages:
        print(f"--- Test: \"{message}\" ---")
        print(f"Expected: {expected}")
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
        print("-" * 60)
        print()

    print("=" * 60)
    print("DAY 5 TESTS COMPLETE")
    print()
    print("CHECK:")
    print("1. Did 'Analyze NVDA' show real factor scores?")
    print("   (momentum, value, quality, etc. — not 'placeholder')")
    print("2. Did 'Analyze BANANA' show a graceful error?")
    print("3. Check Phoenix — new traces should appear")
    print()
    print("If all pass: Day 5 is COMPLETE ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tool1())
