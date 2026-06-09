"""
Factor Calculations — 7 factors, each returns a score from -1 to +1.

Factors and academic sources:
1. Momentum (20%) — Jegadeesh & Titman (1993), Journal of Finance
2. Value (15%) — Fama & French (1993), Journal of Financial Economics
3. Quality (15%) — Fama & French (2015), Review of Financial Studies
4. Volatility (15%) — CBOE VIX (1993), universally used
5. Relative Strength (15%) — MSCI factor research
6. Mean Reversion (10%) — De Bondt & Thaler (1985), Journal of Finance
7. Volume (10%) — Weakest standalone, confirming signal

Each function:
- Takes stock data dict (from data_fetcher or cache)
- Returns a FactorScore with name, score, weight, and detail
"""

import logging
import pandas as pd
from tradeshield.config import FACTOR_WEIGHTS
from tradeshield.pipeline.validator import FactorScore

logger = logging.getLogger("tradeshield.model")


def _get_history_df(stock_data: dict) -> pd.DataFrame | None:
    """
    Extract history as a DataFrame from stock data.
    
    Handles both live data (history is already a DataFrame)
    and cached data (history is a dict of dicts).
    """
    history = stock_data.get("history")
    if history is None:
        return None

    if isinstance(history, pd.DataFrame):
        return history

    if isinstance(history, dict):
        df = pd.DataFrame.from_dict(history, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        # Ensure numeric columns
        for col in ["Close", "Volume", "MA_10", "MA_20", "MA_50"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    return None


def calculate_momentum(stock_data: dict) -> FactorScore:
    """
    Factor 1: Momentum — Is the stock trending up or down?

    Compares 10-day moving average to 50-day moving average.
    If 10-day > 50-day, stock is in an uptrend (positive score).
    If 10-day < 50-day, stock is in a downtrend (negative score).

    Source: Jegadeesh & Titman (1993) — momentum effect is the
    most replicated anomaly in financial markets.

    Score: (MA_10 - MA_50) / MA_50, clamped to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["momentum"]

    df = _get_history_df(stock_data)
    if df is None or len(df) < 50:
        logger.warning(f"model.momentum | ticker={ticker} | status=insufficient_data")
        return FactorScore(
            name="momentum", score=0.0, weight=weight,
            detail="Insufficient data for momentum calculation (need 50+ days)"
        )

    # Calculate MAs if not already present
    if "MA_10" not in df.columns or df["MA_10"].isna().all():
        df["MA_10"] = df["Close"].rolling(window=10).mean()
    if "MA_50" not in df.columns or df["MA_50"].isna().all():
        df["MA_50"] = df["Close"].rolling(window=50).mean()

    ma_10 = df["MA_10"].iloc[-1]
    ma_50 = df["MA_50"].iloc[-1]

    if pd.isna(ma_10) or pd.isna(ma_50) or ma_50 == 0:
        return FactorScore(
            name="momentum", score=0.0, weight=weight,
            detail="Moving averages unavailable"
        )

    # Raw score: how far apart the MAs are, as a percentage
    raw = (ma_10 - ma_50) / ma_50

    # Scale to [-1, +1] range (cap at ±10% divergence = ±1.0)
    score = max(-1.0, min(1.0, raw * 10))
    score = round(score, 2)

    direction = "uptrend" if score > 0 else "downtrend" if score < 0 else "flat"
    detail = (
        f"10-day MA (${ma_10:.2f}) {'above' if ma_10 > ma_50 else 'below'} "
        f"50-day MA (${ma_50:.2f}) — {direction} "
        f"({'+' if raw >= 0 else ''}{raw*100:.1f}% divergence)"
    )

    logger.info(f"model.momentum | ticker={ticker} | score={score} | detail={direction}")
    return FactorScore(name="momentum", score=score, weight=weight, detail=detail)


def calculate_value(stock_data: dict) -> FactorScore:
    """
    Factor 2: Value — Is the stock cheap or expensive?

    Compares the stock's P/E ratio to its sector average.
    Low P/E relative to sector = potentially undervalued (positive).
    High P/E relative to sector = potentially overvalued (negative).

    Source: Fama & French (1993) — value factor (HML) is one of
    the foundational factors in asset pricing.

    Score: (sector_avg_PE - stock_PE) / sector_avg_PE, clamped to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["value"]

    pe_ratio = stock_data.get("pe_ratio")
    sector_avg_pe = stock_data.get("sector_avg_pe")

    # If no P/E available, try to use a reasonable sector default
    if pe_ratio is None or pe_ratio <= 0:
        return FactorScore(
            name="value", score=0.0, weight=weight,
            detail=f"P/E ratio unavailable for {ticker} — neutral score"
        )

    if sector_avg_pe is None or sector_avg_pe <= 0:
        # Use broad market average P/E as fallback (~25 for S&P 500)
        sector_avg_pe = 25.0

    # Positive when stock is cheaper than sector (lower P/E = better value)
    raw = (sector_avg_pe - pe_ratio) / sector_avg_pe
    score = max(-1.0, min(1.0, raw * 2))  # Scale: 50% cheaper/more expensive = ±1.0
    score = round(score, 2)

    label = "undervalued" if score > 0.2 else "overvalued" if score < -0.2 else "fairly valued"
    detail = (
        f"P/E {pe_ratio:.1f} vs sector avg {sector_avg_pe:.1f} — "
        f"{label} ({'+' if raw >= 0 else ''}{raw*100:.1f}% relative)"
    )

    logger.info(f"model.value | ticker={ticker} | pe={pe_ratio:.1f} | score={score}")
    return FactorScore(name="value", score=score, weight=weight, detail=detail)


def calculate_quality(stock_data: dict) -> FactorScore:
    """
    Factor 3: Quality — Is the company fundamentally healthy?

    Compares profit margin to sector average.
    High margin = strong company (positive).
    Low margin = weak company (negative).

    Source: Fama & French (2015) — profitability factor in the
    5-factor model. Higher operating profitability → higher returns.

    Score: (stock_margin - sector_avg) / sector_avg, clamped to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["quality"]

    margin = stock_data.get("profit_margin")

    if margin is None:
        return FactorScore(
            name="quality", score=0.0, weight=weight,
            detail=f"Profit margin unavailable for {ticker} — neutral score"
        )

    # Sector average profit margin (approximate defaults by sector)
    sector = stock_data.get("sector", "unknown")
    sector_margins = {
        "tech": 0.20,       # Tech: ~20% average
        "energy": 0.10,     # Energy: ~10%
        "healthcare": 0.15, # Healthcare: ~15%
        "finance": 0.25,    # Finance: ~25%
        "consumer": 0.08,   # Consumer: ~8%
        "industrial": 0.10, # Industrial: ~10%
    }
    sector_avg = sector_margins.get(sector, 0.12)  # Default 12%

    if sector_avg == 0:
        sector_avg = 0.12

    raw = (margin - sector_avg) / abs(sector_avg)
    score = max(-1.0, min(1.0, raw * 2))
    score = round(score, 2)

    label = "strong" if score > 0.2 else "weak" if score < -0.2 else "average"
    detail = (
        f"Profit margin {margin*100:.1f}% vs sector avg {sector_avg*100:.1f}% — "
        f"{label} profitability"
    )

    logger.info(f"model.quality | ticker={ticker} | margin={margin:.3f} | score={score}")
    return FactorScore(name="quality", score=score, weight=weight, detail=detail)


def calculate_volatility(stock_data: dict) -> FactorScore:
    """
    Factor 4: Volatility — Is the market scared or calm?

    Assesses the current VIX level.
    Low VIX (below 15) = calm market, favorable for trading (positive).
    High VIX (above 30) = scared market, risky environment (negative).

    Source: CBOE (1993). VIX is universally used as the market's
    "fear gauge." Every institutional trading desk monitors it.

    Score: mapped from VIX level to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["volatility"]

    vix = stock_data.get("vix", 20.0)

    # VIX scoring (industry standard thresholds):
    # VIX 10 → +1.0 (very calm)
    # VIX 15 → +0.5 (calm)
    # VIX 20 → 0.0 (neutral)
    # VIX 25 → -0.5 (elevated)
    # VIX 30 → -0.75 (high fear)
    # VIX 40+ → -1.0 (extreme fear)
    score = -(vix - 20) / 20  # Linear mapping: VIX 20 = 0, VIX 40 = -1, VIX 0 = +1
    score = max(-1.0, min(1.0, score))
    score = round(score, 2)

    if vix < 15:
        label = "calm market"
    elif vix < 20:
        label = "slightly calm"
    elif vix < 25:
        label = "slightly elevated"
    elif vix < 30:
        label = "elevated fear"
    else:
        label = "high volatility"

    detail = f"VIX at {vix:.1f} — {label}"

    logger.info(f"model.volatility | ticker={ticker} | vix={vix:.1f} | score={score}")
    return FactorScore(name="volatility", score=score, weight=weight, detail=detail)


def calculate_relative_strength(stock_data: dict) -> FactorScore:
    """
    Factor 5: Relative Strength — stock vs its sector peers.

    Compares the stock's recent return to the sector average return.
    Outperforming peers = positive. Underperforming = negative.

    Source: MSCI factor research, Fama-French cross-sectional studies.

    Score: (stock_return - sector_return) scaled to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["relative_strength"]

    df = _get_history_df(stock_data)
    if df is None or len(df) < 20:
        return FactorScore(
            name="relative_strength", score=0.0, weight=weight,
            detail="Insufficient data for relative strength calculation"
        )

    # Calculate 1-month return for this stock
    close_now = df["Close"].iloc[-1]
    close_month_ago = df["Close"].iloc[-20] if len(df) >= 20 else df["Close"].iloc[0]

    if close_month_ago == 0 or pd.isna(close_month_ago):
        return FactorScore(
            name="relative_strength", score=0.0, weight=weight,
            detail="Unable to calculate return"
        )

    stock_return = (close_now - close_month_ago) / close_month_ago

    # Sector average return
    sector_return = stock_data.get("sector_avg_return", 0.0)
    if sector_return is None:
        sector_return = 0.0

    # Relative performance
    relative = stock_return - sector_return

    # Scale to [-1, +1] (±10% outperformance = ±1.0)
    score = max(-1.0, min(1.0, relative * 10))
    score = round(score, 2)

    label = "outperforming" if score > 0.2 else "underperforming" if score < -0.2 else "in line"
    detail = (
        f"Stock return {stock_return*100:+.1f}% vs sector {sector_return*100:+.1f}% — "
        f"{label} peers ({relative*100:+.1f}% relative)"
    )

    logger.info(f"model.rel_strength | ticker={ticker} | score={score}")
    return FactorScore(name="relative_strength", score=score, weight=weight, detail=detail)


def calculate_mean_reversion(stock_data: dict) -> FactorScore:
    """
    Factor 6: Mean Reversion — Has the stock moved too far too fast?

    Measures how far the current price is from its 20-day moving average.
    Price far below MA = oversold, might bounce up (positive).
    Price far above MA = overbought, might pull back (negative).

    This COMPLEMENTS momentum: momentum says "follow the trend,"
    mean reversion says "the trend may have gone too far."

    Source: De Bondt & Thaler (1985) — "Does the Stock Market Overreact?"
    Extreme movers tend to reverse. Published in Journal of Finance.

    Score: (MA_20 - price) / MA_20 scaled to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["mean_reversion"]

    df = _get_history_df(stock_data)
    if df is None or len(df) < 20:
        return FactorScore(
            name="mean_reversion", score=0.0, weight=weight,
            detail="Insufficient data for mean reversion calculation"
        )

    if "MA_20" not in df.columns or df["MA_20"].isna().all():
        df["MA_20"] = df["Close"].rolling(window=20).mean()

    current_price = df["Close"].iloc[-1]
    ma_20 = df["MA_20"].iloc[-1]

    if pd.isna(ma_20) or ma_20 == 0:
        return FactorScore(
            name="mean_reversion", score=0.0, weight=weight,
            detail="20-day moving average unavailable"
        )

    # How far price is from MA_20 (as percentage)
    deviation = (current_price - ma_20) / ma_20

    # INVERTED: positive when price is BELOW MA (oversold = buy signal)
    # negative when price is ABOVE MA (overbought = sell signal)
    raw = -deviation

    # Scale to [-1, +1] (±5% deviation = ±1.0)
    score = max(-1.0, min(1.0, raw * 20))
    score = round(score, 2)

    if deviation < -0.03:
        label = "oversold (potential bounce)"
    elif deviation > 0.03:
        label = "overbought (potential pullback)"
    else:
        label = "near average"

    detail = (
        f"Price ${current_price:.2f} is {deviation*100:+.1f}% from "
        f"20-day MA (${ma_20:.2f}) — {label}"
    )

    logger.info(f"model.mean_reversion | ticker={ticker} | deviation={deviation:.3f} | score={score}")
    return FactorScore(name="mean_reversion", score=score, weight=weight, detail=detail)


def calculate_volume(stock_data: dict) -> FactorScore:
    """
    Factor 7: Volume — Are other traders confirming the trend?

    Compares current trading volume to the 30-day average.
    High volume confirming the price trend = positive.
    Low volume = weak signal, less conviction.

    This is the weakest standalone predictor (hence lowest weight).
    It confirms or denies the other signals.

    Score: (current_volume / avg_volume - 1) scaled to [-1, +1]
    """
    ticker = stock_data.get("ticker", "UNKNOWN")
    weight = FACTOR_WEIGHTS["volume"]

    current_volume = stock_data.get("current_volume", 0)
    volume_avg = stock_data.get("volume_avg", 0)

    if volume_avg == 0 or current_volume == 0:
        return FactorScore(
            name="volume", score=0.0, weight=weight,
            detail="Volume data unavailable"
        )

    # Volume ratio (1.0 = average, 2.0 = double average)
    ratio = current_volume / volume_avg

    # Score: above average = positive, below = negative
    # 2x average = +1.0, 0.5x average = -1.0
    raw = ratio - 1.0
    score = max(-1.0, min(1.0, raw))
    score = round(score, 2)

    if ratio > 1.5:
        label = "high volume (strong conviction)"
    elif ratio > 1.1:
        label = "above average volume"
    elif ratio > 0.9:
        label = "average volume"
    elif ratio > 0.5:
        label = "below average volume"
    else:
        label = "very low volume (weak signal)"

    detail = f"Volume {current_volume:,.0f} vs avg {volume_avg:,.0f} ({ratio:.2f}x) — {label}"

    logger.info(f"model.volume | ticker={ticker} | ratio={ratio:.2f} | score={score}")
    return FactorScore(name="volume", score=score, weight=weight, detail=detail)


def calculate_all_factors(stock_data: dict) -> list[FactorScore]:
    """
    Calculate all 7 factors for a stock.

    Args:
        stock_data: Dict from data_fetcher or cache.

    Returns:
        List of 7 FactorScore objects.
    """
    return [
        calculate_momentum(stock_data),
        calculate_value(stock_data),
        calculate_quality(stock_data),
        calculate_volatility(stock_data),
        calculate_relative_strength(stock_data),
        calculate_mean_reversion(stock_data),
        calculate_volume(stock_data),
    ]
