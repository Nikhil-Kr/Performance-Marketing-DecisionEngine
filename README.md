# 🧭 Project Expedition

**Automated Decision Engine for Performance Marketing**

An AI-powered system that automatically detects marketing anomalies, diagnoses root causes using historical knowledge, and proposes remediation actions.

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
git clone https://github.com/Nikhil-Kr/Performance-Marketing-DecisionEngine.git
cd Performance-Marketing-DecisionEngine

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
│   │       ├── router.py
│   │       ├── investigator.py
│   │       ├── explainer.py
│   │       └── critic.py
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
| Tier 1 | gemini-2.0-flash | Routing, investigation, action mapping | Low |
| Tier 2 | gemini-2.5-pro | Diagnosis synthesis, validation, chat | High |

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

See [Expedition_Flow.md](Expedition_Flow.md) for the detailed node-by-node walkthrough.

### Node Descriptions

| Node | Purpose | Model Tier |
|------|---------|------------|
| **Preflight** | Validates data freshness | — |
| **Detect** | Finds anomalies via z-score | — |
| **Router** | Classifies channel type | Tier 1 (Flash) |
| **Investigator** | Deep-dives into root cause | Tier 1 (Flash) |
| **Memory** | RAG retrieval of past incidents | Embeddings |
| **Explainer** | Synthesizes diagnosis + selects actions | Tier 2 (Pro) |
| **Critic** | Triple-Lock validation | Tier 2 (Pro) |
| **Proposer** | Formats actions for execution | Tier 1 (Flash) |

### Key Design Patterns

1. **Data Abstraction** - Interfaces with mock/production implementations
2. **Tiered Intelligence** - Right-size models for each task
3. **RAG Memory** - ChromaDB for semantic search of past incidents; temporally filtered to prevent future-data contamination
4. **Self-Correcting Critic** - Triple-Lock Protocol with retry loop
5. **Human-in-the-Loop** - Actions require approval before execution
6. **Cross-Channel Correlation** - Preflight links related anomalies
7. **LLM Action Mapping** - Proposer uses LLM to select from template library
8. **MMM Guardrail** - Blocks budget increases when marginal ROAS < 1.0 (data from `strategy.get_mmm_guardrails()`)
9. **ROOT_CAUSE_ACTION_MAP** - Explainer infers root cause category; Proposer only offers actions valid for that category
10. **Time-Travel Analysis** - UI date picker flows into state; all investigators and RAG use the selected date as their data cutoff

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

MIT License

## 🙏 Acknowledgments

Built for GoFundMe's Growth Science team.

---

**Questions?** Open an issue or reach out to the Decision Science team.
