"""
Day 13: Hardening Tests

Tests all 5 governance tools DIRECTLY in Python — zero Gemini calls.
Validates edge cases, error handling, and data integrity.

Usage: python scripts/test_hardening.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from tradeshield.agent.tools.analyze import analyze_trade
from tradeshield.agent.tools.explain import explain_decision
from tradeshield.agent.tools.fairness import audit_fairness
from tradeshield.agent.tools.drift import detect_drift
from tradeshield.agent.tools.improve import assess_reliability, analyze_with_reliability
from tradeshield.phoenix.client import get_all_traces, get_summary_stats


def run_tests():
    print("=" * 60)
    print("TradeShield — Hardening Tests (Day 13)")
    print("=" * 60)
    print()
    print("Zero Gemini calls. All tests call Python functions directly.")
    print()

    passed = 0
    failed = 0
    total = 0

    def test(name, condition, detail=""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name} — {detail}")

    # ============================================================
    # Test Group 1: Data Integrity
    # ============================================================
    print("--- Group 1: Data Integrity ---")
    traces = get_all_traces()
    test("Traces loaded", len(traces) > 0, f"got {len(traces)}")
    test("108 traces expected", len(traces) == 108, f"got {len(traces)}")

    stats = get_summary_stats()
    test("Summary stats available", stats is not None)
    test("Accuracy calculated", stats.get("accuracy") is not None)
    test("6 sectors present", len(stats.get("by_sector", {})) == 6, f"got {len(stats.get('by_sector', {}))}")
    test("3 decision types", len(stats.get("by_decision", {})) == 3, f"got {len(stats.get('by_decision', {}))}")
    test("3 time windows", len(stats.get("by_window", {})) == 3, f"got {len(stats.get('by_window', {}))}")
    print()

    # ============================================================
    # Test Group 2: Tool 1 — analyze_trade
    # ============================================================
    print("--- Group 2: Tool 1 (analyze_trade) ---")

    # Valid ticker (cached)
    result = analyze_trade("NVDA")
    test("NVDA returns result", result is not None)
    test("NVDA has decision", result.get("decision") in ["BUY", "SELL", "HOLD"])
    test("NVDA has confidence", 50 <= result.get("confidence", 0) <= 99)
    test("NVDA has 7 factors", len(result.get("factors", {})) == 7, f"got {len(result.get('factors', {}))}")
    test("NVDA has composite", result.get("composite_score") is not None or result.get("composite") is not None)

    # Case insensitive
    result_lower = analyze_trade("nvda")
    test("Case insensitive", result_lower.get("ticker") == "NVDA")

    # Invalid ticker
    result_bad = analyze_trade("BANANA")
    test("Invalid ticker handled", result_bad.get("error") is True or "error" in str(result_bad).lower())
    print()

    # ============================================================
    # Test Group 3: Tool 2 — explain_decision
    # ============================================================
    print("--- Group 3: Tool 2 (explain_decision) ---")

    result = explain_decision("NVDA")
    test("NVDA explanation exists", result is not None)
    test("No error", result.get("error") is not True)
    test("Has decisions list", len(result.get("decisions", [])) > 0)
    test("Has summary", result.get("summary") is not None)
    test("Has ticker accuracy", "accuracy" in str(result.get("summary", {})))

    # Check evidence lineage
    decisions = result.get("decisions", [])
    if decisions:
        first = decisions[0]
        lineage = first.get("evidence_lineage", {})
        test("Has data source", "Yahoo" in lineage.get("data_source", ""))
        test("Has model version", "7-factor" in lineage.get("model_version", ""))
        test("Has outcome", first.get("outcome") is not None)
    else:
        test("Has evidence lineage", False, "no decisions found")

    # Unknown ticker
    result_unknown = explain_decision("ZZZZZ")
    test("Unknown ticker handled", result_unknown.get("error") is True)
    print()

    # ============================================================
    # Test Group 4: Tool 3 — audit_fairness
    # ============================================================
    print("--- Group 4: Tool 3 (audit_fairness) ---")

    result = audit_fairness()
    test("Fairness result exists", result is not None)
    test("No error", result.get("error") is not True)
    test("Has sector stats", len(result.get("sector_stats", {})) == 6)
    test("Has disparate impact", len(result.get("disparate_impact_ratios", {})) > 0)
    test("Has flags", result.get("flags") is not None)
    test("Has assessment", result.get("assessment") is not None)
    test("Has caveat", result.get("caveat") is not None)

    # Verify disparate impact calculations
    di = result.get("disparate_impact_ratios", {})
    if "accuracy" in di:
        test("Accuracy DI ratio valid", 0 <= di["accuracy"]["ratio"] <= 1)
        test("Accuracy DI flagged", di["accuracy"]["flagged"] is True, "should be flagged")
    print()

    # ============================================================
    # Test Group 5: Tool 4 — detect_drift
    # ============================================================
    print("--- Group 5: Tool 4 (detect_drift) ---")

    result = detect_drift()
    test("Drift result exists", result is not None)
    test("No error", result.get("error") is not True)
    test("3 periods analyzed", result.get("periods_analyzed") == 3)
    test("Has period stats", len(result.get("period_stats", {})) == 3)
    test("Has comparisons", len(result.get("period_comparisons", [])) > 0)
    test("Has flags", result.get("flags") is not None)
    test("Has assessment", result.get("assessment") is not None)
    test("Accuracy drift detected", any("Accuracy" in f for f in result.get("flags", [])))
    print()

    # ============================================================
    # Test Group 6: Tool 5 — assess_reliability
    # ============================================================
    print("--- Group 6: Tool 5 (assess_reliability) ---")

    result = assess_reliability("NVDA")
    test("Reliability result exists", result is not None)
    test("Has warning level", result.get("warning_level") in ["GREEN", "YELLOW", "RED", "INSUFFICIENT_DATA"])
    test("Has 5 dimensions", len(result.get("dimensions", {})) == 5)
    test("Has specific reasons", len(result.get("specific_reasons", [])) > 0)
    test("Has recommendation", result.get("recommendation") is not None)

    # Check each dimension
    dims = result.get("dimensions", {})
    test("Has evidence coverage", "evidence_coverage" in dims)
    test("Has past accuracy", "past_accuracy" in dims)
    test("Has confidence gap", "confidence_gap" in dims)
    test("Has drift signal", "drift_signal" in dims)
    test("Has pattern consistency", "pattern_consistency" in dims)

    # Unknown sector ticker
    result_unknown = assess_reliability("ZZZZZ")
    test("Unknown ticker has warning", result_unknown.get("warning_level") is not None)
    print()

    # ============================================================
    # Test Group 7: Combined Tool
    # ============================================================
    print("--- Group 7: Combined Tool (analyze_with_reliability) ---")

    result = analyze_with_reliability("AAPL")
    test("Combined result exists", result is not None)
    test("Has reliability", result.get("reliability_assessment") is not None)
    test("Has analysis", result.get("analysis") is not None)
    test("Has combined summary", result.get("combined_summary") is not None)
    test("Analysis has decision", result.get("analysis", {}).get("decision") in ["BUY", "SELL", "HOLD"])
    test("Reliability has warning", result.get("reliability_assessment", {}).get("warning_level") is not None)
    print()

    # ============================================================
    # Summary
    # ============================================================
    print("=" * 60)
    print(f"HARDENING RESULTS: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 60)

    if failed == 0:
        print("ALL TESTS PASSED ✓")
        print("Day 13 COMPLETE ✓")
    else:
        print(f"{failed} test(s) failed — review above.")
        print("Day 13 needs attention.")

    print("=" * 60)

    return passed, failed, total


if __name__ == "__main__":
    run_tests()
