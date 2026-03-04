<!-- # 🧭 Project Expedition

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

**Questions or Issues?** Open an issue on GitHub or reach out to the maintainers. -->
# 🧭 Project Expedition

**Automated Decision Engine for Performance Marketing**

An AI-powered system that automatically detects marketing anomalies, diagnoses root causes using historical knowledge, and proposes remediation actions.

![Architecture](docs/architecture.png)

## 🎯 What It Does

1. **Detects Anomalies** - Monitors all marketing channels using windowed z-scores, seasonality, and rate-of-change detection
2. **Correlates Across Channels** - Identifies when anomalies in different channels share a common cause
3. **Investigates Root Causes** - Uses specialized AI agents for paid media, influencer, and offline channels
4. **Retrieves Historical Context** - RAG-powered memory recalls similar past incidents and recovery timelines
5. **Generates Diagnosis** - Multi-persona explanations (Executive → Data Scientist)
6. **Validates with Critic Loop** - Triple-Lock Protocol with self-correcting retry (up to 2 retries)
7. **Proposes Actions** - LLM-powered action mapping from a template library
8. **Tracks Decisions** - Persistent feedback, audit trail, and RAG feedback loop

## 🚀 Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/YOUR_USERNAME/expedition.git
cd expedition

# 2. Run setup
make setup

# 3. Generate mock data
make mock-data

# 4. Initialize RAG knowledge base
make init-rag

# 5. Run the dashboard
make run
```

Open http://localhost:8501 in your browser.

## 📁 Project Structure

```
expedition/
├── src/
│   ├── data_layer/           # Data abstraction (mock ↔ production)
│   │   ├── interfaces/       # Abstract base classes
│   │   ├── mock/             # CSV-based mock data
│   │   └── connectors/       # BigQuery, CreatorIQ (stubs)
│   │
│   ├── intelligence/         # LLM layer (Gemini)
│   │   ├── models.py         # Tiered model access + MockLLM fallback
│   │   └── prompts/          # All LLM prompts
│   │
│   ├── nodes/                # LangGraph nodes
│   │   ├── preflight.py      # Data freshness + cross-channel correlation
│   │   ├── router.py         # Routes to specialist investigators
│   │   ├── investigators/    # Paid media, Influencer, Offline
│   │   ├── memory/           # RAG retrieval + feedback storage
│   │   ├── explainer/        # Diagnosis synthesis (retry-aware)
│   │   ├── critic/           # Triple-Lock validation
│   │   └── proposer/         # LLM-powered action mapping
│   │
│   ├── action_layer/         # API execution (mock ↔ production)
│   │   ├── interfaces/       # Abstract executor
│   │   ├── mock/             # Logs without executing
│   │   └── connectors/       # Google/Meta/TikTok APIs (stubs)
│   │
│   ├── feedback/             # Persistent feedback + audit logging
│   ├── notifications/        # Slack webhook alerts
│   ├── schemas/              # Pydantic models + LangGraph state
│   └── graph.py              # LangGraph workflow definition
│
├── data/
│   ├── mock_csv/             # Generated mock data (15+ channels)
│   ├── post_mortems/         # Historical incidents for RAG
│   ├── embeddings/           # ChromaDB persistence
│   ├── feedback/             # Feedback logs (generated at runtime)
│   └── audit/                # Action decision logs (generated at runtime)
│
├── scripts/
│   ├── generate_mock_data.py # Creates mock CSVs with injected anomalies
│   └── init_vector_store.py  # Initializes ChromaDB with post-mortems
│
├── tests/
│   └── test_expedition.py
│
├── app.py                    # Streamlit dashboard
└── Makefile                  # All commands
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# For mock mode (default) - no GCP needed
DATA_LAYER_MODE=mock
ACTION_LAYER_MODE=mock

# For real Gemini LLM
GOOGLE_CLOUD_PROJECT=your-project-id
# Then run: gcloud auth application-default login

# For production data + actions
DATA_LAYER_MODE=production
ACTION_LAYER_MODE=production
```

### Tiered Intelligence

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| Tier 1 | gemini-2.0-flash | Routing, data fetching, action mapping | Low |
| Tier 2 | gemini-2.5-pro | Investigation, diagnosis, validation | High |

When GCP credentials are unavailable, the system falls back to MockLLM automatically.

## 📊 Supported Channels

### Paid Media
- Google Search, PMax, Display, YouTube
- Meta (Facebook/Instagram)
- TikTok
- LinkedIn
- Programmatic
- Affiliate

### Influencer
- CreatorIQ integration
- Platform-specific metrics
- Causal/incremental analysis

### Offline
- TV, Radio
- Out-of-home (OOH)
- Events, Podcast
- Direct mail

## 🧠 Architecture

### LangGraph Flow

```
Pre-Flight → Detect → Router → Investigator → Memory → Explainer ⇄ Critic → Proposer
                         ↓                                           ↑
                    ┌────┴────┐                              Retry Loop
                    │    │    │                               (up to 2x)
               Paid   Infl  Offline
               Media  uencer
```

See [EXPEDITION_FLOW.md](EXPEDITION_FLOW.md) for the detailed node-by-node walkthrough.

### Key Design Patterns

1. **Data Abstraction** - Interfaces with mock/production implementations
2. **Tiered Intelligence** - Right-size models for each task
3. **RAG Memory** - ChromaDB for semantic search of past incidents
4. **Self-Correcting Critic** - Triple-Lock Protocol with retry loop
5. **Human-in-the-Loop** - Actions require approval before execution
6. **Cross-Channel Correlation** - Preflight links related anomalies
7. **LLM Action Mapping** - Proposer uses LLM to select from template library

## 🛡️ Triple-Lock Protocol

The Critic node applies three validation checks:

1. **Data Grounding** - Every claim must reference specific data
2. **Evidence Verification** - Conclusions must follow from evidence
3. **Hallucination Check** - Flag claims beyond provided data

If validation fails:
- Risk > 80% → Escalate to human (too risky to retry)
- Risk ≤ 80% + retries left → Loop back to Explainer with feedback
- Retries exhausted → Proceed with warning flag

## 📈 Dashboard Features

- **Anomaly Dashboard** - Real-time status cards for all channels
- **Cross-Channel Correlations** - Related anomalies highlighted
- **Investigation View** - Deep dive with trend charts
- **Multi-Persona Diagnosis** - Toggle Executive/Marketer/Data Scientist views
- **Critic Retry Indicator** - Shows when diagnosis was refined
- **Action Approval** - ✅ Approve / ❌ Reject with audit logging
- **Impact Simulator** - Recovery projections from historical data
- **AI Assistant** - Chat with 10-turn memory for follow-up questions
- **Feedback Buttons** - 👍/👎 persistent feedback on every diagnosis

## 🔑 What's Real vs Mock

| Component | Current State | Production Swap |
|-----------|---------------|-----------------|
| LLM (all nodes) | ✅ Real Gemini (with MockLLM fallback) | Already production-ready |
| RAG Embeddings | ✅ Real Vertex AI (with hash fallback) | Already production-ready |
| Marketing Data | Mock (CSV files) | Implement BigQuery connector |
| Influencer Data | Mock (CSV files) | Implement CreatorIQ connector |
| Action Execution | Mock (logs only) | Implement platform API connectors |
| Slack Notifications | Ready to enable | Add webhook URL |
| Feedback/Audit Logs | ✅ Real (CSV files) | Works as-is |

## 🔄 Switching Mock → Production

The entire system is designed for easy swapping:

```bash
# In .env, change these two lines:
DATA_LAYER_MODE=production
ACTION_LAYER_MODE=production

# Then implement:
# 1. src/data_layer/connectors/bigquery.py (your BigQuery tables)
# 2. src/action_layer/connectors/*.py (your API credentials)
```

All nodes, prompts, graph, and the dashboard work unchanged.

See [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) for the detailed transition walkthrough.

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ -v --cov=src

# Run specific test class
pytest tests/test_expedition.py::TestGraph -v
```

## ⚙️ Commands

```bash
make setup              # Create venv, install deps, copy .env
make mock-data          # Generate mock CSV data
make init-rag           # Initialize ChromaDB with historical incidents
make run                # Start Streamlit dashboard
make run-batch          # Process all anomalies (up to 10)
make run-batch-notify   # Batch + Slack notifications
make run-batch-report   # Batch + markdown report
make test               # Run all tests
make lint               # Lint with ruff
make clean              # Remove generated files
```

## 🚢 Deployment

### Streamlit Cloud (Recommended for Demo)
1. Push to GitHub
2. Connect repo at [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in dashboard (copy from `.env`)

### Google Cloud Run
```bash
gcloud run deploy expedition --source . --region us-central1
```

### Railway
1. Connect GitHub repo
2. Add environment variables
3. Set start command: `streamlit run app.py --server.port $PORT`

## 📝 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

Built for GoFundMe's Growth Science team.

---

**Questions?** Open an issue or reach out to the Decision Science team.