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
    → Trading Model (4-factor rule-based scorer, NOT AI)
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

**The trading model uses mathematical formulas (moving averages, weighted scoring), not AI.** It generates auditable decision streams for governance demonstration.

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Google Cloud account with Gemini API key
- Arize Phoenix Cloud account with API key

### Installation

```bash
git clone https://github.com/[YOUR-USERNAME]/tradeshield-ai-governance.git
cd tradeshield-ai-governance
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```
GOOGLE_GENAI_API_KEY=your-gemini-key
PHOENIX_API_KEY=your-phoenix-key
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-space/v1/traces
```

### Run Locally

```bash
# Seed historical data (first time only)
python scripts/seed.py

# Start the agent
python -m tradeshield.main
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

A simplified multi-factor scoring system using four signals:
- **Momentum** (30%): 10-day vs 50-day moving average
- **Volatility** (25%): VIX level assessment
- **Relative Strength** (25%): stock vs sector performance
- **Volume** (20%): current vs average trading volume

This is arithmetic, not AI. The model exists to generate realistic decision streams for governance demonstration. It is not a production trading strategy.

### The Governance Agent (what does the observing)

Powered by Gemini as the reasoning engine. When a compliance officer asks a question, the agent selects the appropriate observability primitive, queries Phoenix traces, and provides evidence-backed answers.

### The Self-Assessment Loop

The reliability assessment primitive queries the agent's own historical traces via Phoenix MCP. It finds past decisions made under similar conditions, calculates actual accuracy, and compares it to the model's stated confidence. If there's a significant gap, it warns the user.

This is evidence-based confidence calibration through trace querying — not machine learning or model retraining.

Note: Reliability thresholds (GREEN >70%, YELLOW 50-70%, RED <50%) are heuristic baselines for demonstration. Production deployment would calibrate against institutional risk tolerance.

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
