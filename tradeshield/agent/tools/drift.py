"""
Tool 4: Detect Drift

Compares the trading model's behavior across time periods.
Tracks changes in decision distribution, confidence, accuracy,
and recommendation patterns. Flags changes exceeding 15%.

Drift detection answers: "Has the model's behavior changed?"
This is critical for governance because a model that performed
well last month might be performing poorly now — and nobody
notices without monitoring.
"""

import logging
from tradeshield.phoenix.client import query_by_window, get_all_traces

logger = logging.getLogger("tradeshield.tools")

# Available time windows from seeded data
VALID_WINDOWS = ["2_months_ago", "1_month_ago", "1_week_ago"]
DRIFT_THRESHOLD = 0.15  # 15% change = flagged


def detect_drift() -> dict:
    """Compare the trading model's recent behavior to past behavior.

    Queries traced decisions from different time periods and compares
    decision distributions, confidence levels, accuracy rates, and
    recommendation patterns. Flags any metric that changed by more
    than 15% between periods.

    Compares three time periods: 2 months ago, 1 month ago, and
    1 week ago to show how the model's behavior evolved.

    Use this tool when the user asks things like:
    - "Has the model changed?"
    - "Detect drift"
    - "Compare this month to last month"
    - "Is the model's behavior different?"
    - "Any behavioral changes?"

    Returns:
        dict: Drift analysis with per-period stats, changes,
              flags for significant shifts, and trend assessment.
    """
    all_traces = get_all_traces()
    if not all_traces:
        return {
            "error": True,
            "message": "No traced decisions found. Run the seed script first.",
        }

    # Get traces for each time window
    periods = {}
    for window in VALID_WINDOWS:
        traces = query_by_window(window)
        if traces:
            periods[window] = _calculate_period_stats(window, traces)

    if len(periods) < 2:
        return {
            "error": True,
            "message": "Need at least 2 time periods for drift detection. "
                       "Only found data for: " + ", ".join(periods.keys()),
        }

    # Calculate changes between consecutive periods
    period_keys = [w for w in VALID_WINDOWS if w in periods]
    changes = []
    flags = []

    for i in range(len(period_keys) - 1):
        earlier = period_keys[i]
        later = period_keys[i + 1]
        comparison = _compare_periods(
            periods[earlier], periods[later], earlier, later
        )
        changes.append(comparison)
        flags.extend(comparison["flags"])

    # Overall drift between earliest and latest
    if len(period_keys) >= 2:
        overall = _compare_periods(
            periods[period_keys[0]],
            periods[period_keys[-1]],
            period_keys[0],
            period_keys[-1],
        )
    else:
        overall = changes[0] if changes else {}

    # Trend assessment
    assessment = _assess_drift(periods, flags)

    response = {
        "periods_analyzed": len(periods),
        "period_stats": {k: v for k, v in periods.items()},
        "period_comparisons": changes,
        "overall_drift": overall,
        "flags": flags,
        "assessment": assessment,
        "drift_threshold": f"{DRIFT_THRESHOLD:.0%}",
        "note": "Drift detection compares decision patterns across time "
                "periods. Significant changes may indicate market regime "
                "shifts, model instability, or data quality issues.",
    }

    logger.info(
        f"tools.drift | periods={len(periods)} | "
        f"flags={len(flags)} | status=complete"
    )

    return response


def _calculate_period_stats(window: str, traces: list) -> dict:
    """Calculate statistics for a single time period."""
    total = len(traces)
    decisions = [t.get("decision") for t in traces]
    correct = sum(1 for t in traces if t.get("correct"))
    confidences = [t.get("confidence", 0) for t in traces]

    buy_count = decisions.count("BUY")
    sell_count = decisions.count("SELL")
    hold_count = decisions.count("HOLD")

    # Find dominant factor (most common top contributor)
    # We don't have factor-level data in seed_results, so use composite direction
    positive_composites = sum(1 for t in traces if t.get("composite", 0) > 0)
    negative_composites = sum(1 for t in traces if t.get("composite", 0) < 0)

    avg_composite = sum(t.get("composite", 0) for t in traces) / total if total > 0 else 0

    return {
        "window": window.replace("_", " "),
        "trace_count": total,
        "buy_rate": round(buy_count / total, 3) if total > 0 else 0,
        "sell_rate": round(sell_count / total, 3) if total > 0 else 0,
        "hold_rate": round(hold_count / total, 3) if total > 0 else 0,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "hold_count": hold_count,
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
        "avg_confidence": round(sum(confidences) / total, 1) if total > 0 else 0,
        "avg_composite": round(avg_composite, 3),
        "bullish_ratio": round(positive_composites / total, 3) if total > 0 else 0,
    }


def _compare_periods(earlier: dict, later: dict,
                     earlier_label: str, later_label: str) -> dict:
    """Compare two time periods and identify significant changes."""
    changes = {}
    flags = []

    metrics_to_compare = [
        ("buy_rate", "BUY rate"),
        ("sell_rate", "SELL rate"),
        ("hold_rate", "HOLD rate"),
        ("accuracy", "Accuracy"),
        ("avg_confidence", "Average confidence"),
        ("avg_composite", "Average composite score"),
        ("bullish_ratio", "Bullish ratio"),
    ]

    for key, label in metrics_to_compare:
        earlier_val = earlier.get(key, 0)
        later_val = later.get(key, 0)

        # Calculate absolute change
        change = later_val - earlier_val

        # Calculate relative change (percentage points for rates, % for others)
        if key in ["accuracy", "avg_confidence"]:
            change_str = f"{change:+.1f} percentage points"
            significant = abs(change) > (DRIFT_THRESHOLD * 100)
        elif key in ["avg_composite"]:
            change_str = f"{change:+.3f}"
            significant = abs(change) > 0.1  # Composite threshold
        else:
            change_str = f"{change:+.3f} ({change*100:+.1f} pp)"
            significant = abs(change) > DRIFT_THRESHOLD

        changes[key] = {
            "earlier": earlier_val,
            "later": later_val,
            "change": change_str,
            "significant": significant,
        }

        if significant:
            direction = "increased" if change > 0 else "decreased"
            flags.append(
                f"{label} {direction}: {earlier_val} → {later_val} "
                f"({change_str}) between {earlier_label.replace('_', ' ')} "
                f"and {later_label.replace('_', ' ')}"
            )

    return {
        "earlier_period": earlier_label.replace("_", " "),
        "later_period": later_label.replace("_", " "),
        "changes": changes,
        "flags": flags,
        "significant_changes": len(flags),
    }


def _assess_drift(periods: dict, flags: list) -> str:
    """Generate overall drift assessment."""
    if not flags:
        return (
            "No significant behavioral drift detected. The model's "
            "decision patterns have remained stable across all time periods."
        )

    # Check accuracy trend
    period_keys = [w for w in VALID_WINDOWS if w in periods]
    accuracies = [periods[k]["accuracy"] for k in period_keys]

    if len(accuracies) >= 2:
        if accuracies[-1] > accuracies[0] + 10:
            trend = "improving"
            trend_detail = (
                f"Accuracy improved from {accuracies[0]}% to {accuracies[-1]}% "
                f"over the evaluation period."
            )
        elif accuracies[-1] < accuracies[0] - 10:
            trend = "degrading"
            trend_detail = (
                f"Accuracy degraded from {accuracies[0]}% to {accuracies[-1]}% "
                f"over the evaluation period. This may indicate model decay."
            )
        else:
            trend = "stable accuracy"
            trend_detail = (
                f"Accuracy remained relatively stable "
                f"({accuracies[0]}% → {accuracies[-1]}%)."
            )
    else:
        trend = "unknown"
        trend_detail = ""

    flag_count = len(flags)
    if flag_count <= 2:
        severity = "Moderate drift detected"
    else:
        severity = "Significant drift detected"

    return (
        f"{severity}: {flag_count} metric(s) changed beyond the "
        f"{DRIFT_THRESHOLD:.0%} threshold. {trend_detail} "
        f"Review decision patterns and consider model recalibration."
    )
