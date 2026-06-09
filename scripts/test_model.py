"""
Run the trading model on cached stock data.

Runs the 7-factor model on several stocks from different sectors
and prints complete factor breakdowns and decisions.

No Gemini calls. No API key usage. Uses pre-fetched cached data.

Usage: python scripts/test_model.py
"""

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from tradeshield.pipeline.cache import load_from_cache
from tradeshield.model.factors import calculate_all_factors
from tradeshield.model.scorer import score_stock, format_decision_summary


# Test stocks — one from each sector
TEST_TICKERS = ["NVDA", "XOM", "JNJ", "JPM", "WMT", "BA"]


def main():
    print("=" * 60)
    print("TradeShield — Day 4 Trading Model Test")
    print("=" * 60)
    print()
    print("Running 7-factor model on cached data.")
    print("No Gemini calls. No API usage.")
    print()

    results = []
    
    for ticker in TEST_TICKERS:
        # Load cached data
        data = load_from_cache(ticker)
        if data is None:
            print(f"⚠ No cached data for {ticker}. Run prefetch_data.py first.")
            continue

        # Calculate all 7 factors
        factors = calculate_all_factors(data)

        # Score and decide
        result = score_stock(ticker, data, factors)
        results.append(result)

        # Print formatted summary
        print(format_decision_summary(result))
        print()

    # Summary table
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Ticker':8s} {'Sector':12s} {'Decision':8s} {'Conf':5s} {'Score':8s} {'Top Factor'}")
    print("-" * 70)

    for r in results:
        # Find the factor with highest absolute contribution
        top_factor = max(r.factors, key=lambda f: abs(f.score * f.weight))
        print(
            f"{r.ticker:8s} {r.sector:12s} {r.decision:8s} {r.confidence}%  "
            f"{r.composite_score:+.3f}  {top_factor.name} ({top_factor.score:+.2f})"
        )

    # Decision distribution
    decisions = [r.decision for r in results]
    buy_count = decisions.count("BUY")
    sell_count = decisions.count("SELL")
    hold_count = decisions.count("HOLD")

    print()
    print(f"Distribution: {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD")
    print(f"Average confidence: {sum(r.confidence for r in results) / len(results):.0f}%")
    print()
    print("Day 4 model test complete.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
