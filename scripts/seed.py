"""
Seed Script — Generate 70-100 traces in Phoenix using historical data.

This script:
1. Loads cached stock data (3 months of history per stock)
2. Simulates running the model at 3 different past dates per stock
3. Calculates actual outcomes (did price go up/down 5 days after?)
4. Sends each decision as a trace to Phoenix with custom attributes
5. Prints accuracy summary by sector and condition

IMPORTANT: Does NOT use Gemini. Runs pipeline + model directly.
This avoids rate limits entirely. Zero API key cost.

Usage: python scripts/seed.py
"""

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tradeshield.seed")

# Set up Phoenix tracing BEFORE anything else
from tradeshield.phoenix.tracing import setup_tracing
setup_tracing()

import pandas as pd
from opentelemetry import trace

from tradeshield.config import SEEDED_TICKERS, SECTOR_MAP, DATA_DIR
from tradeshield.pipeline.cache import load_from_cache
from tradeshield.model.factors import calculate_all_factors
from tradeshield.model.scorer import score_stock, calculate_composite, determine_decision, calculate_confidence

# Get a tracer for creating spans
tracer = trace.get_tracer("tradeshield.seed")

# Seed configuration
SEED_WINDOWS = [
    {"label": "2_months_ago", "end_offset": 44, "start_offset": 0},   # Days 0-44 (earliest)
    {"label": "1_month_ago", "end_offset": 22, "start_offset": 0},    # Days 0-22+offset
    {"label": "1_week_ago", "end_offset": 5, "start_offset": 0},      # Most recent
]
OUTCOME_DAYS = 5  # Check price 5 trading days after decision
SEED_DELAY = 0.5  # Seconds between traces (prevent Phoenix rate limiting)


def build_stock_data_for_window(cached_data: dict, history_df: pd.DataFrame,
                                 end_idx: int) -> dict:
    """
    Build a stock_data dict as if we were analyzing at a specific past date.

    Args:
        cached_data: Full cached data dict
        history_df: Full history DataFrame
        end_idx: The index (from end) to use as "current" date
                 0 = most recent, 44 = 44 days ago

    Returns:
        dict: Stock data dict that looks like it was fetched on that date
    """
    # Slice history up to the simulated "current" date
    if end_idx == 0:
        window_df = history_df.copy()
    else:
        window_df = history_df.iloc[:-end_idx].copy()

    if len(window_df) < 50:
        return None

    # Recalculate moving averages for this window
    window_df["MA_10"] = window_df["Close"].rolling(window=10).mean()
    window_df["MA_20"] = window_df["Close"].rolling(window=20).mean()
    window_df["MA_50"] = window_df["Close"].rolling(window=50).mean()

    current_price = float(window_df["Close"].iloc[-1])
    current_volume = float(window_df["Volume"].iloc[-1])
    volume_avg = float(window_df["Volume"].mean())

    return {
        "ticker": cached_data.get("ticker", ""),
        "sector": cached_data.get("sector", "unknown"),
        "history": window_df,
        "current_price": current_price,
        "current_volume": current_volume,
        "volume_avg": volume_avg,
        "pe_ratio": cached_data.get("pe_ratio"),
        "profit_margin": cached_data.get("profit_margin"),
        "vix": cached_data.get("vix", 20.0),
        "data_points": len(window_df),
        "fetch_timestamp": str(window_df.index[-1]),
    }


def calculate_outcome(history_df: pd.DataFrame, decision_idx: int,
                       decision: str) -> dict:
    """
    Calculate the actual outcome N days after a decision.

    Args:
        history_df: Full history DataFrame
        decision_idx: Index in the DataFrame where decision was made
        decision: "BUY", "SELL", or "HOLD"

    Returns:
        dict: outcome details
    """
    if decision_idx + OUTCOME_DAYS >= len(history_df):
        return {"outcome": "unknown", "correct": None, "price_change_pct": None}

    price_at_decision = float(history_df["Close"].iloc[decision_idx])
    price_after = float(history_df["Close"].iloc[decision_idx + OUTCOME_DAYS])
    change_pct = (price_after - price_at_decision) / price_at_decision * 100

    # Determine if decision was correct
    if decision == "BUY":
        correct = change_pct > 0  # Price went up = correct
    elif decision == "SELL":
        correct = change_pct < 0  # Price went down = correct
    else:  # HOLD
        correct = abs(change_pct) < 2  # Price stayed within ±2% = correct

    return {
        "outcome": "correct" if correct else "incorrect",
        "correct": correct,
        "price_at_decision": round(price_at_decision, 2),
        "price_after_5_days": round(price_after, 2),
        "price_change_pct": round(change_pct, 2),
    }


def send_trace_to_phoenix(ticker: str, sector: str, decision: str,
                           confidence: int, composite: float,
                           factors: list, market_data: dict,
                           outcome: dict, window_label: str,
                           decision_date: str, vix: float):
    """
    Create a trace in Phoenix with all custom attributes.

    Uses OpenTelemetry tracer directly (no Gemini needed).
    """
    with tracer.start_as_current_span("trade_analysis") as span:
        # Core decision attributes
        span.set_attribute("ticker", ticker)
        span.set_attribute("sector", sector)
        span.set_attribute("decision", decision)
        span.set_attribute("confidence", confidence)
        span.set_attribute("composite_score", composite)
        span.set_attribute("vix_level", vix)
        span.set_attribute("momentum_direction", "positive" if composite > 0 else "negative")

        # Time and version
        span.set_attribute("decision_date", decision_date)
        span.set_attribute("window_label", window_label)
        span.set_attribute("model_version", "7-factor-v1")
        span.set_attribute("analysis_type", "seeded_trade_analysis")

        # Outcome
        span.set_attribute("outcome", outcome.get("outcome", "unknown"))
        span.set_attribute("outcome_correct", str(outcome.get("correct", "unknown")))
        span.set_attribute("price_at_decision", outcome.get("price_at_decision", 0))
        span.set_attribute("price_after_5_days", outcome.get("price_after_5_days", 0))
        span.set_attribute("price_change_pct", outcome.get("price_change_pct", 0))

        # Factor scores
        for f in factors:
            span.set_attribute(f"factor_{f.name}_score", f.score)
            span.set_attribute(f"factor_{f.name}_weight", f.weight)

        # Market data
        span.set_attribute("price", market_data.get("price", 0))
        span.set_attribute("pe_ratio", str(market_data.get("pe_ratio", "N/A")))
        span.set_attribute("profit_margin", str(market_data.get("profit_margin", "N/A")))

        # Add a descriptive event
        span.add_event(
            "trade_decision",
            attributes={
                "summary": f"{decision} {ticker} at ${market_data.get('price', 0)} "
                          f"with {confidence}% confidence. "
                          f"Outcome: {outcome.get('outcome', 'unknown')} "
                          f"({outcome.get('price_change_pct', 'N/A')}% change)"
            }
        )


def main():
    print("=" * 60)
    print("TradeShield — Seed Phoenix with Historical Traces")
    print("=" * 60)
    print()
    print(f"Stocks: {len(SEEDED_TICKERS)}")
    print(f"Windows per stock: {len(SEED_WINDOWS)}")
    print(f"Expected traces: ~{len(SEEDED_TICKERS) * len(SEED_WINDOWS)}")
    print(f"Outcome measurement: {OUTCOME_DAYS} trading days after decision")
    print()
    print("NO Gemini calls. Direct pipeline + model only.")
    print()

    # Track results
    all_results = []
    trace_count = 0
    skipped = 0

    for i, ticker in enumerate(SEEDED_TICKERS, 1):
        # Load cached data
        cached = load_from_cache(ticker)
        if cached is None:
            logger.warning(f"seed | ticker={ticker} | status=no_cache | skipping")
            skipped += 1
            continue

        # Convert history to DataFrame
        history_data = cached.get("history", {})
        if isinstance(history_data, dict):
            history_df = pd.DataFrame.from_dict(history_data, orient="index")
            history_df.index = pd.to_datetime(history_df.index)
            history_df = history_df.sort_index()
            for col in ["Close", "Volume", "Open", "High", "Low"]:
                if col in history_df.columns:
                    history_df[col] = pd.to_numeric(history_df[col], errors="coerce")
        else:
            logger.warning(f"seed | ticker={ticker} | status=bad_history_format")
            skipped += 1
            continue

        total_days = len(history_df)
        sector = SECTOR_MAP.get(ticker, "unknown")

        for window in SEED_WINDOWS:
            end_offset = window["end_offset"]
            label = window["label"]

            # Build stock data for this window
            stock_data = build_stock_data_for_window(cached, history_df, end_offset)
            if stock_data is None:
                logger.warning(
                    f"seed | ticker={ticker} | window={label} | "
                    f"status=insufficient_data | skipping"
                )
                continue

            # Calculate factors and score
            factors = calculate_all_factors(stock_data)
            result = score_stock(ticker, stock_data, factors)

            # Calculate outcome
            decision_idx = total_days - 1 - end_offset
            outcome = calculate_outcome(history_df, decision_idx, result.decision)

            # Get the decision date
            if decision_idx >= 0 and decision_idx < len(history_df):
                decision_date = str(history_df.index[decision_idx].date())
            else:
                decision_date = "unknown"

            # Send trace to Phoenix
            send_trace_to_phoenix(
                ticker=ticker,
                sector=sector,
                decision=result.decision,
                confidence=result.confidence,
                composite=result.composite_score,
                factors=factors,
                market_data=result.market_data,
                outcome=outcome,
                window_label=label,
                decision_date=decision_date,
                vix=cached.get("vix", 20.0),
            )

            trace_count += 1

            # Track for summary
            all_results.append({
                "ticker": ticker,
                "sector": sector,
                "decision": result.decision,
                "confidence": result.confidence,
                "composite": result.composite_score,
                "window": label,
                "date": decision_date,
                "outcome": outcome.get("outcome", "unknown"),
                "correct": outcome.get("correct"),
                "price_change": outcome.get("price_change_pct"),
            })

            logger.info(
                f"seed | {trace_count:3d} | {ticker:5s} | {label:15s} | "
                f"{result.decision:4s} {result.confidence}% | "
                f"outcome={outcome.get('outcome', 'unknown'):9s} | "
                f"change={outcome.get('price_change_pct', 'N/A')}%"
            )

            # Delay to prevent Phoenix rate limiting
            time.sleep(SEED_DELAY)

        # Progress
        if i % 10 == 0:
            print(f"\n  Progress: {i}/{len(SEEDED_TICKERS)} stocks processed, "
                  f"{trace_count} traces sent\n")

    # ========================================
    # SUMMARY
    # ========================================
    print()
    print("=" * 60)
    print("SEEDING COMPLETE")
    print("=" * 60)
    print(f"  Total traces: {trace_count}")
    print(f"  Skipped: {skipped}")
    print()

    # Overall accuracy
    known = [r for r in all_results if r["correct"] is not None]
    correct = [r for r in known if r["correct"]]
    if known:
        accuracy = len(correct) / len(known) * 100
        print(f"  Overall accuracy: {len(correct)}/{len(known)} ({accuracy:.1f}%)")
    else:
        print(f"  Overall accuracy: no outcomes available")
    print()

    # Accuracy by sector
    print("  Accuracy by sector:")
    sectors = sorted(set(r["sector"] for r in all_results))
    for sector in sectors:
        sector_known = [r for r in known if r["sector"] == sector]
        sector_correct = [r for r in sector_known if r["correct"]]
        if sector_known:
            acc = len(sector_correct) / len(sector_known) * 100
            print(f"    {sector:12s}: {len(sector_correct)}/{len(sector_known)} ({acc:.1f}%)")
        else:
            print(f"    {sector:12s}: no outcomes")
    print()

    # Decision distribution
    decisions = [r["decision"] for r in all_results]
    buy = decisions.count("BUY")
    sell = decisions.count("SELL")
    hold = decisions.count("HOLD")
    print(f"  Decision distribution: {buy} BUY, {sell} SELL, {hold} HOLD")
    print()

    # Accuracy by decision type
    print("  Accuracy by decision:")
    for dec in ["BUY", "SELL", "HOLD"]:
        dec_known = [r for r in known if r["decision"] == dec]
        dec_correct = [r for r in dec_known if r["correct"]]
        if dec_known:
            acc = len(dec_correct) / len(dec_known) * 100
            print(f"    {dec:5s}: {len(dec_correct)}/{len(dec_known)} ({acc:.1f}%)")
    print()

    # Accuracy by time window
    print("  Accuracy by time period:")
    for window in SEED_WINDOWS:
        label = window["label"]
        w_known = [r for r in known if r["window"] == label]
        w_correct = [r for r in w_known if r["correct"]]
        if w_known:
            acc = len(w_correct) / len(w_known) * 100
            print(f"    {label:15s}: {len(w_correct)}/{len(w_known)} ({acc:.1f}%)")
    print()

    # Save results to JSON for reference
    results_path = DATA_DIR / "seed_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  Results saved to: {results_path}")
    print()

    print("NOW CHECK PHOENIX:")
    print(f"  Go to https://app.phoenix.arize.com")
    print(f"  Open space shruthikashetty2309")
    print(f"  Project 'tradeshield' should show {trace_count}+ total traces")
    print()
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
