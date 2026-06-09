"""
TradeShield Agent — ADK Entry Point

Sets up Phoenix tracing, imports the real tools, and defines root_agent.

Run locally with: adk web .
Test with: python scripts/test_agent.py

Tool status:
- analyze_trade: REAL (Day 5) ← uses pipeline + 7-factor model
- explain_decision: placeholder (Day 7)
- audit_fairness: placeholder (Day 8)
- detect_drift: placeholder (Day 9)
- assess_reliability: placeholder (Day 10)
"""

from tradeshield.phoenix.tracing import setup_tracing

# Set up tracing BEFORE creating the agent
setup_tracing()

from google.adk.agents import Agent
from tradeshield.agent.prompt import TRADESHIELD_SYSTEM_PROMPT
from tradeshield.config import GEMINI_MODEL

# REAL tool (Day 5)
from tradeshield.agent.tools.analyze import analyze_trade


# ============================================================
# PLACEHOLDER TOOLS (replaced on Days 7-10)
# ============================================================

def system_check() -> dict:
    """Check if the TradeShield system is operational.

    Use this tool when the user asks about system status,
    health check, or whether the system is working.

    Returns:
        dict: System status information.
    """
    return {
        "status": "operational",
        "components": {
            "data_pipeline": "ready (36 stocks cached)",
            "trading_model": "ready (7 factors configured)",
            "phoenix_tracing": "connected",
            "tools": {
                "analyze_trade": "operational",
                "explain_decision": "coming Day 7",
                "audit_fairness": "coming Day 8",
                "detect_drift": "coming Day 9",
                "assess_reliability": "coming Day 10",
            }
        },
    }


def explain_decision(ticker: str) -> dict:
    """Explain why the trading model made a specific past decision.

    Queries Phoenix traces to find the decision record and provides
    a plain-English explanation with evidence lineage.

    Placeholder — full implementation on Day 7.

    Args:
        ticker: Stock ticker to explain (e.g., "NVDA")

    Returns:
        dict: Explanation with factor breakdown and evidence lineage.
    """
    return {
        "status": "placeholder",
        "ticker": ticker.upper(),
        "message": f"Explanation for {ticker.upper()} decisions will be available "
                   f"after Day 7. The analysis data is being traced to Phoenix — "
                   f"explanations will query these traces.",
    }


def audit_fairness() -> dict:
    """Check if the trading model treats all stock sectors equally.

    Queries all traced decisions, groups by sector, and calculates
    disparate impact ratios to detect potential bias.

    Placeholder — full implementation on Day 8.

    Returns:
        dict: Fairness analysis across sectors with disparate impact ratios.
    """
    return {
        "status": "placeholder",
        "message": "Fairness audit will be available after Day 8.",
    }


def detect_drift() -> dict:
    """Compare the trading model's recent behavior to past behavior.

    Queries traces from two time periods and compares decision distributions,
    confidence levels, and factor dominance.

    Placeholder — full implementation on Day 9.

    Returns:
        dict: Drift analysis comparing recent vs baseline behavior.
    """
    return {
        "status": "placeholder",
        "message": "Drift detection will be available after Day 9.",
    }


def assess_reliability(ticker: str) -> dict:
    """Assess how reliable the trading model is for a specific stock.

    Checks the model's past accuracy in similar market conditions
    before presenting a new recommendation.

    Placeholder — full implementation on Day 10.

    Args:
        ticker: Stock ticker to assess reliability for.

    Returns:
        dict: Reliability assessment with historical accuracy and warning level.
    """
    return {
        "status": "placeholder",
        "ticker": ticker.upper(),
        "message": f"Reliability assessment for {ticker.upper()} will be "
                   f"available after Day 10.",
    }


# ============================================================
# AGENT DEFINITION
# ============================================================

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
        analyze_trade,       # REAL — Day 5
        explain_decision,    # placeholder — Day 7
        audit_fairness,      # placeholder — Day 8
        detect_drift,        # placeholder — Day 9
        assess_reliability,  # placeholder — Day 10
    ],
)
