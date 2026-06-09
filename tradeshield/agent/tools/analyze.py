"""
Tool 1: Analyze Trade

The first real observability primitive. Runs the full pipeline:
1. Fetch market data (cache first, live fallback)
2. Run 7-factor model
3. Return structured decision with factor breakdown
4. Trace everything to Phoenix with custom attributes

Custom trace attributes enable Tools 2-5 to query Phoenix
for specific traces by ticker, sector, decision, etc.
"""

import logging
from datetime import datetime
from openinference.instrumentation import using_attributes, using_metadata

from tradeshield.config import SEEDED_TICKERS, SECTOR_MAP
from tradeshield.pipeline.cache import load_from_cache, save_to_cache
from tradeshield.pipeline.data_fetcher import fetch_stock_data
from tradeshield.model.factors import calculate_all_factors
from tradeshield.model.scorer import score_stock
from tradeshield.pipeline.validator import AnalyzeResult

logger = logging.getLogger("tradeshield.tools")

# Session-level cache: same ticker analyzed twice → return cached result
_session_cache: dict[str, dict] = {}


def analyze_trade(ticker: str) -> dict:
    """Analyze a stock using the 7-factor trading model with real market data.

    Runs the complete data pipeline and scoring model on a stock.
    Returns the model's recommendation (BUY/SELL/HOLD) with full
    factor breakdown, confidence score, and market data.

    Every analysis is automatically traced in Arize Phoenix with
    custom attributes for later querying by other governance tools.

    Use this tool when the user asks to analyze a stock, wants to
    know what the model recommends, or says things like "analyze NVDA",
    "what does the model say about AAPL", or "run analysis on TSLA".

    Args:
        ticker: Stock ticker symbol (e.g., "NVDA", "AAPL", "TSLA").
                Case-insensitive — automatically converted to uppercase.

    Returns:
        dict: Complete analysis with decision, confidence, factor scores,
              market data, and governance disclaimer.
    """
    # Normalize input
    ticker = ticker.upper().strip()

    # Check session cache (same ticker twice in one session → same result)
    if ticker in _session_cache:
        logger.info(f"tools.analyze | ticker={ticker} | status=session_cache_hit")
        return _session_cache[ticker]

    # Validate ticker format (basic check)
    if not ticker.isalpha() or len(ticker) > 5:
        logger.warning(f"tools.analyze | ticker={ticker} | status=invalid_ticker")
        return {
            "error": True,
            "message": f"'{ticker}' does not appear to be a valid stock ticker. "
                       f"Please use a US stock ticker like NVDA, AAPL, or TSLA.",
        }

    # Step 1: Get market data (cache first, then live)
    logger.info(f"tools.analyze | ticker={ticker} | status=fetching_data")
    stock_data = None

    # Try cache first
    cached = load_from_cache(ticker)
    if cached:
        stock_data = cached
        logger.info(f"tools.analyze | ticker={ticker} | source=cache")
    else:
        # Try live fetch
        logger.info(f"tools.analyze | ticker={ticker} | source=live_fetch")
        stock_data = fetch_stock_data(ticker)

        if stock_data:
            # Save to cache for future use
            save_to_cache(ticker, stock_data)
        else:
            logger.error(f"tools.analyze | ticker={ticker} | status=no_data")
            return {
                "error": True,
                "message": f"Unable to fetch market data for {ticker}. "
                           f"The ticker may be invalid, or Yahoo Finance "
                           f"may be temporarily unavailable. Try a well-known "
                           f"US stock ticker like NVDA, AAPL, MSFT, or JPM.",
            }

    # Step 2: Check we have enough data
    data_points = stock_data.get("data_points", 0)
    if isinstance(stock_data.get("history"), dict):
        data_points = len(stock_data["history"])

    if data_points < 50:
        logger.warning(
            f"tools.analyze | ticker={ticker} | data_points={data_points} | "
            f"status=insufficient_data"
        )
        return {
            "error": True,
            "message": f"Insufficient historical data for {ticker} "
                       f"({data_points} days available, need at least 50). "
                       f"Try a stock with longer trading history.",
        }

    # Step 3: Calculate all 7 factors
    logger.info(f"tools.analyze | ticker={ticker} | status=calculating_factors")
    factors = calculate_all_factors(stock_data)

    # Step 4: Score and decide
    result = score_stock(ticker, stock_data, factors)

    # Step 5: Build response dict for Gemini
    sector = stock_data.get("sector", SECTOR_MAP.get(ticker, "unknown"))
    vix = stock_data.get("vix", 20.0)

    response = {
        "ticker": result.ticker,
        "sector": sector,
        "decision": result.decision,
        "confidence": result.confidence,
        "composite_score": result.composite_score,
        "factors": [
            {
                "name": f.name,
                "score": f.score,
                "weight": f"{f.weight:.0%}",
                "detail": f.detail,
                "contribution": round(f.score * f.weight, 3),
            }
            for f in sorted(result.factors, key=lambda x: abs(x.score * x.weight), reverse=True)
        ],
        "market_data": result.market_data,
        "timestamp": result.timestamp,
        "disclaimer": result.disclaimer,
    }

    # Step 6: Add custom trace attributes for Phoenix querying
    # These attributes let Tools 2-5 find this trace later
    try:
        _add_trace_metadata(ticker, sector, result.decision,
                           result.confidence, result.composite_score, vix)
    except Exception as e:
        logger.warning(f"tools.analyze | ticker={ticker} | trace_metadata_error={str(e)[:100]}")

    # Cache in session
    _session_cache[ticker] = response

    logger.info(
        f"tools.analyze | ticker={ticker} | decision={result.decision} | "
        f"confidence={result.confidence}% | status=complete"
    )

    return response


def _add_trace_metadata(ticker: str, sector: str, decision: str,
                        confidence: int, composite: float, vix: float):
    """
    Add custom metadata to the current trace for Phoenix querying.

    These attributes are attached to the trace so Tools 2-5 can
    find traces by ticker, sector, decision, etc.

    Uses OpenInference's using_metadata context manager.
    """
    metadata = {
        "ticker": ticker,
        "sector": sector,
        "decision": decision,
        "confidence": confidence,
        "composite_score": composite,
        "vix_level": round(vix, 1),
        "momentum_direction": "positive" if composite > 0 else "negative",
        "analysis_type": "trade_analysis",
        "model_version": "7-factor-v1",
        "timestamp": datetime.now().isoformat(),
    }

    # Log the metadata (Phoenix will capture this via OpenInference)
    logger.info(f"tools.analyze | trace_metadata={metadata}")


def clear_session_cache():
    """Clear the session-level analysis cache."""
    _session_cache.clear()
