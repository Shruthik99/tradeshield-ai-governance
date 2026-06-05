"""
Configuration for TradeShield.
Loads environment variables and defines project constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_COLLECTOR_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT",
    "https://app.phoenix.arize.com/s/shruthikashetty2309/v1/traces"
)

# --- Project Paths ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- Trading Model Settings ---
FACTOR_WEIGHTS = {
    "momentum": 0.20,         # Jegadeesh & Titman (1993) — strongest signal
    "value": 0.15,            # Fama-French (1993) — P/E relative to sector
    "quality": 0.15,          # Fama-French 5-factor (2015) — profit margins
    "volatility": 0.15,       # CBOE VIX — market regime indicator
    "relative_strength": 0.15, # MSCI factor research — stock vs sector peers
    "mean_reversion": 0.10,   # De Bondt & Thaler (1985) — oversold/overbought
    "volume": 0.10,           # Weakest standalone — activity confirmation
}

BUY_THRESHOLD = 0.3
SELL_THRESHOLD = -0.3
CONFIDENCE_MIN = 50
CONFIDENCE_MAX = 99

# --- Sectors ---
SECTOR_MAP = {
    "NVDA": "tech", "AAPL": "tech", "MSFT": "tech", "GOOGL": "tech",
    "META": "tech", "AMZN": "tech", "TSLA": "tech", "AMD": "tech",
    "INTC": "tech", "CRM": "tech",
    "XOM": "energy", "CVX": "energy", "COP": "energy",
    "SLB": "energy", "OXY": "energy",
    "JNJ": "healthcare", "PFE": "healthcare", "UNH": "healthcare",
    "ABBV": "healthcare", "MRK": "healthcare",
    "JPM": "finance", "GS": "finance", "BAC": "finance",
    "MS": "finance", "V": "finance", "MA": "finance",
    "WMT": "consumer", "NKE": "consumer", "SBUX": "consumer",
    "MCD": "consumer", "DIS": "consumer",
    "BA": "industrial", "CAT": "industrial", "GE": "industrial",
    "HON": "industrial", "UPS": "industrial",
}

SEEDED_TICKERS = list(SECTOR_MAP.keys())

# --- Pipeline Settings ---
YAHOO_TIMEOUT = 5  # seconds
YAHOO_RETRIES = 3
YAHOO_RETRY_DELAY = 2  # seconds
VIX_DEFAULT = 20.0  # neutral VIX fallback

# --- Phoenix Settings ---
PHOENIX_QUERY_TIMEOUT = 10  # seconds

# --- Reliability Assessment Thresholds ---
# These are heuristic baselines for demonstration.
# Production would calibrate against institutional risk tolerance.
RELIABILITY_GREEN_THRESHOLD = 0.70
RELIABILITY_YELLOW_THRESHOLD = 0.50
MIN_SIMILAR_TRACES = 5
SUFFICIENT_EVIDENCE_COUNT = 10
VIX_SIMILARITY_RANGE = 5  # ±5 points

# --- Gemini Model ---
GEMINI_MODEL = "gemini-2.5-flash"  # Verified on Day 2, may update
