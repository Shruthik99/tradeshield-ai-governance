"""
TradeShield Agent — ADK Entry Point

Tool status:
- analyze_trade: REAL (Day 5)
- explain_decision: REAL (Day 7)
- audit_fairness: REAL (Day 8) ← NEW
- detect_drift: placeholder (Day 9)
- assess_reliability: placeholder (Day 10)
"""

from tradeshield.phoenix.tracing import setup_tracing
setup_tracing()

from google.adk.agents import Agent
from tradeshield.agent.prompt import TRADESHIELD_SYSTEM_PROMPT
from tradeshield.config import GEMINI_MODEL

# REAL tools
from tradeshield.agent.tools.analyze import analyze_trade
from tradeshield.agent.tools.explain import explain_decision
from tradeshield.agent.tools.fairness import audit_fairness


# ============================================================
# PLACEHOLDER TOOLS (replaced on Days 9-10)
# ============================================================

def system_check() -> dict:
    """Check if the TradeShield system is operational.

    Returns:
        dict: System status information.
    """
    return {
        "status": "operational",
        "tools": {
            "analyze_trade": "operational",
            "explain_decision": "operational",
            "audit_fairness": "operational",
            "detect_drift": "coming Day 9",
            "assess_reliability": "coming Day 10",
        },
        "traced_decisions": 108,
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
        "message": f"Reliability assessment for {ticker.upper()} available after Day 10.",
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
        analyze_trade,          # REAL — Day 5
        explain_decision,       # REAL — Day 7
        audit_fairness,         # REAL — Day 8
        detect_drift,           # placeholder — Day 9
        assess_reliability,     # placeholder — Day 10
    ],
)
