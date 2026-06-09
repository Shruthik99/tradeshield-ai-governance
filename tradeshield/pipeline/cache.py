"""
Cache — saves and loads pre-fetched market data as JSON files.

Simple file-based storage in the /data folder.
No complex caching framework — just JSON files.

Why caching matters:
- Demo reliability: if Yahoo Finance is slow during judging, we use cached data
- Speed: cached data loads in milliseconds vs 1-2 seconds for live fetch
- Consistency: same data produces same results for debugging

Cache strategy:
- Pre-fetch all 36 stocks on Day 3 (run once)
- During demo: check cache first, live fetch as fallback
- During seeding (Day 6): use historical data from cache
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from tradeshield.config import DATA_DIR

logger = logging.getLogger("tradeshield.pipeline")


def save_to_cache(ticker: str, data: dict) -> bool:
    """
    Save stock data to a JSON file in the data/ directory.

    The history DataFrame is converted to a dict for JSON serialization.
    All other fields are stored as-is.

    Args:
        ticker: Stock ticker (used as filename).
        data: Stock data dict from fetch_stock_data().

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    try:
        ticker = ticker.upper().strip()
        filepath = DATA_DIR / f"{ticker}.json"

        # Convert DataFrame to serializable format
        cache_data = {}
        for key, value in data.items():
            if key == "history":
                # Convert DataFrame to dict of lists
                df = value.copy()
                df.index = df.index.strftime("%Y-%m-%d")
                cache_data["history"] = df.to_dict(orient="index")
            else:
                cache_data[key] = value

        cache_data["cached_at"] = datetime.now().isoformat()

        with open(filepath, "w") as f:
            json.dump(cache_data, f, indent=2, default=str)

        logger.info(
            f"pipeline.cache | ticker={ticker} | action=save | "
            f"file={filepath.name} | status=success"
        )
        return True

    except Exception as e:
        logger.error(
            f"pipeline.cache | ticker={ticker} | action=save | "
            f"status=error | error={str(e)[:200]}"
        )
        return False


def load_from_cache(ticker: str) -> dict | None:
    """
    Load stock data from a cached JSON file.

    Converts the history dict back to a format compatible with
    the trading model (dict of dicts with date keys).

    Args:
        ticker: Stock ticker to load.

    Returns:
        dict: Cached stock data, or None if not found.
    """
    try:
        ticker = ticker.upper().strip()
        filepath = DATA_DIR / f"{ticker}.json"

        if not filepath.exists():
            logger.info(
                f"pipeline.cache | ticker={ticker} | action=load | "
                f"status=not_found"
            )
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        logger.info(
            f"pipeline.cache | ticker={ticker} | action=load | "
            f"cached_at={data.get('cached_at', 'unknown')} | status=success"
        )
        return data

    except Exception as e:
        logger.error(
            f"pipeline.cache | ticker={ticker} | action=load | "
            f"status=error | error={str(e)[:200]}"
        )
        return None


def is_cached(ticker: str) -> bool:
    """Check if a stock has cached data."""
    ticker = ticker.upper().strip()
    filepath = DATA_DIR / f"{ticker}.json"
    return filepath.exists()


def get_cached_tickers() -> list[str]:
    """Return list of all cached ticker symbols."""
    tickers = []
    for f in DATA_DIR.glob("*.json"):
        tickers.append(f.stem.upper())
    return sorted(tickers)


def prefetch_all_stocks(tickers: list[str]) -> dict:
    """
    Fetch and cache data for all provided tickers.

    Args:
        tickers: List of ticker symbols to fetch.

    Returns:
        dict: Summary with counts of success/failure.
    """
    from tradeshield.pipeline.data_fetcher import fetch_stock_data

    results = {"success": 0, "failed": 0, "tickers_failed": []}

    total = len(tickers)
    for i, ticker in enumerate(tickers, 1):
        logger.info(
            f"pipeline.prefetch | progress={i}/{total} | ticker={ticker}"
        )

        data = fetch_stock_data(ticker)
        if data:
            saved = save_to_cache(ticker, data)
            if saved:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["tickers_failed"].append(ticker)
        else:
            results["failed"] += 1
            results["tickers_failed"].append(ticker)

    logger.info(
        f"pipeline.prefetch | total={total} | success={results['success']} | "
        f"failed={results['failed']}"
    )
    return results
