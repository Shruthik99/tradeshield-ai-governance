"""
Tool 5: Reliability Assessment

The most important governance primitive. Evaluates historical
accuracy BEFORE presenting a new recommendation.

Evaluates 5 dimensions:
1. Evidence coverage — sufficient or sparse historical data?
2. Past accuracy — what % of similar decisions were correct?
3. Confidence gap — stated confidence vs actual track record
4. Drift signal — has behavior shifted recently?
5. Pattern consistency — were similar cases treated consistently?

Assigns: GREEN (>70%), YELLOW (50-70%), RED (<50%), INSUFFICIENT_DATA

Also contains the combined analyze_with_reliability tool that
runs BOTH reliability check and analysis in one call.

This implements Arize's "self-improving agent" feedback loop:
the agent queries its own historical traces to evaluate its
own reliability before presenting results.
"""

import logging
from tradeshield.config import (
    RELIABILITY_GREEN_THRESHOLD,
    RELIABILITY_YELLOW_THRESHOLD,
    MIN_SIMILAR_TRACES,
    SUFFICIENT_EVIDENCE_COUNT,
    SECTOR_MAP,
)
from tradeshield.phoenix.client import (
    query_by_ticker,
    query_by_sector,
    query_by_conditions,
    get_accuracy_by_sector,
    get_accuracy_by_decision,
    get_accuracy_by_window,
)
from tradeshield.agent.tools.analyze import analyze_trade

logger = logging.getLogger("tradeshield.tools")


def assess_reliability(ticker: str) -> dict:
    """Assess how reliable the trading model is for a specific stock.

    Queries historical traced decisions to evaluate the model's
    track record in similar conditions. Checks past accuracy,
    evidence coverage, confidence calibration, drift signals,
    and pattern consistency before presenting a recommendation.

    Returns a warning level (GREEN/YELLOW/RED) with specific
    reasons for the assessment.

    Use this tool when the user asks things like:
    - "How reliable is the model for tech stocks?"
    - "Should I trust this recommendation?"
    - "Check accuracy for NVDA"
    - "What's the model's track record?"

    Args:
        ticker: Stock ticker to assess reliability for (e.g., "NVDA").

    Returns:
        dict: Reliability assessment with 5 dimensions, warning level,
              and specific reasons.
    """
    ticker = ticker.upper().strip()
    sector = SECTOR_MAP.get(ticker, "unknown")

    # 1. Find traces for this specific ticker
    ticker_traces = query_by_ticker(ticker)

    # 2. Find traces for the same sector (broader evidence base)
    sector_traces = query_by_sector(sector)

    # 3. Evaluate 5 dimensions
    evidence = _evaluate_evidence_coverage(ticker_traces, sector_traces, ticker, sector)
    accuracy = _evaluate_past_accuracy(ticker_traces, sector_traces, ticker, sector)
    confidence_gap = _evaluate_confidence_gap(ticker_traces, sector_traces)
    drift = _evaluate_drift_signal(sector_traces)
    consistency = _evaluate_pattern_consistency(ticker_traces, sector_traces)

    # 4. Determine warning level
    warning_level, reasons = _determine_warning_level(
        evidence, accuracy, confidence_gap, drift, consistency, ticker
    )

    response = {
        "ticker": ticker,
        "sector": sector,
        "similar_traces_ticker": len(ticker_traces),
        "similar_traces_sector": len(sector_traces),
        "dimensions": {
            "evidence_coverage": evidence,
            "past_accuracy": accuracy,
            "confidence_gap": confidence_gap,
            "drift_signal": drift,
            "pattern_consistency": consistency,
        },
        "warning_level": warning_level,
        "specific_reasons": reasons,
        "recommendation": _generate_recommendation(warning_level, reasons),
        "caveat": (
            "Thresholds are heuristic baselines for demonstration. "
            "Production deployment would calibrate against institutional "
            "risk tolerance."
        ),
    }

    logger.info(
        f"tools.reliability | ticker={ticker} | sector={sector} | "
        f"warning={warning_level} | reasons={len(reasons)} | status=complete"
    )

    return response


def analyze_with_reliability(ticker: str) -> dict:
    """Analyze a stock AND check reliability in one combined call.

    Runs the reliability assessment first, then the analysis.
    Returns both results together. This is more reliable than
    depending on Gemini to chain two separate tool calls.

    Use this tool when the user asks things like:
    - "Analyze NVDA with reliability check"
    - "Give me a full assessment of AAPL"
    - "Analyze and check reliability for TSLA"

    Args:
        ticker: Stock ticker to analyze and assess.

    Returns:
        dict: Combined reliability assessment + trading analysis.
    """
    ticker = ticker.upper().strip()

    # Run reliability FIRST
    reliability = assess_reliability(ticker)

    # Then run analysis
    analysis = analyze_trade(ticker)

    response = {
        "reliability_assessment": reliability,
        "analysis": analysis,
        "combined_summary": _generate_combined_summary(reliability, analysis),
    }

    logger.info(
        f"tools.combined | ticker={ticker} | "
        f"warning={reliability.get('warning_level')} | "
        f"decision={analysis.get('decision', 'N/A')} | status=complete"
    )

    return response


# ============================================================
# DIMENSION EVALUATORS
# ============================================================

def _evaluate_evidence_coverage(ticker_traces, sector_traces, ticker, sector):
    """Dimension 1: Do we have enough historical data?"""
    ticker_count = len(ticker_traces)
    sector_count = len(sector_traces)

    if ticker_count >= SUFFICIENT_EVIDENCE_COUNT:
        level = "sufficient"
        detail = f"{ticker_count} traced decisions for {ticker} — strong evidence base"
    elif ticker_count >= MIN_SIMILAR_TRACES:
        level = "sparse"
        detail = (
            f"{ticker_count} traced decisions for {ticker} "
            f"(+{sector_count} for {sector} sector) — limited but usable"
        )
    else:
        level = "insufficient"
        detail = (
            f"Only {ticker_count} traced decisions for {ticker}. "
            f"Using {sector_count} sector-level traces as supplementary evidence."
        )

    return {"level": level, "detail": detail, "ticker_count": ticker_count, "sector_count": sector_count}


def _evaluate_past_accuracy(ticker_traces, sector_traces, ticker, sector):
    """Dimension 2: How accurate were past predictions?"""
    # Ticker-level accuracy
    ticker_known = [t for t in ticker_traces if t.get("correct") is not None]
    ticker_correct = sum(1 for t in ticker_known if t.get("correct"))
    ticker_accuracy = (ticker_correct / len(ticker_known) * 100) if ticker_known else None

    # Sector-level accuracy
    sector_known = [t for t in sector_traces if t.get("correct") is not None]
    sector_correct = sum(1 for t in sector_known if t.get("correct"))
    sector_accuracy = (sector_correct / len(sector_known) * 100) if sector_known else None

    # Use ticker accuracy if enough data, otherwise sector
    if ticker_known and len(ticker_known) >= MIN_SIMILAR_TRACES:
        primary_accuracy = round(ticker_accuracy, 1)
        source = f"{ticker} ({len(ticker_known)} decisions)"
    elif sector_known:
        primary_accuracy = round(sector_accuracy, 1)
        source = f"{sector} sector ({len(sector_known)} decisions)"
    else:
        primary_accuracy = None
        source = "no data"

    return {
        "ticker_accuracy": round(ticker_accuracy, 1) if ticker_accuracy else None,
        "sector_accuracy": round(sector_accuracy, 1) if sector_accuracy else None,
        "primary_accuracy": primary_accuracy,
        "source": source,
        "detail": f"Historical accuracy: {primary_accuracy}% based on {source}"
        if primary_accuracy else "No historical accuracy data available",
    }


def _evaluate_confidence_gap(ticker_traces, sector_traces):
    """Dimension 3: Does stated confidence match actual accuracy?"""
    # Use whichever set has more data
    traces = ticker_traces if len(ticker_traces) >= MIN_SIMILAR_TRACES else sector_traces
    known = [t for t in traces if t.get("correct") is not None]

    if not known:
        return {"gap": None, "detail": "Insufficient data for confidence calibration"}

    avg_confidence = sum(t.get("confidence", 0) for t in known) / len(known)
    actual_accuracy = sum(1 for t in known if t.get("correct")) / len(known) * 100

    gap = round(avg_confidence - actual_accuracy, 1)

    if gap > 20:
        assessment = "severely overconfident"
    elif gap > 10:
        assessment = "moderately overconfident"
    elif gap > 0:
        assessment = "slightly overconfident"
    elif gap > -10:
        assessment = "well-calibrated"
    else:
        assessment = "underconfident"

    return {
        "avg_stated_confidence": round(avg_confidence, 1),
        "actual_accuracy": round(actual_accuracy, 1),
        "gap": gap,
        "assessment": assessment,
        "detail": (
            f"Model states {avg_confidence:.0f}% confidence but achieves "
            f"{actual_accuracy:.0f}% accuracy — {assessment} "
            f"(gap: {gap:+.1f} points)"
        ),
    }


def _evaluate_drift_signal(sector_traces):
    """Dimension 4: Has the model's behavior shifted recently?"""
    # Split by time window
    early = [t for t in sector_traces if t.get("window") == "2_months_ago"]
    recent = [t for t in sector_traces if t.get("window") == "1_week_ago"]

    if not early or not recent:
        return {"signal": "unknown", "detail": "Insufficient data for drift assessment"}

    # Compare accuracy
    early_known = [t for t in early if t.get("correct") is not None]
    recent_known = [t for t in recent if t.get("correct") is not None]

    if not early_known or not recent_known:
        return {"signal": "unknown", "detail": "Insufficient outcome data for drift"}

    early_acc = sum(1 for t in early_known if t.get("correct")) / len(early_known) * 100
    recent_acc = sum(1 for t in recent_known if t.get("correct")) / len(recent_known) * 100
    change = recent_acc - early_acc

    if abs(change) < 10:
        signal = "stable"
        detail = f"Accuracy stable: {early_acc:.0f}% → {recent_acc:.0f}% ({change:+.0f}pp)"
    elif change > 0:
        signal = "improving"
        detail = f"Accuracy improving: {early_acc:.0f}% → {recent_acc:.0f}% ({change:+.0f}pp)"
    else:
        signal = "degrading"
        detail = f"Accuracy degrading: {early_acc:.0f}% → {recent_acc:.0f}% ({change:+.0f}pp)"

    return {
        "signal": signal,
        "early_accuracy": round(early_acc, 1),
        "recent_accuracy": round(recent_acc, 1),
        "change": round(change, 1),
        "detail": detail,
    }


def _evaluate_pattern_consistency(ticker_traces, sector_traces):
    """Dimension 5: Were similar cases treated consistently?"""
    traces = ticker_traces if len(ticker_traces) >= MIN_SIMILAR_TRACES else sector_traces

    if len(traces) < 2:
        return {"consistency": "unknown", "detail": "Too few traces for consistency check"}

    decisions = [t.get("decision") for t in traces]
    composites = [t.get("composite", 0) for t in traces]

    unique_decisions = set(decisions)
    decision_count = len(decisions)

    # Check if decisions are consistent
    most_common = max(set(decisions), key=decisions.count)
    most_common_pct = decisions.count(most_common) / decision_count * 100

    # Check composite score variance
    if composites:
        avg_comp = sum(composites) / len(composites)
        variance = sum((c - avg_comp) ** 2 for c in composites) / len(composites)
    else:
        variance = 0

    if most_common_pct >= 80:
        consistency = "consistent"
        detail = (
            f"Model consistently recommends {most_common} "
            f"({most_common_pct:.0f}% of decisions)"
        )
    elif most_common_pct >= 60:
        consistency = "mostly_consistent"
        detail = (
            f"Model leans toward {most_common} ({most_common_pct:.0f}%) "
            f"but shows some variation across {len(unique_decisions)} decision types"
        )
    else:
        consistency = "inconsistent"
        detail = (
            f"Model shows mixed signals: {', '.join(f'{d}={decisions.count(d)}' for d in unique_decisions)}. "
            f"No clear dominant pattern."
        )

    return {
        "consistency": consistency,
        "dominant_decision": most_common,
        "dominant_pct": round(most_common_pct, 1),
        "unique_decisions": len(unique_decisions),
        "detail": detail,
    }


# ============================================================
# WARNING LEVEL DETERMINATION
# ============================================================

def _determine_warning_level(evidence, accuracy, conf_gap, drift, consistency, ticker):
    """Combine all 5 dimensions into a warning level."""
    reasons = []
    score = 0  # Higher = better

    # Evidence coverage
    if evidence["level"] == "sufficient":
        score += 2
    elif evidence["level"] == "sparse":
        score += 1
        reasons.append(f"Limited historical data for {ticker}")
    else:
        reasons.append(f"Insufficient historical data for {ticker} — reliability unknown")
        return "INSUFFICIENT_DATA", reasons

    # Past accuracy
    acc = accuracy.get("primary_accuracy")
    if acc is not None:
        if acc >= RELIABILITY_GREEN_THRESHOLD * 100:
            score += 3
        elif acc >= RELIABILITY_YELLOW_THRESHOLD * 100:
            score += 1
            reasons.append(f"Moderate accuracy ({acc}%) — below green threshold")
        else:
            reasons.append(f"Low accuracy ({acc}%) — model has been unreliable in similar conditions")
    else:
        reasons.append("No accuracy data available")

    # Confidence gap
    gap = conf_gap.get("gap")
    if gap is not None:
        if gap > 20:
            reasons.append(
                f"Severely overconfident: states {conf_gap['avg_stated_confidence']:.0f}% "
                f"but achieves {conf_gap['actual_accuracy']:.0f}%"
            )
        elif gap > 10:
            score += 1
            reasons.append(
                f"Moderately overconfident (gap: {gap:+.1f} points)"
            )
        else:
            score += 2

    # Drift signal
    drift_signal = drift.get("signal")
    if drift_signal == "stable":
        score += 2
    elif drift_signal == "improving":
        score += 1
        reasons.append("Model behavior is shifting (improving) — monitor closely")
    elif drift_signal == "degrading":
        reasons.append("Model accuracy is DEGRADING — increased risk")

    # Pattern consistency
    cons = consistency.get("consistency")
    if cons == "consistent":
        score += 2
    elif cons == "mostly_consistent":
        score += 1
    else:
        reasons.append("Inconsistent decision patterns — model gives mixed signals")

    # Determine level (max possible score = 11)
    if score >= 8:
        level = "GREEN"
        if not reasons:
            reasons.append("Strong historical track record with consistent patterns")
    elif score >= 5:
        level = "YELLOW"
        if not reasons:
            reasons.append("Some concerns but within acceptable range")
    else:
        level = "RED"
        if not reasons:
            reasons.append("Multiple reliability concerns identified")

    return level, reasons


def _generate_recommendation(warning_level, reasons):
    """Generate a governance recommendation based on warning level."""
    if warning_level == "GREEN":
        return (
            "Historical evidence supports this recommendation. "
            "Standard review process appropriate."
        )
    elif warning_level == "YELLOW":
        return (
            "Some reliability concerns noted. Consider additional "
            "review before acting on this recommendation."
        )
    elif warning_level == "RED":
        return (
            "Significant reliability concerns. This recommendation "
            "should be flagged for senior review before any action."
        )
    else:
        return (
            "Insufficient historical evidence to assess reliability. "
            "Treat this as an unvalidated signal requiring human judgment."
        )


def _generate_combined_summary(reliability, analysis):
    """Generate summary for the combined analyze+reliability response."""
    warning = reliability.get("warning_level", "UNKNOWN")
    decision = analysis.get("decision", "N/A")
    confidence = analysis.get("confidence", "N/A")
    ticker = analysis.get("ticker", "N/A")

    if warning == "GREEN":
        return (
            f"The model recommends {decision} for {ticker} at {confidence}% "
            f"confidence. Historical reliability is GREEN — the model has "
            f"performed adequately in similar conditions."
        )
    elif warning == "YELLOW":
        return (
            f"The model recommends {decision} for {ticker} at {confidence}% "
            f"confidence, but reliability is YELLOW. Review the specific "
            f"concerns before acting on this recommendation."
        )
    elif warning == "RED":
        return (
            f"The model recommends {decision} for {ticker} at {confidence}% "
            f"confidence, but reliability is RED. The model has been "
            f"unreliable in similar conditions. Flag for senior review."
        )
    else:
        return (
            f"The model recommends {decision} for {ticker} at {confidence}% "
            f"confidence, but there is insufficient historical data to "
            f"assess reliability. Treat as unvalidated."
        )
