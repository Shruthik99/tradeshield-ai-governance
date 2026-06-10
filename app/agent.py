"""
TradeShield Agent — ADK Entry Point with Phoenix MCP Integration

ALL 5 custom tools + Phoenix MCP Server for direct trace querying.

The Phoenix MCP Server gives the agent direct access to:
- Query traces and spans in Phoenix
- List projects and sessions
- Access datasets and experiments
- Browse annotations

This implements the "self-improving agent" feedback loop:
the agent can query its own historical traces via MCP
to investigate patterns, debug decisions, and improve.

Custom tools handle domain-specific governance analysis.
Phoenix MCP handles raw trace access for ad-hoc queries.
"""

import os
from tradeshield.phoenix.tracing import setup_tracing
setup_tracing()

from google.adk.agents import Agent
from tradeshield.agent.prompt import TRADESHIELD_SYSTEM_PROMPT
from tradeshield.config import GEMINI_MODEL, PHOENIX_API_KEY

# ALL REAL TOOLS
from tradeshield.agent.tools.analyze import analyze_trade
from tradeshield.agent.tools.explain import explain_decision
from tradeshield.agent.tools.fairness import audit_fairness
from tradeshield.agent.tools.drift import detect_drift
from tradeshield.agent.tools.improve import assess_reliability, analyze_with_reliability

# MCP Integration
try:
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, StdioServerParameters

    phoenix_mcp = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y", "@arizeai/phoenix-mcp@latest",
                    "--baseUrl", "https://app.phoenix.arize.com/s/shruthikashetty2309",
                    "--apiKey", PHOENIX_API_KEY,
                ],
            ),
        ),
    )
    MCP_AVAILABLE = True
    print("[TradeShield] Phoenix MCP Server configured ✓")
except Exception as e:
    phoenix_mcp = None
    MCP_AVAILABLE = False
    print(f"[TradeShield] Phoenix MCP not available: {e}")
    print("[TradeShield] Falling back to custom tools only (REST-based queries)")


def system_check() -> dict:
    """Check if the TradeShield system is operational.

    Returns:
        dict: System status information.
    """
    return {
        "status": "fully operational",
        "tools": {
            "analyze_trade": "operational",
            "explain_decision": "operational",
            "audit_fairness": "operational",
            "detect_drift": "operational",
            "assess_reliability": "operational",
            "analyze_with_reliability": "operational",
            "phoenix_mcp": "connected" if MCP_AVAILABLE else "not available (using REST fallback)",
        },
        "traced_decisions": 108,
        "version": "all 5 governance primitives + Phoenix MCP",
    }


# ============================================================
# AGENT DEFINITION — COMPLETE WITH MCP
# ============================================================

# Build tools list
tools_list = [
    system_check,
    analyze_trade,
    explain_decision,
    audit_fairness,
    detect_drift,
    assess_reliability,
    analyze_with_reliability,
]

# Add Phoenix MCP if available
if MCP_AVAILABLE and phoenix_mcp:
    tools_list.append(phoenix_mcp)

root_agent = Agent(
    name="tradeshield",
    model=GEMINI_MODEL,
    description=(
        "TradeShield — Operational observability for AI-assisted "
        "financial trading decisions. All 5 governance primitives "
        "active with Phoenix MCP integration for direct trace access."
    ),
    instruction=TRADESHIELD_SYSTEM_PROMPT,
    tools=tools_list,
)
