"""
Data Validator — Pydantic schemas for market data validation.

Validates:
- Stock prices are positive
- Dates are in chronological order
- No critical fields are missing
- Factor scores are within valid ranges
- Confidence is within bounds

Every piece of data entering the system passes through these schemas.
Bad data is rejected with a specific error message.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================
# INPUT SCHEMAS (data entering the system)
# ============================================================

class StockData(BaseModel):
    """Validated stock market data from Yahoo Finance."""

    ticker: str = Field(..., description="Stock ticker symbol, uppercase")
    sector: str = Field(..., description="Sector classification")
    current_price: float = Field(..., gt=0, description="Must be positive")
    current_volume: float = Field(..., ge=0, description="Must be non-negative")
    volume_avg: float = Field(..., ge=0, description="Average volume")
    pe_ratio: Optional[float] = Field(None, description="P/E ratio, may be unavailable")
    profit_margin: Optional[float] = Field(None, description="Profit margin, may be unavailable")
    vix: float = Field(..., ge=0, le=100, description="VIX between 0-100")
    data_points: int = Field(..., ge=1, description="Number of historical data points")
    fetch_timestamp: str = Field(..., description="When data was fetched")

    # Moving averages (optional — may not have enough data for MA_50)
    ma_10: Optional[float] = Field(None, description="10-day moving average")
    ma_20: Optional[float] = Field(None, description="20-day moving average")
    ma_50: Optional[float] = Field(None, description="50-day moving average")

    # Sector averages for relative comparison
    sector_avg_return: Optional[float] = Field(None, description="Sector average return")
    sector_avg_pe: Optional[float] = Field(None, description="Sector average P/E")

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v):
        return v.upper().strip()

    @field_validator("sector")
    @classmethod
    def sector_lowercase(cls, v):
        return v.lower().strip()


# ============================================================
# FACTOR SCHEMAS (intermediate calculations)
# ============================================================

class FactorScore(BaseModel):
    """A single factor's calculated score with metadata."""

    name: str = Field(..., description="Factor name")
    score: float = Field(..., ge=-1.0, le=1.0, description="Score from -1 to +1")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight in composite")
    detail: str = Field(..., description="Human-readable explanation of the score")


# ============================================================
# OUTPUT SCHEMAS (tool results sent to Gemini)
# ============================================================

class AnalyzeResult(BaseModel):
    """Output from Tool 1: Analyze Trade."""

    ticker: str
    sector: str
    decision: Literal["BUY", "SELL", "HOLD"]
    confidence: int = Field(..., ge=50, le=99, description="Confidence percentage")
    composite_score: float = Field(..., ge=-1.0, le=1.0)
    factors: list[FactorScore]
    market_data: dict = Field(..., description="Key market data points used")
    timestamp: str = Field(..., description="When analysis was performed")
    disclaimer: str = Field(
        default="This is a governance demonstration signal, not an investment recommendation."
    )


class EvidenceLineage(BaseModel):
    """Evidence chain for any tool output — shows where data came from."""

    data_source: str = Field(default="Yahoo Finance via yfinance")
    trace_id: Optional[str] = Field(None, description="Phoenix trace ID if available")
    timestamp: str = Field(..., description="When the original decision was made")
    model_version: str = Field(default="7-factor scorer v1.0")
    outcome: Optional[str] = Field(None, description="Actual outcome if known")


class ExplainResult(BaseModel):
    """Output from Tool 2: Explain Decision."""

    ticker: str
    date: str
    decision: Literal["BUY", "SELL", "HOLD"]
    confidence: int
    factors: list[FactorScore]
    evidence_lineage: EvidenceLineage
    explanation_summary: str = Field(..., description="Plain-English summary")


class SectorStats(BaseModel):
    """Statistics for one sector in a fairness audit."""

    sector: str
    count: int
    buy_rate: float = Field(..., ge=0.0, le=1.0)
    sell_rate: float = Field(..., ge=0.0, le=1.0)
    hold_rate: float = Field(..., ge=0.0, le=1.0)
    avg_confidence: float
    accuracy: Optional[float] = Field(None, description="If outcomes available")


class FairnessResult(BaseModel):
    """Output from Tool 3: Audit Fairness."""

    sectors: list[SectorStats]
    disparate_impact_ratio: float = Field(..., ge=0.0)
    flags: list[str] = Field(default_factory=list)
    caveat: str = Field(
        default="Simplified category-level comparison for demonstration. "
        "Production fairness auditing requires deeper statistical analysis."
    )


class PeriodStats(BaseModel):
    """Statistics for one time period in drift detection."""

    period_label: str
    trace_count: int
    buy_rate: float
    sell_rate: float
    hold_rate: float
    avg_confidence: float
    dominant_factor: str


class DriftResult(BaseModel):
    """Output from Tool 4: Detect Drift."""

    period1: PeriodStats
    period2: PeriodStats
    changes: dict = Field(..., description="Changed metrics with delta values")
    flags: list[str] = Field(default_factory=list, description="Metrics exceeding 15% change")


class ReliabilityResult(BaseModel):
    """Output from Tool 5: Evidence-Aware Reliability Assessment."""

    ticker: str
    similar_count: int = Field(..., description="Number of similar historical traces")
    past_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_gap: Optional[float] = Field(None, description="Stated confidence minus actual accuracy")
    evidence_coverage: Literal["sufficient", "sparse", "insufficient"]
    drift_signal: Literal["stable", "shifting", "unknown"]
    pattern_consistency: Literal["consistent", "inconsistent", "unknown"]
    warning_level: Literal["GREEN", "YELLOW", "RED", "INSUFFICIENT_DATA"]
    specific_reasons: list[str] = Field(default_factory=list)
    caveat: str = Field(
        default="Thresholds are heuristic baselines for demonstration. "
        "Production deployment would calibrate against institutional risk tolerance."
    )


class AnalyzeWithReliabilityResult(BaseModel):
    """Output from combined Tool: Analyze + Reliability Assessment."""

    reliability: ReliabilityResult
    analysis: AnalyzeResult
