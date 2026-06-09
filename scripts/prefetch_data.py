"""
Pre-fetch Script — downloads and caches market data for all 36 stocks.

Run this once to populate the /data folder with JSON files.
After this, the demo doesn't depend on live Yahoo Finance.

Usage: python scripts/prefetch_data.py

No Gemini calls. No API key usage. Just Yahoo Finance (free, public).
"""

import sys
import logging
from datetime import datetime

# Set up logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tradeshield.pipeline")

from tradeshield.config import SEEDED_TICKERS, SECTOR_MAP
from tradeshield.pipeline.cache import prefetch_all_stocks, get_cached_tickers


def main():
    print("=" * 60)
    print("TradeShield — Pre-fetch Market Data")
    print("=" * 60)
    print()
    print(f"Stocks to fetch: {len(SEEDED_TICKERS)}")
    print(f"Sectors: {len(set(SECTOR_MAP.values()))}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This fetches real market data from Yahoo Finance.")
    print("No Gemini calls. No API key usage.")
    print()

    # Run pre-fetch
    results = prefetch_all_stocks(SEEDED_TICKERS)

    # Summary
    print()
    print("=" * 60)
    print("PRE-FETCH COMPLETE")
    print("=" * 60)
    print(f"  Success: {results['success']}/{len(SEEDED_TICKERS)}")
    print(f"  Failed:  {results['failed']}/{len(SEEDED_TICKERS)}")

    if results["tickers_failed"]:
        print(f"  Failed tickers: {', '.join(results['tickers_failed'])}")

    # Show cached tickers
    cached = get_cached_tickers()
    print()
    print(f"Cached tickers ({len(cached)}):")

    # Group by sector
    sectors = {}
    for t in cached:
        s = SECTOR_MAP.get(t, "unknown")
        sectors.setdefault(s, []).append(t)

    for sector, tickers in sorted(sectors.items()):
        print(f"  {sector}: {', '.join(tickers)}")

    print()
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data saved to: data/*.json")
    print("=" * 60)

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
