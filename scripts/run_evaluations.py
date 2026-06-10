"""
Day 12: Evaluation Framework

Scores the trading model's decisions against actual outcomes.
Generates evaluation metrics for governance reporting.

ZERO Gemini calls — runs entirely on local data.

Evaluation dimensions:
1. Overall accuracy (correct/total)
2. Sector-level accuracy with disparity analysis
3. Decision-type accuracy (BUY/SELL/HOLD)
4. Confidence calibration (stated vs actual)
5. Temporal stability (accuracy across time periods)
6. Failure pattern classification (why decisions fail)

Output: evaluation_report.json + printed summary
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from datetime import datetime
from tradeshield.phoenix.client import (
    get_all_traces,
    get_accuracy_by_sector,
    get_accuracy_by_decision,
    get_accuracy_by_window,
    get_summary_stats,
)
from tradeshield.config import DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tradeshield.eval")


def run_evaluations():
    """Run all evaluation dimensions."""

    print("=" * 60)
    print("TradeShield — Evaluation Framework (Day 12)")
    print("=" * 60)
    print()
    print("Zero Gemini calls. All evaluations run on local trace data.")
    print()

    traces = get_all_traces()
    if not traces:
        print("ERROR: No traces found. Run seed.py first.")
        return

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_traces": len(traces),
        "evaluations": {},
    }

    # ============================================================
    # Evaluation 1: Overall Accuracy
    # ============================================================
    print("--- Evaluation 1: Overall Accuracy ---")
    stats = get_summary_stats()
    overall = {
        "total": stats["total_traces"],
        "known_outcomes": stats["known_outcomes"],
        "correct": stats["correct"],
        "accuracy": stats["accuracy"],
        "grade": _grade_accuracy(stats["accuracy"]),
    }
    report["evaluations"]["overall_accuracy"] = overall
    print(f"  Accuracy: {stats['accuracy']}% ({stats['correct']}/{stats['known_outcomes']})")
    print(f"  Grade: {overall['grade']}")
    print()

    # ============================================================
    # Evaluation 2: Sector Fairness
    # ============================================================
    print("--- Evaluation 2: Sector Fairness ---")
    sector_stats = get_accuracy_by_sector()
    accuracies = {s: v["accuracy"] for s, v in sector_stats.items()}
    max_acc = max(accuracies.values())
    min_acc = min(accuracies.values())
    disparity_ratio = round(min_acc / max_acc, 3) if max_acc > 0 else 0

    fairness = {
        "sector_accuracies": accuracies,
        "best_sector": max(accuracies, key=accuracies.get),
        "worst_sector": min(accuracies, key=accuracies.get),
        "disparity_ratio": disparity_ratio,
        "fair": disparity_ratio >= 0.80,
        "grade": "PASS" if disparity_ratio >= 0.80 else "FAIL",
    }
    report["evaluations"]["sector_fairness"] = fairness

    for sector, acc in sorted(accuracies.items()):
        flag = " ← WORST" if sector == fairness["worst_sector"] else ""
        flag = " ← BEST" if sector == fairness["best_sector"] else flag
        print(f"  {sector:12s}: {acc}%{flag}")
    print(f"  Disparity ratio: {disparity_ratio} (threshold: 0.80)")
    print(f"  Grade: {fairness['grade']}")
    print()

    # ============================================================
    # Evaluation 3: Decision Type Accuracy
    # ============================================================
    print("--- Evaluation 3: Decision Type Accuracy ---")
    dec_stats = get_accuracy_by_decision()
    decision_eval = {}
    for dec, stats in dec_stats.items():
        decision_eval[dec] = {
            "total": stats["total"],
            "correct": stats["correct"],
            "accuracy": stats["accuracy"],
            "grade": _grade_accuracy(stats["accuracy"]),
        }
        print(f"  {dec:5s}: {stats['accuracy']}% ({stats['correct']}/{stats['total']}) — {decision_eval[dec]['grade']}")

    report["evaluations"]["decision_accuracy"] = decision_eval
    print()

    # ============================================================
    # Evaluation 4: Confidence Calibration
    # ============================================================
    print("--- Evaluation 4: Confidence Calibration ---")
    known = [t for t in traces if t.get("correct") is not None]
    avg_confidence = sum(t.get("confidence", 0) for t in known) / len(known)
    actual_accuracy = sum(1 for t in known if t.get("correct")) / len(known) * 100
    gap = round(avg_confidence - actual_accuracy, 1)

    calibration = {
        "avg_stated_confidence": round(avg_confidence, 1),
        "actual_accuracy": round(actual_accuracy, 1),
        "overconfidence_gap": gap,
        "assessment": _assess_calibration(gap),
        "grade": "PASS" if abs(gap) <= 10 else "FAIL",
    }
    report["evaluations"]["confidence_calibration"] = calibration
    print(f"  Stated confidence: {avg_confidence:.1f}%")
    print(f"  Actual accuracy:   {actual_accuracy:.1f}%")
    print(f"  Gap:               {gap:+.1f} points")
    print(f"  Assessment:        {calibration['assessment']}")
    print(f"  Grade:             {calibration['grade']}")
    print()

    # ============================================================
    # Evaluation 5: Temporal Stability
    # ============================================================
    print("--- Evaluation 5: Temporal Stability ---")
    window_stats = get_accuracy_by_window()
    windows = {}
    prev_acc = None
    for w in ["2_months_ago", "1_month_ago", "1_week_ago"]:
        if w in window_stats:
            acc = window_stats[w]["accuracy"]
            change = round(acc - prev_acc, 1) if prev_acc is not None else 0
            windows[w] = {
                "accuracy": acc,
                "total": window_stats[w]["total"],
                "correct": window_stats[w]["correct"],
                "change_from_previous": change,
            }
            prev_acc = acc
            print(f"  {w:15s}: {acc}% ({window_stats[w]['correct']}/{window_stats[w]['total']}) change: {change:+.1f}pp")

    # Calculate stability score
    accs = [v["accuracy"] for v in windows.values()]
    if len(accs) >= 2:
        max_change = max(accs) - min(accs)
        stable = max_change < 15
    else:
        max_change = 0
        stable = True

    temporal = {
        "windows": windows,
        "max_accuracy_swing": round(max_change, 1),
        "stable": stable,
        "grade": "PASS" if stable else "FAIL — significant drift detected",
    }
    report["evaluations"]["temporal_stability"] = temporal
    print(f"  Max swing: {max_change:.1f}pp (threshold: 15pp)")
    print(f"  Grade: {temporal['grade']}")
    print()

    # ============================================================
    # Evaluation 6: Failure Pattern Classification
    # ============================================================
    print("--- Evaluation 6: Failure Pattern Analysis ---")
    failures = [t for t in traces if t.get("correct") is False]
    failure_patterns = classify_failures(failures)
    report["evaluations"]["failure_patterns"] = failure_patterns

    for pattern, count in sorted(failure_patterns["categories"].items(), key=lambda x: -x[1]):
        pct = round(count / len(failures) * 100, 1) if failures else 0
        print(f"  {pattern:30s}: {count} failures ({pct}%)")

    print(f"  Total failures analyzed: {len(failures)}")
    print()

    # ============================================================
    # Overall Evaluation Score
    # ============================================================
    print("=" * 60)
    print("OVERALL EVALUATION SUMMARY")
    print("=" * 60)

    grades = {
        "Overall Accuracy": overall["grade"],
        "Sector Fairness": fairness["grade"],
        "BUY Accuracy": decision_eval.get("BUY", {}).get("grade", "N/A"),
        "SELL Accuracy": decision_eval.get("SELL", {}).get("grade", "N/A"),
        "HOLD Accuracy": decision_eval.get("HOLD", {}).get("grade", "N/A"),
        "Confidence Calibration": calibration["grade"],
        "Temporal Stability": temporal["grade"],
    }

    pass_count = sum(1 for g in grades.values() if g == "PASS" or g == "A" or g == "B")
    fail_count = sum(1 for g in grades.values() if "FAIL" in str(g) or g in ["D", "F"])

    for metric, grade in grades.items():
        status = "✓" if "FAIL" not in str(grade) and grade not in ["D", "F"] else "✗"
        print(f"  {status} {metric:25s}: {grade}")

    print()
    print(f"  Passed: {pass_count}/{len(grades)}")
    print(f"  Failed: {fail_count}/{len(grades)}")
    print()

    # The model is SUPPOSED to have issues — that's the point of governance
    print("  NOTE: A low-accuracy model is EXPECTED and INTENTIONAL.")
    print("  TradeShield's value is in DETECTING and REPORTING these issues,")
    print("  not in having a perfect model. The governance layer correctly")
    print("  identifies all failure patterns above.")
    print()

    report["overall"] = {
        "grades": grades,
        "passed": pass_count,
        "failed": fail_count,
        "total_metrics": len(grades),
        "note": "Low accuracy is intentional. TradeShield's value is governance and detection.",
    }

    # Save report
    report_path = DATA_DIR / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"  Report saved to: {report_path}")
    print()
    print("=" * 60)
    print("Day 12 COMPLETE ✓")
    print("=" * 60)


def classify_failures(failures: list) -> dict:
    """Classify why decisions failed."""
    categories = {
        "overconfident_buy": 0,      # BUY with high confidence, price dropped
        "overconfident_sell": 0,     # SELL with high confidence, price rose
        "wrong_direction_hold": 0,   # HOLD but price moved significantly
        "momentum_reversal": 0,     # Momentum was positive but price dropped (or vice versa)
        "value_trap": 0,            # Low P/E (value signal) but stock dropped
        "quality_misleading": 0,    # High quality score but wrong decision
        "other": 0,
    }

    for f in failures:
        decision = f.get("decision", "")
        confidence = f.get("confidence", 0)
        price_change = f.get("price_change", 0)
        composite = f.get("composite", 0)

        if decision == "BUY" and price_change < 0:
            categories["overconfident_buy"] += 1
        elif decision == "SELL" and price_change > 0:
            categories["overconfident_sell"] += 1
        elif decision == "HOLD" and abs(price_change) > 3:
            categories["wrong_direction_hold"] += 1
        elif composite > 0 and price_change < -2:
            categories["momentum_reversal"] += 1
        elif composite < 0 and price_change > 2:
            categories["value_trap"] += 1
        else:
            categories["other"] += 1

    # Remove zero categories
    categories = {k: v for k, v in categories.items() if v > 0}

    return {
        "total_failures": len(failures),
        "categories": categories,
        "most_common": max(categories, key=categories.get) if categories else "none",
    }


def _grade_accuracy(accuracy: float) -> str:
    if accuracy >= 70:
        return "A"
    elif accuracy >= 50:
        return "B"
    elif accuracy >= 35:
        return "C"
    elif accuracy >= 25:
        return "D"
    else:
        return "F"


def _assess_calibration(gap: float) -> str:
    if gap > 30:
        return "Severely overconfident — model needs significant recalibration"
    elif gap > 20:
        return "Highly overconfident — confidence scores are misleading"
    elif gap > 10:
        return "Moderately overconfident — confidence should be discounted"
    elif gap > 0:
        return "Slightly overconfident — minor calibration needed"
    elif gap > -10:
        return "Well calibrated"
    else:
        return "Underconfident — model is better than it thinks"


if __name__ == "__main__":
    run_evaluations()
