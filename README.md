# 🧭 Project Expedition

**Automated Decision Engine for Performance Marketing**

An AI-powered system that automatically detects marketing anomalies, diagnoses root causes using historical knowledge, and proposes remediation actions.

![Architecture](docs/architecture.png)

## 🎯 What It Does

1. **Detects Anomalies** - Monitors all marketing channels for unexpected metric changes
2. **Investigates Root Causes** - Uses specialized AI agents to analyze what went wrong
3. **Retrieves Historical Context** - RAG-powered memory recalls similar past incidents
4. **Generates Diagnosis** - Multi-persona explanations (Executive → Data Scientist)
5. **Proposes Actions** - Creates executable JSON payloads for platform APIs
6. **Validates Safety** - Triple-Lock Protocol prevents hallucinated recommendations

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
│   │   └── connectors/       # BigQuery, CreatorIQ (production)
│   │
│   ├── intelligence/         # LLM layer (Gemini)
│   │   ├── models.py         # Tiered model access
│   │   └── prompts/          # All LLM prompts
│   │
│   ├── nodes/                # LangGraph nodes
│   │   ├── preflight.py      # Data freshness check
│   │   ├── router.py         # Routes to specialists
│   │   ├── investigators/    # Paid media, Influencer
│   │   ├── memory/           # RAG retrieval
│   │   ├── explainer/        # Diagnosis synthesis
│   │   ├── proposer/         # Action generation
│   │   └── critic/           # Triple-Lock validation
│   │
│   ├── action_layer/         # API execution (mock ↔ production)
│   │   ├── interfaces/       # Abstract executor
│   │   ├── mock/             # Logs without executing
│   │   └── connectors/       # Google/Meta/TikTok APIs
│   │
│   ├── schemas/              # Pydantic models
│   └── graph.py              # LangGraph definition
│
├── data/
│   ├── mock_csv/             # Generated mock data
│   ├── post_mortems/         # Historical incidents for RAG
│   └── embeddings/           # ChromaDB persistence
│
├── scripts/
│   ├── generate_mock_data.py
│   └── init_vector_store.py
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

# For production - requires GCP credentials
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./credentials/sa-key.json
DATA_LAYER_MODE=production
ACTION_LAYER_MODE=production
```

### Tiered Intelligence

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| Tier 1 | gemini-2.0-flash | Routing, data fetching | Low |
| Tier 2 | gemini-2.5-pro | Reasoning, diagnosis | High |

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

All nodes, prompts, and the dashboard work unchanged.

## 📊 Supported Channels

### Paid Media
- Google Search, PMax, Display, YouTube
- Meta (Facebook/Instagram)
- TikTok
- LinkedIn
- Programmatic

### Influencer
- CreatorIQ integration
- Platform-specific metrics
- Causal/incremental analysis

### Offline
- Direct mail
- TV, Radio
- Out-of-home
- Events

## 🧠 Architecture

### LangGraph Flow

```
Pre-Flight → Detect → Router → Investigator → Memory → Explainer → Critic → Proposer
                         ↓
                    ┌────┴────┐
                    │         │
               Paid Media  Influencer
```

### Key Design Patterns

1. **Data Abstraction** - Interfaces with mock/production implementations
2. **Tiered Intelligence** - Right-size models for each task
3. **RAG Memory** - ChromaDB for semantic search of past incidents
4. **Triple-Lock Protocol** - Critic validates before proposing actions
5. **Human-in-the-Loop** - Actions require approval before execution

## 🛡️ Triple-Lock Protocol

The Critic node applies three validation checks:

1. **Data Grounding** - Every claim must reference specific data
2. **Evidence Verification** - Conclusions must follow from evidence
3. **Hallucination Check** - Flag claims beyond provided data

Actions are blocked if hallucination risk > 50%.

## 📈 Dashboard Features

- **Anomaly Dashboard** - Real-time status of all channels
- **Investigation View** - Deep dive into specific anomalies
- **Multi-Persona Diagnosis** - Switch between Executive/Technical views
- **Action Approval** - Review and approve proposed changes
- **Historical Context** - View similar past incidents

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ -v --cov=src

# Test specific module
pytest tests/unit/test_data_layer.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make lint` and `make test`
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

Built for GoFundMe's Growth Science team.

---

**Questions?** Open an issue or reach out to the Decision Science team.
