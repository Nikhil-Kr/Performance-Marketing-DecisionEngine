# 🧭 Project Expedition

**Automated Decision Engine for Performance Marketing**

An AI-powered system that automatically detects marketing anomalies, diagnoses root causes using historical knowledge, and proposes remediation actions across all marketing channels.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Repository:** [github.com/Nikhil-Kr/Performance-Marketing-DecisionEngine](https://github.com/Nikhil-Kr/Performance-Marketing-DecisionEngine)

---

## 🎯 What It Does

1. **Detects Anomalies** — Monitors all marketing channels for unexpected metric changes (CPA spikes, ROAS drops, conversion collapses)
2. **Investigates Root Causes** — Routes to specialized AI investigators (Paid Media, Influencer, Offline)
3. **Retrieves Historical Context** — RAG-powered memory recalls similar past incidents and their resolutions
4. **Enriches with Market Data** — Pulls competitor intelligence, MMM saturation curves, MTA attribution
5. **Generates Multi-Persona Diagnosis** — Executive summary → Technical details (4 audience levels)
6. **Proposes Aligned Actions** — LLM selects actions that match its own diagnosis (no keyword mismatch)
7. **Validates Safety** — Triple-Lock Protocol prevents hallucinated recommendations
8. **Simulates Impact** — 7-day projection charts show baseline vs. action scenarios

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Time-Travel Analysis** | Analyze anomalies as of any historical date |
| **MMM Guardrails** | Blocks budget increases on saturated channels |
| **MTA Comparison** | Shows Last-Click vs Data-Driven attribution |
| **Competitor Intelligence** | Surfaces relevant competitor activity |
| **Market Trends** | Google Trends overlay on performance charts |
| **Impact Simulation** | Visual forecast of action outcomes |
| **Batch Processing** | Process multiple anomalies with Slack notifications |
| **Mock ↔ Production** | Switch data sources with one env variable |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Nikhil-Kr/Performance-Marketing-DecisionEngine.git
cd Performance-Marketing-DecisionEngine

# 2. Run setup (creates venv, installs dependencies)
make setup

# 3. Configure environment
cp .env.example .env
# Edit .env with your GCP project ID

# 4. Authenticate with GCP (for Gemini API)
gcloud auth application-default login

# 5. Generate mock data
make mock-data

# 6. Initialize RAG knowledge base
make init-rag

# 7. Run the dashboard
make run
```

Open **http://localhost:8501** in your browser.

---

## 📊 Supported Channels (15 Total)

### Digital — Paid Search & Shopping
- Google Search
- Google Performance Max
- Google Display
- Google YouTube

### Digital — Social
- Meta Ads (Facebook/Instagram)
- TikTok Ads
- LinkedIn Ads

### Digital — Programmatic & Affiliate
- Programmatic (DV360, The Trade Desk)
- Affiliate Networks

### Offline
- TV (Linear & CTV)
- Podcast
- Radio
- Direct Mail
- Out-of-Home (OOH)
- Events

### Creator Economy
- Influencer Campaigns (CreatorIQ integration)

---

## 🏗️ Architecture

### LangGraph Flow

```
┌──────────┐    ┌────────┐    ┌────────┐    ┌──────────────┐
│ Preflight│───▶│ Detect │───▶│ Router │───▶│ Investigator │
└──────────┘    └────────┘    └────────┘    └──────┬───────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                       ┌────────────┐      ┌────────────┐      ┌────────────┐
                       │ Paid Media │      │ Influencer │      │  Offline   │
                       └─────┬──────┘      └─────┬──────┘      └─────┬──────┘
                             │                   │                   │
                             └───────────────────┼───────────────────┘
                                                 ▼
┌──────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌──────────┐
│ Proposer │◀───│ Critic │◀───│Explainer│◀───│ Memory │◀───│(combines)│
└──────────┘    └────────┘    └────────┘    └────────┘    └──────────┘
```

### Node Descriptions

| Node | Purpose | Model Tier |
|------|---------|------------|
| **Preflight** | Validates data freshness | — |
| **Detect** | Finds anomalies via z-score | — |
| **Router** | Classifies channel type | Tier 1 (Flash) |
| **Investigator** | Deep-dives into root cause | Tier 2 (Pro) |
| **Memory** | RAG retrieval of past incidents | Embeddings |
| **Explainer** | Synthesizes diagnosis + selects actions | Tier 2 (Pro) |
| **Critic** | Triple-Lock validation | Tier 2 (Pro) |
| **Proposer** | Formats actions for execution | — |

---

## 📁 Project Structure

```
expedition/
├── app.py                    # Streamlit dashboard
├── Makefile                  # All commands
├── .env.example              # Configuration template
│
├── src/
│   ├── graph.py              # LangGraph orchestration
│   ├── batch.py              # Batch processing mode
│   │
│   ├── data_layer/           # Data abstraction
│   │   ├── interfaces/       # Abstract base classes
│   │   ├── mock/             # CSV-based mock data
│   │   │   ├── marketing.py  # Channel performance
│   │   │   ├── influencer.py # Creator campaigns
│   │   │   ├── strategy.py   # MMM & MTA data
│   │   │   └── market.py     # Competitor & trends
│   │   └── connectors/       # Production (BigQuery, CreatorIQ)
│   │
│   ├── intelligence/         # LLM layer
│   │   ├── models.py         # Tiered Gemini access
│   │   └── prompts/          # All LLM prompts
│   │       ├── router.py
│   │       ├── investigator.py
│   │       ├── explainer.py  # Includes action catalog
│   │       └── critic.py
│   │
│   ├── nodes/                # LangGraph nodes
│   │   ├── preflight.py
│   │   ├── router.py
│   │   ├── investigators/
│   │   │   ├── paid_media.py
│   │   │   ├── influencer.py
│   │   │   └── offline.py
│   │   ├── memory/
│   │   │   └── retriever.py  # ChromaDB RAG
│   │   ├── explainer/
│   │   │   └── synthesizer.py
│   │   ├── critic/
│   │   │   └── validator.py
│   │   └── proposer/
│   │       └── action_mapper.py
│   │
│   ├── action_layer/         # Execution layer
│   │   ├── interfaces/       # Abstract executor
│   │   ├── mock/             # Logs without executing
│   │   └── connectors/       # Platform APIs
│   │       ├── google_ads.py
│   │       ├── meta_ads.py
│   │       ├── tiktok_ads.py
│   │       ├── linkedin_ads.py
│   │       ├── programmatic.py
│   │       ├── affiliate.py
│   │       └── offline.py    # Slack-based notifications
│   │
│   ├── notifications/
│   │   └── slack.py          # Slack webhook integration
│   │
│   ├── schemas/
│   │   └── state.py          # Pydantic state models
│   │
│   └── utils/
│       └── config.py         # Settings management
│
├── data/
│   ├── mock_csv/             # Generated mock data (15 channels)
│   ├── post_mortems/         # Historical incidents for RAG
│   └── embeddings/           # ChromaDB persistence
│
├── scripts/
│   ├── generate_mock_data.py # Creates realistic mock data
│   └── init_vector_store.py  # Initializes RAG embeddings
│
└── tests/
    └── test_expedition.py
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# ===========================================
# LAYER MODES (mock or production)
# ===========================================
DATA_LAYER_MODE=mock
ACTION_LAYER_MODE=mock

# ===========================================
# GOOGLE CLOUD / VERTEX AI
# ===========================================
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1

# ===========================================
# GEMINI MODELS (Tiered Intelligence)
# ===========================================
GEMINI_TIER1_MODEL=gemini-2.0-flash
GEMINI_TIER2_MODEL=gemini-2.5-pro
EMBEDDING_MODEL=text-embedding-004

# ===========================================
# NOTIFICATIONS
# ===========================================
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL_ALERTS=#marketing-alerts
SLACK_CHANNEL_MEDIA_BUYING=#media-buying

# ===========================================
# PLATFORM CREDENTIALS (Production Only)
# ===========================================
# See .env.example for full list
```

### Tiered Intelligence

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| Tier 1 | gemini-2.0-flash | Routing, classification | Low |
| Tier 2 | gemini-2.5-pro | Investigation, diagnosis, validation | Higher |

Models are configurable via `.env` — upgrade to Gemini 3 when available.

---

## 🔄 Mock → Production

The entire system is designed for seamless environment switching:

```bash
# In .env, change these two lines:
DATA_LAYER_MODE=production
ACTION_LAYER_MODE=production

# Then implement your connectors:
# 1. src/data_layer/connectors/bigquery.py (your data warehouse)
# 2. src/action_layer/connectors/*.py (add API credentials)
```

**All nodes, prompts, and the dashboard work unchanged.**

### What Changes Per Mode

| Component | Mock Mode | Production Mode |
|-----------|-----------|-----------------|
| Channel Data | CSV files | BigQuery tables |
| Influencer Data | CSV files | CreatorIQ API |
| Action Execution | Logged only | Real API calls |
| Offline Actions | Logged only | Slack alerts to media team |

---

## 🛡️ Triple-Lock Protocol

The Critic node applies three validation checks before any action is proposed:

1. **Data Grounding** — Every claim must reference specific metrics
2. **Evidence Verification** — Conclusions must logically follow from evidence
3. **Hallucination Check** — Flags claims that go beyond provided data

Actions are blocked if hallucination risk > 50%.

---

## 📈 Dashboard Features

### Investigation View
- **Anomaly Summary** — Metric, severity, deviation %
- **Channel Performance** — Historical trend with anomaly highlighted
- **Market Overlay** — Google Trends comparison
- **Competitor Activity** — Recent competitive moves

### Strategy Context
- **MMM Guardrails** — Saturation status and recommendation
- **MTA Comparison** — Attribution model differences

### Diagnosis
- **Multi-Persona Views** — Executive, Director, Marketer, Data Scientist
- **Historical Context** — Similar past incidents from RAG
- **Confidence Score** — Model's certainty in diagnosis

### Actions
- **Proposed Actions** — With risk level and estimated impact
- **Impact Simulation** — 7-day projection chart
- **Approval Flow** — Review before execution

---

## 🧪 Testing & Development

```bash
# Run all tests
make test

# Run with verbose output
pytest tests/ -v

# Lint code
make lint

# Format code
make format

# Test Slack connection
make test-slack
```

---

## 📋 Available Make Commands

```bash
make help           # Show all commands
make setup          # Full setup (venv, deps, .env)
make mock-data      # Generate mock marketing data
make init-rag       # Initialize ChromaDB vector store
make run            # Run Streamlit dashboard
make run-batch      # Process anomalies in batch mode
make run-batch-notify  # Batch mode with Slack notifications
make test-slack     # Test Slack webhook
make test           # Run tests
make lint           # Lint code
make clean          # Remove generated files
make quickstart     # Full setup + run (one command)
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run `make lint` and `make test`
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built for marketing decision science teams who need automated anomaly detection and diagnosis at scale.

---

**Questions or Issues?** Open an issue on GitHub or reach out to the maintainers.