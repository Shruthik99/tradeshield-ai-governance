# TradeShield

**Operational observability for AI-assisted financial decision systems.**

TradeShield is a proof-of-concept AI governance agent that provides continuous observability, explainability, and operational accountability for AI-assisted trading decisions. Built for the [Google Cloud Rapid Agent Hackathon 2026](https://rapid-agent.devpost.com/) — Arize track.

> ⚠️ This is a hackathon proof of concept. Not a production compliance solution. Not financial advice.

---

## The Problem

Financial institutions are integrating AI into trading workflows faster than governance systems can keep up. Existing compliance processes struggle to explain AI-assisted decisions, monitor behavioral drift, detect unreliable outputs, and maintain audit-ready evidence trails.

Regulators are responding:
- The **SEC's 2026 examination priorities** include AI oversight ([sec.gov](https://www.sec.gov/about/reports-publications/2026-examination-priorities))
- **Texas TRAIGA** (effective Jan 2026) requires AI audit trails with penalties up to $200,000
- **Gartner** projects the AI governance market at $492M in 2026, growing to $1B by 2030

Real consequences exist: Knight Capital lost $440M in 45 minutes from an ungoverned algorithm. Goldman Sachs/Apple were fined $89M by the CFPB for unexplainable automated decisions.

---

## What TradeShield Does

A compliance officer types questions in plain English. The agent investigates using real market data and stored decision records, then provides evidence-backed answers with full provenance.

**Five observability primitives:**

**1. Decision Tracing** — Every AI trading decision automatically recorded with full evidence lineage (inputs, factor scores, confidence, timestamps, source provenance).

**2. Plain-English Explainability** — Translates AI decision factors into structured explanations with evidence citations. Answers: "Why did the AI recommend selling NVDA?"

**3. Bias & Category-Level Outcome Monitoring** — Detects statistically significant disparities across stock sectors and categories. Calculates disparate impact ratios and flags anomalies.

**4. Decision-Pattern Drift Monitoring** — Tracks changes in output behavior, confidence distributions, factor dominance, and recommendation consistency across time periods.

**5. Evidence-Aware Reliability Assessment** — Evaluates historical accuracy, evidence coverage, confidence calibration, drift signals, and pattern consistency before presenting recommendations. Warns when AI confidence exceeds actual track record.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  LAYER 1: REASONING                             │
│  Gemini (reasoning engine, only AI in project)  │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  LAYER 2: GOVERNANCE                            │
│  Decision tracing · Evidence lineage ·          │
│  Plain-English explainability                   │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  LAYER 3: OBSERVABILITY                         │
│  Drift monitoring · Reliability assessment ·    │
│  Bias monitoring · Confidence calibration       │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  LAYER 4: HUMAN OVERSIGHT                       │
│  Reliability warnings · Escalation signals ·    │
│  Review prompts                                 │
└─────────────────────────────────────────────────┘
```

**Data flow:**
```
Yahoo Finance (real market data)
  → Data Pipeline (validate, transform, cache)
    → Trading Model (7-factor rule-based scorer, NOT AI)
      → Decision + trace → OpenInference → Arize Phoenix Cloud
        → Agent queries traces via Phoenix MCP/REST
          → Evidence-backed response to user
```

---

## Tech Stack

| Component | Purpose |
|-----------|---------|
| Google ADK | Agent framework |
| Gemini | Reasoning engine (only AI — hackathon requirement) |
| Arize Phoenix Cloud | Trace storage and observability |
| Phoenix MCP Server | Agent queries own traces |
| OpenInference | Auto-tracing of all agent actions |
| Yahoo Finance | Real market data (public, free) |
| pandas + pydantic | Data processing and validation |
| FastAPI | API server |
| React + CopilotKit | Frontend (AG-UI protocol) |
| Cloud Run | Hosting |

**The trading model uses mathematical formulas (moving averages, P/E ratios, profit margins, weighted scoring), not AI.** It generates auditable decision streams for governance demonstration.

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Google Cloud account with Gemini API key
- Arize Phoenix Cloud account with API key

### Installation

```bash
git clone https://github.com/Shruthik99/tradeshield-ai-governance.git
cd tradeshield-ai-governance
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
pip install -e .
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```
GOOGLE_API_KEY=your-gemini-key
PHOENIX_API_KEY=your-phoenix-key
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-space/v1/traces
```

### Run Locally

```bash
# Seed historical data (first time only)
python scripts/seed.py

# Test the agent
python scripts/test_agent.py

# Run with ADK web UI
adk web .
```

### Deploy to Cloud Run

```bash
gcloud run deploy tradeshield \
  --project tradeshield-496721 \
  --region us-central1 \
  --source .
```

---

## How It Works

### The Trading Model (what's being observed)

A simplified multi-factor scoring system using seven signals:
- **Momentum** (20%): 10-day vs 50-day moving average — Jegadeesh & Titman (1993)
- **Value** (15%): P/E ratio vs sector average — Fama & French (1993)
- **Quality** (15%): profit margin vs sector average — Fama & French (2015)
- **Volatility** (15%): VIX level assessment — CBOE (1993)
- **Relative Strength** (15%): stock vs sector performance — MSCI factor research
- **Mean Reversion** (10%): distance from 20-day moving average — De Bondt & Thaler (1985)
- **Volume** (10%): current vs average trading volume

This is arithmetic, not AI. The model exists to generate realistic decision streams for governance demonstration. It is not a production trading strategy. Factor weights are heuristic starting points reflecting relative academic evidence strength, not optimized values.

### The Governance Agent (what does the observing)

Powered by Gemini as the reasoning engine. When a compliance officer asks a question, the agent selects the appropriate observability primitive, queries Phoenix traces, and provides evidence-backed answers.

The agent enforces 7 guardrails: scope limitation, no financial advice, no hallucination, tool enforcement, honest limitations, no regulatory claims, and model-agnostic clarity.

### The Self-Assessment Loop

The reliability assessment primitive queries the agent's own historical traces via Phoenix MCP. It finds past decisions made under similar conditions (same sector, similar VIX level, same momentum direction), calculates actual accuracy, and compares it to the model's stated confidence.

The assessment evaluates five dimensions:
- **Evidence coverage**: sufficient or sparse historical data?
- **Past accuracy**: what percentage of similar decisions were correct?
- **Confidence gap**: stated confidence vs actual track record
- **Drift signal**: has the model's behavior shifted recently?
- **Pattern consistency**: were similar cases treated consistently?

This is evidence-based confidence calibration through trace querying — not machine learning or model retraining.

Note: Reliability thresholds (GREEN >70%, YELLOW 50-70%, RED <50%) are heuristic baselines for demonstration. Production deployment would calibrate against institutional risk tolerance.

---

## Project Structure

```
tradeshield-ai-governance/
├── app/                        ← ADK web entry point
│   ├── __init__.py
│   └── agent.py                ← root_agent definition
├── tradeshield/                ← Core package
│   ├── config.py               ← Settings, weights, sector mappings
│   ├── main.py                 ← FastAPI entry point
│   ├── agent/                  ← System prompt and tools
│   │   ├── prompt.py           ← 7 guardrails, tool descriptions
│   │   └── tools/              ← 5 observability primitives
│   ├── model/                  ← 7-factor trading model (math, not AI)
│   │   ├── factors.py          ← Factor calculations
│   │   └── scorer.py           ← Weighted scoring + decision logic
│   ├── pipeline/               ← Data ingestion and validation
│   │   ├── data_fetcher.py     ← Yahoo Finance integration
│   │   ├── validator.py        ← Pydantic schema validation
│   │   └── cache.py            ← JSON file caching
│   └── phoenix/                ← Observability infrastructure
│       ├── tracing.py          ← OpenInference → Phoenix Cloud
│       └── client.py           ← Trace querying (REST/MCP)
├── scripts/
│   ├── seed.py                 ← Generate 70-100 historical traces
│   ├── test_agent.py           ← Agent verification
│   └── verify_setup.py         ← Package verification
├── data/                       ← Pre-fetched market data (JSON)
├── tests/                      ← pytest test suite
├── requirements.txt
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## What We Honestly Acknowledge

- There is no single comprehensive AI governance law in the US yet
- SEC priorities are examination focus areas, not codified requirements
- Industry standards for AI explainability are still evolving
- Governance tooling provides transparency, not accuracy
- Monitoring a system is not the same as understanding it
- A well-governed AI can still make bad decisions
- Effective AI governance requires organizational change, not just tools
- This is a proof of concept demonstrating governance infrastructure
- The trading model is simplified for demonstration purposes
- Reliability thresholds are heuristic, not statistically validated

---

## Verified Sources

| Source | Type |
|--------|------|
| [SEC 2026 Examination Priorities](https://www.sec.gov/about/reports-publications/2026-examination-priorities) | Government |
| [Texas TRAIGA](https://www.hklaw.com/en/insights/publications/2025/02/the-texas-responsible-ai-governance-act) | Enacted law |
| [Gartner AI Governance Market](https://www.gartner.com/en/newsroom/press-releases/2026-02-17) | Analyst |
| [Federal Reserve AI Adoption](https://www.federalreserve.gov/econres/notes/feds-notes/monitoring-ai-adoption-in-the-u-s-economy-20260403.html) | Government |
| Knight Capital $440M loss | SEC filings |
| Goldman/Apple $89M CFPB fine | CFPB enforcement |

---

## Disclaimers

- **Not financial advice.** TradeShield is a governance and audit demonstration tool.
- **Not a production system.** This is a hackathon proof of concept.
- **Market data** sourced from Yahoo Finance via yfinance for educational and demonstration purposes.
- **Do not enter personal or sensitive information** into the application.

---

## License

MIT — see [LICENSE](LICENSE) file.
