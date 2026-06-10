"""
Tool 3: Audit Fairness

Checks if the trading model treats all stock sectors equally.
Queries all traced decisions, groups by sector, and calculates
disparate impact ratios to detect potential bias.

Disparate impact ratio = lowest group rate / highest group rate.
Industry standard threshold: ratios below 0.80 indicate potential bias.
Source: EEOC 4/5ths rule adapted for AI fairness auditing.
"""

import logging
from tradeshield.phoenix.client import (
    get_all_traces,
    get_accuracy_by_sector,
    get_accuracy_by_decision,
)

logger = logging.getLogger("tradeshield.tools")


def audit_fairness() -> dict:
    """Check if the trading model treats all stock sectors equally.

    Queries all traced decisions in Arize Phoenix, groups them by
    sector, and calculates disparate impact ratios to detect
    potential bias in the model's recommendations.

    Analyzes: decision distribution (BUY/SELL/HOLD rates per sector),
    accuracy rates per sector, confidence levels per sector, and
    calculates disparate impact ratios for each metric.

    Use this tool when the user asks things like:
    - "Is the model fair across sectors?"
    - "Check for bias"
    - "Compare sectors"
    - "Fairness audit"
    - "Are there disparities?"

    Returns:
        dict: Complete fairness analysis with per-sector stats,
              disparate impact ratios, flags, and recommendations.
    """
    traces = get_all_traces()

    if not traces:
        return {
            "error": True,
            "message": "No traced decisions found. Run the seed script first.",
        }

    # Group traces by sector
    sectors = {}
    for t in traces:
        sector = t.get("sector", "unknown")
        if sector not in sectors:
            sectors[sector] = {
                "traces": [],
                "decisions": [],
                "correct": 0,
                "total": 0,
                "confidences": [],
            }

        sectors[sector]["traces"].append(t)
        sectors[sector]["decisions"].append(t.get("decision"))
        sectors[sector]["total"] += 1
        sectors[sector]["confidences"].append(t.get("confidence", 0))
        if t.get("correct"):
            sectors[sector]["correct"] += 1

    # Calculate per-sector stats
    sector_stats = {}
    for sector, data in sectors.items():
        total = data["total"]
        decisions = data["decisions"]
        buy_count = decisions.count("BUY")
        sell_count = decisions.count("SELL")
        hold_count = decisions.count("HOLD")

        sector_stats[sector] = {
            "total_decisions": total,
            "buy_rate": round(buy_count / total, 3) if total > 0 else 0,
            "sell_rate": round(sell_count / total, 3) if total > 0 else 0,
            "hold_rate": round(hold_count / total, 3) if total > 0 else 0,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "accuracy": round(data["correct"] / total * 100, 1) if total > 0 else 0,
            "avg_confidence": round(sum(data["confidences"]) / total, 1) if total > 0 else 0,
        }

    # Calculate disparate impact ratios
    flags = []
    disparate_impact = {}

    # Accuracy disparate impact
    accuracies = {s: stats["accuracy"] for s, stats in sector_stats.items() if stats["accuracy"] > 0}
    if accuracies:
        max_acc = max(accuracies.values())
        min_acc = min(accuracies.values())
        best_sector = max(accuracies, key=accuracies.get)
        worst_sector = min(accuracies, key=accuracies.get)
        acc_ratio = round(min_acc / max_acc, 3) if max_acc > 0 else 0

        disparate_impact["accuracy"] = {
            "ratio": acc_ratio,
            "best_sector": f"{best_sector} ({max_acc}%)",
            "worst_sector": f"{worst_sector} ({min_acc}%)",
            "threshold": 0.80,
            "flagged": acc_ratio < 0.80,
        }
        if acc_ratio < 0.80:
            flags.append(
                f"Accuracy disparity: {worst_sector} ({min_acc}%) vs "
                f"{best_sector} ({max_acc}%) — ratio {acc_ratio} < 0.80 threshold"
            )

    # BUY rate disparate impact
    buy_rates = {s: stats["buy_rate"] for s, stats in sector_stats.items()}
    non_zero_buy = {s: r for s, r in buy_rates.items() if r > 0}
    if len(non_zero_buy) >= 2:
        max_buy = max(non_zero_buy.values())
        min_buy = min(non_zero_buy.values())
        buy_ratio = round(min_buy / max_buy, 3) if max_buy > 0 else 0

        disparate_impact["buy_rate"] = {
            "ratio": buy_ratio,
            "highest": f"{max(non_zero_buy, key=non_zero_buy.get)} ({max_buy:.1%})",
            "lowest": f"{min(non_zero_buy, key=non_zero_buy.get)} ({min_buy:.1%})",
            "threshold": 0.80,
            "flagged": buy_ratio < 0.80,
        }
        if buy_ratio < 0.80:
            flags.append(
                f"BUY rate disparity: some sectors receive significantly "
                f"more BUY signals than others — ratio {buy_ratio}"
            )

    # SELL rate disparate impact
    sell_rates = {s: stats["sell_rate"] for s, stats in sector_stats.items()}
    non_zero_sell = {s: r for s, r in sell_rates.items() if r > 0}
    if len(non_zero_sell) >= 2:
        max_sell = max(non_zero_sell.values())
        min_sell = min(non_zero_sell.values())
        sell_ratio = round(min_sell / max_sell, 3) if max_sell > 0 else 0

        disparate_impact["sell_rate"] = {
            "ratio": sell_ratio,
            "highest": f"{max(non_zero_sell, key=non_zero_sell.get)} ({max_sell:.1%})",
            "lowest": f"{min(non_zero_sell, key=non_zero_sell.get)} ({min_sell:.1%})",
            "threshold": 0.80,
            "flagged": sell_ratio < 0.80,
        }
        if sell_ratio < 0.80:
            flags.append(
                f"SELL rate disparity: some sectors receive significantly "
                f"more SELL signals — ratio {sell_ratio}"
            )

    # Confidence disparate impact
    confidences = {s: stats["avg_confidence"] for s, stats in sector_stats.items()}
    if confidences:
        max_conf = max(confidences.values())
        min_conf = min(confidences.values())
        conf_ratio = round(min_conf / max_conf, 3) if max_conf > 0 else 0

        disparate_impact["confidence"] = {
            "ratio": conf_ratio,
            "highest": f"{max(confidences, key=confidences.get)} ({max_conf}%)",
            "lowest": f"{min(confidences, key=confidences.get)} ({min_conf}%)",
            "threshold": 0.80,
            "flagged": conf_ratio < 0.80,
        }
        if conf_ratio < 0.80:
            flags.append(
                f"Confidence disparity: model is significantly more "
                f"confident in some sectors than others — ratio {conf_ratio}"
            )

    # Overall assessment
    flagged_count = sum(1 for d in disparate_impact.values() if d.get("flagged"))
    if flagged_count == 0:
        assessment = "No significant disparities detected across sectors."
    elif flagged_count <= 2:
        assessment = (
            f"Potential bias detected: {flagged_count} metric(s) show "
            f"disparate impact below the 0.80 threshold. Review recommended."
        )
    else:
        assessment = (
            f"Significant bias concern: {flagged_count} metrics show "
            f"disparate impact below threshold. Detailed review required."
        )

    response = {
        "total_traces_analyzed": len(traces),
        "sectors_compared": len(sector_stats),
        "sector_stats": sector_stats,
        "disparate_impact_ratios": disparate_impact,
        "flags": flags,
        "assessment": assessment,
        "caveat": (
            "Simplified category-level comparison for demonstration. "
            "Production fairness auditing requires deeper statistical "
            "analysis including confidence intervals, sample size "
            "adjustments, and domain-specific fairness criteria."
        ),
    }

    logger.info(
        f"tools.fairness | traces={len(traces)} | sectors={len(sector_stats)} | "
        f"flags={len(flags)} | status=complete"
    )

    return response
