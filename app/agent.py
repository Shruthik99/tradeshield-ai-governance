"""
TradeShield Agent — ADK Web Entry Point

This file is discovered by `adk web .` command.
Run: adk web . (from project root)
Then open: http://localhost:8000 in browser

This is a thin wrapper that:
1. Sets up Phoenix tracing
2. Imports the system prompt from tradeshield package
3. Defines placeholder tools (replaced with real ones on Days 5-10)
4. Creates root_agent (required by ADK discovery)
"""

from tradeshield.phoenix.tracing import setup_tracing
setup_tracing()

from google.adk.agents import Agent
from tradeshield.agent.prompt import TRADESHIELD_SYSTEM_PROMPT
from tradeshield.config import GEMINI_MODEL


def system_check() -> dict:
    """Check if the TradeShield system is operational.

    Returns:
        dict: System status information.
    """
    return {
        "status": "operational",
        "stocks_configured": 36,
        "factors": 7,
    }


def analyze_trade(ticker: str) -> dict:
    """Analyze a stock using the trading model and real market data.

    Args:
        ticker: Stock ticker symbol (e.g., NVDA, AAPL)

    Returns:
        dict: Trading model decision with factor breakdown.
    """
    return {
        "status": "placeholder",
        "ticker": ticker.upper(),
        "message": f"Full analysis for {ticker.upper()} available after Day 5."
    }


def explain_decision(ticker: str) -> dict:
    """Explain why the trading model made a specific past decision.

    Args:
        ticker: Stock ticker to explain.

    Returns:
        dict: Explanation with evidence lineage.
    """
    return {
        "status": "placeholder",
        "ticker": ticker.upper(),
        "message": f"Explanations available after Day 7."
    }


def audit_fairness() -> dict:
    """Check if the trading model treats all stock sectors equally.

    Returns:
        dict: Fairness analysis with disparate impact ratios.
    """
    return {
        "status": "placeholder",
        "message": "Fairness audit available after Day 8."
    }


def detect_drift() -> dict:
    """Compare the model's recent behavior to past behavior.

    Returns:
        dict: Drift analysis comparing time periods.
    """
    return {
        "status": "placeholder",
        "message": "Drift detection available after Day 9."
    }


def assess_reliability(ticker: str) -> dict:
    """Assess the model's reliability for a specific stock.

    Args:
        ticker: Stock ticker to assess.

    Returns:
        dict: Reliability assessment with warning level.
    """
    return {
        "status": "placeholder",
        "ticker": ticker.upper(),
        "message": f"Reliability assessment available after Day 10."
    }


root_agent = Agent(
    name="tradeshield",
    model=GEMINI_MODEL,
    description=(
        "TradeShield — Operational observability for AI-assisted "
        "financial trading decisions."
    ),
    instruction=TRADESHIELD_SYSTEM_PROMPT,
    tools=[
        system_check,
        analyze_trade,
        explain_decision,
        audit_fairness,
        detect_drift,
        assess_reliability,
    ],
)
