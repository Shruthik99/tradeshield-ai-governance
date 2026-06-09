"""
Verify agent works and traces flow to Phoenix.

This script:
1. Sets up Phoenix tracing
2. Creates the agent
3. Sends test messages
4. Verifies the agent responds correctly
5. You then check Phoenix dashboard for traces

"""

import asyncio
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Set up tracing FIRST
from tradeshield.phoenix.tracing import setup_tracing
setup_tracing()

# Import after tracing is set up
from tradeshield.agent.prompt import TRADESHIELD_SYSTEM_PROMPT
from tradeshield.config import GEMINI_MODEL


# Simple test tool
def system_check() -> dict:
    """Check if the TradeShield system is operational.

    Returns:
        dict: System status.
    """
    return {
        "status": "operational",
        "stocks_configured": 36,
        "factors": 7,
        "message": "TradeShield is operational."
    }


def analyze_trade(ticker: str) -> dict:
    """Analyze a stock using the trading model. Placeholder for Day 2.

    Args:
        ticker: Stock ticker symbol (e.g., NVDA)

    Returns:
        dict: Placeholder analysis result.
    """
    return {
        "status": "placeholder",
        "ticker": ticker.upper(),
        "message": f"Analysis for {ticker.upper()} — placeholder for Day 2 testing. "
                   f"Full implementation coming Day 5."
    }


# Create agent
agent = Agent(
    name="tradeshield",
    model=GEMINI_MODEL,
    description="TradeShield — AI governance and observability agent.",
    instruction=TRADESHIELD_SYSTEM_PROMPT,
    tools=[system_check, analyze_trade],
)


async def test_agent():
    """Run test conversations with the agent."""

    print("=" * 60)
    print("TradeShield — Day 2 Agent Test")
    print("=" * 60)
    print()

    # Create runner and session
    runner = InMemoryRunner(agent=agent, app_name="tradeshield")
    session = await runner.session_service.create_session(
        app_name="tradeshield",
        user_id="test_user"
    )

    # Test messages
    test_messages = [
        "Hello, what can you do?",
        "Analyze NVDA",
        "Can you help me buy stocks?",  # Should be refused (guardrail 1)
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"--- Test {i}: \"{message}\" ---")
        print()

        # Create user message
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)]
        )

        # Run agent
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

        print(f"Agent: {response_text}")
        print()

    print("=" * 60)
    print("TESTS COMPLETE")
    print()
    print("NOW CHECK PHOENIX:")
    print("1. Go to https://app.phoenix.arize.com")
    print("2. Open your space (shruthikashetty2309)")
    print("3. Click 'Tracing' in the left sidebar")
    print("4. You should see 3 traces (one per test message)")
    print()
    print("If traces appear: Day 2 is COMPLETE ✓")
    print("If no traces: check your PHOENIX_API_KEY and endpoint in .env")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_agent())
