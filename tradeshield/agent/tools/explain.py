"""
Tool 2: Explain Decision

Queries Phoenix traces to find a past trading decision and provides
a plain-English explanation with evidence lineage.

Evidence lineage = shows WHERE the data came from, WHEN the decision
was made, WHAT model version was used, and WHAT the outcome was.

This is the explainability primitive — translates AI decision factors
into structured explanations that compliance officers can understand.
"""

import logging
from tradeshield.phoenix.client import query_by_ticker, get_accuracy_by_decision
from tradeshield.config import SEEDED_TICKERS

logger = logging.getLogger("tradeshield.tools")


def explain_decision(ticker: str) -> dict:
    """Explain why the trading model made a specific past decision for a stock.

    Queries traced decisions in Arize Phoenix to find all historical
    records for the given ticker. Returns a plain-English explanation
    with full evidence lineage showing data source, trace timestamps,
    model version, and actual outcome.

    Use this tool when the user asks things like:
    - "Why did the model sell NVDA?"
    - "Explain the AAPL decision"
    - "What happened with TSLA?"
    - "Show me the evidence for the JPM recommendation"

    Args:
        ticker: Stock ticker symbol to explain (e.g., "NVDA", "AAPL").
                Case-insensitive.

    Returns:
        dict: Explanation with factor breakdown, evidence lineage,
              and outcome data for each traced decision.
    """
    ticker = ticker.upper().strip()

    # Query Phoenix for all traced decisions for this ticker
    traces = query_by_ticker(ticker)

    if not traces:
        # Check if ticker is in our seeded list
        if ticker in SEEDED_TICKERS:
            return {
                "error": True,
                "message": f"No traced decisions found for {ticker}. "
                           f"The seed data may need to be regenerated. "
                           f"Try running the seed script first.",
            }
        else:
            return {
                "error": True,
                "message": f"No traced decisions found for {ticker}. "
                           f"This ticker hasn't been analyzed in historical runs. "
                           f"Would you like me to analyze it now instead?",
            }

    # Get decision type accuracy for context
    decision_accuracy = get_accuracy_by_decision()

    # Build explanations for each traced decision
    explanations = []
    for trace in traces:
        decision = trace.get("decision", "UNKNOWN")
        confidence = trace.get("confidence", 0)
        composite = trace.get("composite", 0)
        window = trace.get("window", "unknown")
        date = trace.get("date", "unknown")
        outcome = trace.get("outcome", "unknown")
        correct = trace.get("correct")
        price_change = trace.get("price_change")

        # Build outcome string
        if outcome == "correct":
            outcome_str = f"CORRECT — price moved as predicted ({price_change:+.1f}%)"
        elif outcome == "incorrect":
            outcome_str = f"INCORRECT — price moved opposite to prediction ({price_change:+.1f}%)"
        else:
            outcome_str = "UNKNOWN — outcome not yet available"

        # Decision type accuracy context
        dec_acc = decision_accuracy.get(decision, {})
        type_accuracy = dec_acc.get("accuracy", 0)
        type_total = dec_acc.get("total", 0)

        explanations.append({
            "time_period": window.replace("_", " "),
            "decision_date": date,
            "decision": decision,
            "confidence": confidence,
            "composite_score": composite,
            "outcome": outcome_str,
            "decision_type_accuracy": f"{decision} signals are {type_accuracy}% accurate "
                                      f"across {type_total} historical decisions",
            "evidence_lineage": {
                "data_source": "Yahoo Finance via yfinance (public market data)",
                "model_version": "7-factor scorer v1.0",
                "factors": "momentum, value, quality, volatility, "
                          "relative_strength, mean_reversion, volume",
                "trace_location": "Arize Phoenix Cloud (tradeshield project)",
                "decision_timestamp": date,
                "outcome_window": "5 trading days after decision",
            },
        })

    # Summary across all time periods
    total = len(traces)
    correct_count = sum(1 for t in traces if t.get("correct"))
    incorrect_count = sum(1 for t in traces if t.get("correct") is False)
    ticker_accuracy = round(correct_count / total * 100, 1) if total > 0 else 0

    response = {
        "ticker": ticker,
        "sector": traces[0].get("sector", "unknown"),
        "total_traced_decisions": total,
        "summary": {
            "correct": correct_count,
            "incorrect": incorrect_count,
            "accuracy": f"{ticker_accuracy}%",
            "observation": _generate_observation(ticker, traces, ticker_accuracy),
        },
        "decisions": explanations,
        "note": "Evidence lineage shows the complete provenance chain "
                "for each decision — from data source through model "
                "version to traced outcome.",
    }

    logger.info(
        f"tools.explain | ticker={ticker} | traces={total} | "
        f"accuracy={ticker_accuracy}% | status=complete"
    )

    return response


def _generate_observation(ticker: str, traces: list, accuracy: float) -> str:
    """Generate a plain-English observation about the ticker's trace history."""

    decisions = [t.get("decision") for t in traces]
    outcomes = [t.get("outcome") for t in traces]

    # Check for consistency
    unique_decisions = set(decisions)
    if len(unique_decisions) == 1:
        consistency = f"The model consistently recommended {decisions[0]} across all time periods."
    else:
        consistency = (
            f"The model's recommendation changed across time periods: "
            f"{', '.join(decisions)}."
        )

    # Check accuracy trend
    if accuracy > 50:
        reliability = f"The model has been relatively reliable for {ticker} ({accuracy}% accuracy)."
    elif accuracy > 25:
        reliability = f"The model has mixed results for {ticker} ({accuracy}% accuracy)."
    else:
        reliability = (
            f"The model has been unreliable for {ticker} ({accuracy}% accuracy). "
            f"Recommendations for this stock should be treated with extra caution."
        )

    return f"{consistency} {reliability}"
