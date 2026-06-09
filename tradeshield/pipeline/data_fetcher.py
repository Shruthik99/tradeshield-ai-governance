"""
Data Fetcher — pulls market data from Yahoo Finance.

Fetches:
- Stock price data (OHLCV + history)
- VIX (market volatility index)
- Fundamental data (P/E ratio, profit margin)

Includes:
- Retry logic (3 attempts, 2-sec delay)
- 5-second timeout
- VIX fallback (default 20 if unavailable)
- Auto-uppercase tickers
- Structured logging

Source: Yahoo Finance via yfinance library (public, free data)
"""

import time
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from tradeshield.config import (
    YAHOO_TIMEOUT, YAHOO_RETRIES, YAHOO_RETRY_DELAY,
    VIX_DEFAULT, SECTOR_MAP
)

# Structured logging
logger = logging.getLogger("tradeshield.pipeline")


def fetch_stock_data(ticker: str, period: str = "3mo") -> dict | None:
    """
    Fetch stock data from Yahoo Finance.

    Args:
        ticker: Stock ticker symbol (e.g., "NVDA"). Auto-uppercased.
        period: How far back to fetch (default "3mo" = 3 months).

    Returns:
        dict with keys: ticker, sector, history (DataFrame), 
        current_price, volume_avg, pe_ratio, profit_margin, vix.
        Returns None if fetch fails after all retries.
    """
    ticker = ticker.upper().strip()
    sector = SECTOR_MAP.get(ticker, "unknown")

    for attempt in range(1, YAHOO_RETRIES + 1):
        try:
            logger.info(
                f"pipeline.fetch | ticker={ticker} | attempt={attempt}/{YAHOO_RETRIES} | "
                f"period={period} | status=starting"
            )

            # Fetch historical price data
            stock = yf.Ticker(ticker)
            history = stock.history(period=period, timeout=YAHOO_TIMEOUT)

            if history.empty:
                logger.warning(
                    f"pipeline.fetch | ticker={ticker} | attempt={attempt}/{YAHOO_RETRIES} | "
                    f"status=empty_data"
                )
                if attempt < YAHOO_RETRIES:
                    time.sleep(YAHOO_RETRY_DELAY)
                    continue
                return None

            # Get current price and volume
            current_price = float(history["Close"].iloc[-1])
            volume_avg = float(history["Volume"].mean())
            current_volume = float(history["Volume"].iloc[-1])

            # Calculate moving averages
            history["MA_10"] = history["Close"].rolling(window=10).mean()
            history["MA_20"] = history["Close"].rolling(window=20).mean()
            history["MA_50"] = history["Close"].rolling(window=50).mean()

            # Get fundamental data (P/E ratio, profit margin)
            pe_ratio = None
            profit_margin = None
            try:
                info = stock.info
                pe_ratio = info.get("trailingPE")
                profit_margin = info.get("profitMargins")
            except Exception as e:
                logger.warning(
                    f"pipeline.fetch | ticker={ticker} | "
                    f"status=fundamentals_unavailable | error={str(e)[:100]}"
                )

            # Fetch VIX
            vix = fetch_vix()

            rows = len(history)
            logger.info(
                f"pipeline.fetch | ticker={ticker} | rows={rows} | "
                f"price={current_price:.2f} | pe={pe_ratio} | "
                f"vix={vix:.1f} | status=success"
            )

            return {
                "ticker": ticker,
                "sector": sector,
                "history": history,
                "current_price": current_price,
                "current_volume": current_volume,
                "volume_avg": volume_avg,
                "pe_ratio": pe_ratio,
                "profit_margin": profit_margin,
                "vix": vix,
                "data_points": rows,
                "fetch_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(
                f"pipeline.fetch | ticker={ticker} | attempt={attempt}/{YAHOO_RETRIES} | "
                f"status=error | error={str(e)[:200]}"
            )
            if attempt < YAHOO_RETRIES:
                time.sleep(YAHOO_RETRY_DELAY)
            else:
                logger.error(
                    f"pipeline.fetch | ticker={ticker} | status=all_retries_failed"
                )
                return None

    return None


def fetch_vix() -> float:
    """
    Fetch current VIX (market volatility index) from Yahoo Finance.

    VIX thresholds (industry standard, source: CBOE):
    - Below 15: calm market
    - 15-25: normal volatility
    - Above 25: elevated fear
    - Above 30: high volatility

    Returns:
        float: Current VIX value, or VIX_DEFAULT (20.0) if unavailable.
    """
    try:
        vix_ticker = yf.Ticker("^VIX")
        vix_history = vix_ticker.history(period="5d", timeout=YAHOO_TIMEOUT)

        if not vix_history.empty:
            vix_value = float(vix_history["Close"].iloc[-1])
            logger.info(f"pipeline.vix | value={vix_value:.2f} | status=success")
            return vix_value
        else:
            logger.warning(f"pipeline.vix | status=empty_data | fallback={VIX_DEFAULT}")
            return VIX_DEFAULT

    except Exception as e:
        logger.warning(
            f"pipeline.vix | status=error | fallback={VIX_DEFAULT} | "
            f"error={str(e)[:100]}"
        )
        return VIX_DEFAULT


def fetch_sector_average(sector: str, metric: str = "return") -> float | None:
    """
    Calculate average performance for a sector.

    Used by the Relative Strength factor to compare a stock vs its peers.

    Args:
        sector: Sector name (e.g., "tech", "energy")
        metric: What to average ("return" for price change, "pe" for P/E)

    Returns:
        float: Sector average, or None if insufficient data.
    """
    sector_tickers = [t for t, s in SECTOR_MAP.items() if s == sector]

    if not sector_tickers:
        logger.warning(f"pipeline.sector | sector={sector} | status=no_tickers")
        return None

    values = []
    for t in sector_tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1mo", timeout=YAHOO_TIMEOUT)
            if not hist.empty and len(hist) >= 2:
                if metric == "return":
                    ret = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]
                    values.append(float(ret))
                elif metric == "pe":
                    info = stock.info
                    pe = info.get("trailingPE")
                    if pe and pe > 0:
                        values.append(float(pe))
        except Exception:
            continue

    if values:
        avg = sum(values) / len(values)
        logger.info(
            f"pipeline.sector | sector={sector} | metric={metric} | "
            f"tickers={len(values)}/{len(sector_tickers)} | avg={avg:.4f}"
        )
        return avg

    logger.warning(f"pipeline.sector | sector={sector} | status=no_data")
    return None
