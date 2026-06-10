"""
Phoenix Client — queries traced decision data.

Provides functions for Tools 2-5 to find and analyze past decisions.
Primary data source: seed_results.json (reliable, fast).
Future enhancement: Phoenix REST API / MCP for live queries.

This is the SHARED query layer. All governance tools use this
to access historical decision data.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from tradeshield.config import DATA_DIR, SECTOR_MAP

logger = logging.getLogger("tradeshield.phoenix")

# Cache loaded results in memory
_seed_data: list[dict] | None = None


def _load_seed_data() -> list[dict]:
    """Load seed results from JSON file. Cached after first load."""
    global _seed_data
    if _seed_data is not None:
        return _seed_data

    filepath = DATA_DIR / "seed_results.json"
    if not filepath.exists():
        logger.warning("phoenix.client | seed_results.json not found")
        return []

    with open(filepath, "r") as f:
        _seed_data = json.load(f)

    logger.info(f"phoenix.client | loaded {len(_seed_data)} traced decisions")
    return _seed_data


def query_by_ticker(ticker: str) -> list[dict]:
    """Find all traced decisions for a specific ticker."""
    ticker = ticker.upper().strip()
    data = _load_seed_data()
    results = [d for d in data if d.get("ticker") == ticker]
    logger.info(f"phoenix.query | ticker={ticker} | found={len(results)}")
    return results


def query_by_sector(sector: str) -> list[dict]:
    """Find all traced decisions for a specific sector."""
    sector = sector.lower().strip()
    data = _load_seed_data()
    results = [d for d in data if d.get("sector") == sector]
    logger.info(f"phoenix.query | sector={sector} | found={len(results)}")
    return results


def query_by_decision(decision: str) -> list[dict]:
    """Find all traced decisions of a specific type (BUY/SELL/HOLD)."""
    decision = decision.upper().strip()
    data = _load_seed_data()
    results = [d for d in data if d.get("decision") == decision]
    logger.info(f"phoenix.query | decision={decision} | found={len(results)}")
    return results


def query_by_window(window: str) -> list[dict]:
    """Find all traced decisions from a specific time window."""
    data = _load_seed_data()
    results = [d for d in data if d.get("window") == window]
    logger.info(f"phoenix.query | window={window} | found={len(results)}")
    return results


def query_by_conditions(
    sector: Optional[str] = None,
    decision: Optional[str] = None,
    window: Optional[str] = None,
    min_confidence: Optional[int] = None,
) -> list[dict]:
    """
    Find traces matching multiple conditions.
    Used by Tool 5 (reliability) to find similar past decisions.
    """
    data = _load_seed_data()
    results = data

    if sector:
        results = [d for d in results if d.get("sector") == sector.lower()]
    if decision:
        results = [d for d in results if d.get("decision") == decision.upper()]
    if window:
        results = [d for d in results if d.get("window") == window]
    if min_confidence is not None:
        results = [d for d in results if d.get("confidence", 0) >= min_confidence]

    logger.info(
        f"phoenix.query | conditions=sector:{sector},decision:{decision},"
        f"window:{window},min_conf:{min_confidence} | found={len(results)}"
    )
    return results


def get_all_traces() -> list[dict]:
    """Return all traced decisions."""
    return _load_seed_data()


def get_accuracy_by_sector() -> dict:
    """Calculate accuracy for each sector."""
    data = _load_seed_data()
    sectors = {}

    for d in data:
        sector = d.get("sector", "unknown")
        if sector not in sectors:
            sectors[sector] = {"total": 0, "correct": 0, "decisions": []}

        sectors[sector]["total"] += 1
        if d.get("correct"):
            sectors[sector]["correct"] += 1
        sectors[sector]["decisions"].append(d.get("decision"))

    # Calculate rates
    for sector, stats in sectors.items():
        total = stats["total"]
        stats["accuracy"] = round(stats["correct"] / total * 100, 1) if total > 0 else 0
        stats["buy_count"] = stats["decisions"].count("BUY")
        stats["sell_count"] = stats["decisions"].count("SELL")
        stats["hold_count"] = stats["decisions"].count("HOLD")
        stats["buy_rate"] = round(stats["buy_count"] / total, 3) if total > 0 else 0
        stats["sell_rate"] = round(stats["sell_count"] / total, 3) if total > 0 else 0
        stats["hold_rate"] = round(stats["hold_count"] / total, 3) if total > 0 else 0
        del stats["decisions"]

    return sectors


def get_accuracy_by_decision() -> dict:
    """Calculate accuracy for each decision type."""
    data = _load_seed_data()
    decisions = {}

    for d in data:
        dec = d.get("decision", "UNKNOWN")
        if dec not in decisions:
            decisions[dec] = {"total": 0, "correct": 0}

        decisions[dec]["total"] += 1
        if d.get("correct"):
            decisions[dec]["correct"] += 1

    for dec, stats in decisions.items():
        total = stats["total"]
        stats["accuracy"] = round(stats["correct"] / total * 100, 1) if total > 0 else 0

    return decisions


def get_accuracy_by_window() -> dict:
    """Calculate accuracy for each time window."""
    data = _load_seed_data()
    windows = {}

    for d in data:
        window = d.get("window", "unknown")
        if window not in windows:
            windows[window] = {"total": 0, "correct": 0}

        windows[window]["total"] += 1
        if d.get("correct"):
            windows[window]["correct"] += 1

    for w, stats in windows.items():
        total = stats["total"]
        stats["accuracy"] = round(stats["correct"] / total * 100, 1) if total > 0 else 0

    return windows


def get_summary_stats() -> dict:
    """Get overall summary statistics."""
    data = _load_seed_data()
    total = len(data)
    correct = sum(1 for d in data if d.get("correct"))
    known = sum(1 for d in data if d.get("correct") is not None)

    return {
        "total_traces": total,
        "known_outcomes": known,
        "correct": correct,
        "accuracy": round(correct / known * 100, 1) if known > 0 else 0,
        "by_sector": get_accuracy_by_sector(),
        "by_decision": get_accuracy_by_decision(),
        "by_window": get_accuracy_by_window(),
    }
