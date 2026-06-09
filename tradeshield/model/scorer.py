"""
Scorer — combines 7 factor scores into a trading decision.

Takes all factor scores, computes a weighted composite,
determines BUY/SELL/HOLD, and calculates confidence.

All arithmetic. No AI. No machine learning.

Decision logic:
- Composite score > +0.3  → BUY
- Composite score < -0.3  → SELL
- Between -0.3 and +0.3   → HOLD

Confidence:
- Maps |composite_score| to 50-99% range
- Higher absolute score = higher confidence
- Score of 0.3 (threshold) = ~65% confidence
- Score of 1.0 (maximum) = 99% confidence

Weights (from config.py, sourced from academic literature):
- Momentum: 20% (Jegadeesh & Titman, 1993)
- Value: 15% (Fama & French, 1993)
- Quality: 15% (Fama & French, 2015)
- Volatility: 15% (CBOE VIX)
- Relative Strength: 15% (MSCI research)
- Mean Reversion: 10% (De Bondt & Thaler, 1985)
- Volume: 10% (weakest standalone)
"""

import logging
from datetime import datetime
from tradeshield.config import BUY_THRESHOLD, SELL_THRESHOLD, CONFIDENCE_MIN, CONFIDENCE_MAX
from tradeshield.pipeline.validator import FactorScore, AnalyzeResult

logger = logging.getLogger("tradeshield.model")


def calculate_composite(factors: list[FactorScore]) -> float:
    """
    Calculate weighted composite score from all factors.

    Args:
        factors: List of FactorScore objects (each has score and weight).

    Returns:
        float: Composite score from -1.0 to +1.0
    """
    composite = sum(f.score * f.weight for f in factors)
    # Clamp to [-1, +1] (shouldn't exceed, but safety check)
    composite = max(-1.0, min(1.0, composite))
    return round(composite, 3)


def determine_decision(composite: float) -> str:
    """
    Determine BUY/SELL/HOLD from composite score.

    Args:
        composite: Weighted composite score (-1.0 to +1.0)

    Returns:
        str: "BUY", "SELL", or "HOLD"
    """
    if composite > BUY_THRESHOLD:
        return "BUY"
    elif composite < SELL_THRESHOLD:
        return "SELL"
    else:
        return "HOLD"


def calculate_confidence(composite: float) -> int:
    """
    Map composite score magnitude to confidence percentage.

    Score of 0.0 → 50% (minimum, no conviction)
    Score of 0.3 → ~65% (threshold, mild conviction)
    Score of 1.0 → 99% (maximum conviction)

    Args:
        composite: Weighted composite score (-1.0 to +1.0)

    Returns:
        int: Confidence from 50 to 99
    """
    # Map |score| from [0, 1] to [50, 99]
    magnitude = abs(composite)
    confidence = CONFIDENCE_MIN + magnitude * (CONFIDENCE_MAX - CONFIDENCE_MIN)
    return int(min(CONFIDENCE_MAX, max(CONFIDENCE_MIN, confidence)))


def score_stock(ticker: str, stock_data: dict, factors: list[FactorScore]) -> AnalyzeResult:
    """
    Produce a complete trading decision for a stock.

    This is the main function that combines everything:
    1. Calculate composite from factor scores
    2. Determine decision (BUY/SELL/HOLD)
    3. Calculate confidence
    4. Package into AnalyzeResult schema

    Args:
        ticker: Stock ticker symbol
        stock_data: Market data dict from data_fetcher or cache
        factors: List of calculated FactorScore objects

    Returns:
        AnalyzeResult: Complete decision with all metadata
    """
    ticker = ticker.upper().strip()

    # Calculate composite score
    composite = calculate_composite(factors)

    # Determine decision
    decision = determine_decision(composite)

    # Calculate confidence
    confidence = calculate_confidence(composite)

    # Build market data summary
    market_data = {
        "price": round(stock_data.get("current_price", 0), 2),
        "volume": int(stock_data.get("current_volume", 0)),
        "volume_avg": int(stock_data.get("volume_avg", 0)),
        "pe_ratio": round(stock_data.get("pe_ratio", 0) or 0, 1) or None,
        "profit_margin": round((stock_data.get("profit_margin", 0) or 0) * 100, 1) or None,
        "vix": round(stock_data.get("vix", 20.0), 1),
        "data_points": stock_data.get("data_points", 0),
        "sector": stock_data.get("sector", "unknown"),
    }

    # Build result
    result = AnalyzeResult(
        ticker=ticker,
        sector=stock_data.get("sector", "unknown"),
        decision=decision,
        confidence=confidence,
        composite_score=composite,
        factors=factors,
        market_data=market_data,
        timestamp=datetime.now().isoformat(),
    )

    # Log the decision
    logger.info(
        f"model.score | ticker={ticker} | decision={decision} | "
        f"confidence={confidence}% | composite={composite:.3f} | "
        f"factors={','.join(f'{f.name}={f.score}' for f in factors)}"
    )

    return result


def format_decision_summary(result: AnalyzeResult) -> str:
    """
    Create a human-readable summary of a trading decision.

    Used for logging and debugging. The agent uses Gemini to
    create the actual user-facing explanation.

    Args:
        result: AnalyzeResult from score_stock()

    Returns:
        str: Formatted summary string
    """
    lines = [
        f"{'='*50}",
        f"TRADING MODEL DECISION: {result.ticker}",
        f"{'='*50}",
        f"Decision: {result.decision} ({result.confidence}% confidence)",
        f"Composite Score: {result.composite_score:+.3f}",
        f"",
        f"Factor Breakdown:",
    ]

    # Sort factors by absolute contribution (weight * score)
    sorted_factors = sorted(
        result.factors,
        key=lambda f: abs(f.score * f.weight),
        reverse=True
    )

    for f in sorted_factors:
        contribution = f.score * f.weight
        lines.append(
            f"  {f.name:20s} | score: {f.score:+.2f} | "
            f"weight: {f.weight:.0%} | contribution: {contribution:+.3f}"
        )
        lines.append(f"  {'':20s} | {f.detail}")

    lines.extend([
        f"",
        f"Market Data:",
        f"  Price: ${result.market_data.get('price', 'N/A')}",
        f"  VIX: {result.market_data.get('vix', 'N/A')}",
        f"  P/E: {result.market_data.get('pe_ratio', 'N/A')}",
        f"  Sector: {result.market_data.get('sector', 'N/A')}",
        f"{'='*50}",
    ])

    return "\n".join(lines)
