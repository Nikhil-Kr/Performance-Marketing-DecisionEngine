# ===========================================
# Project Expedition - Makefile
# ===========================================
# Automated Decision Engine for Performance Marketing
# ===========================================

.PHONY: setup install run run-batch test lint format mock-data init-rag clean help \
        test-slack quickstart check-env validate-config

# Default target
.DEFAULT_GOAL := help

# ===========================================
# HELP
# ===========================================
help:
	@echo ""
	@echo "🧭 Project Expedition - Available Commands"
	@echo "==========================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Full setup (venv, dependencies, .env)"
	@echo "  make install        - Install dependencies only"
	@echo "  make quickstart     - One command: setup + mock-data + init-rag + run"
	@echo ""
	@echo "Data Generation:"
	@echo "  make mock-data      - Generate mock marketing data (all 15 channels)"
	@echo "  make init-rag       - Initialize ChromaDB vector store with post-mortems"
	@echo "  make refresh-data   - Regenerate mock data + reinitialize RAG"
	@echo ""
	@echo "Running the Application:"
	@echo "  make run            - Run Streamlit dashboard"
	@echo "  make run-cli        - Run single diagnosis via CLI"
	@echo "  make run-batch      - Process anomalies in batch mode"
	@echo "  make run-batch-notify  - Batch mode with Slack notifications"
	@echo "  make run-batch-report  - Batch mode with markdown report"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           - Run all tests"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Lint code with ruff"
	@echo "  make format         - Format code with ruff"
	@echo "  make check-env      - Validate environment configuration"
	@echo ""
	@echo "Integrations:"
	@echo "  make test-slack     - Test Slack webhook connection"
	@echo "  make test-gemini    - Test Gemini API connection"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Remove generated files and caches"
	@echo "  make clean-data     - Remove only generated data"
	@echo "  make clean-all      - Remove everything including venv"
	@echo ""

# ===========================================
# SETUP & INSTALLATION
# ===========================================
setup:
	@echo "🔧 Setting up Project Expedition..."
	@echo ""
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -e ".[dev]"
	@if [ ! -f .env ]; then cp .env.example .env; echo "📄 Created .env from template"; fi
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your GCP project ID"
	@echo "  2. Run: gcloud auth application-default login"
	@echo "  3. Run: make mock-data"
	@echo "  4. Run: make init-rag"
	@echo "  5. Run: make run"
	@echo ""
	@echo "Or just run: make quickstart"

# Use when the venv already exists and you only need to sync dependencies (faster than setup)
install:
	. .venv/bin/activate && pip install -e ".[dev]"

# One command to go from zero to running dashboard: setup → generate data → embed RAG → launch
quickstart: setup mock-data init-rag run

# ===========================================
# DATA GENERATION
# ===========================================
mock-data:
	@echo "📊 Generating mock marketing data..."
	. .venv/bin/activate && python scripts/generate_mock_data.py
	@echo ""
	@echo "✅ Mock data generated in data/mock_csv/"

init-rag:
	@echo "🧠 Initializing RAG vector store..."
	. .venv/bin/activate && python scripts/init_vector_store.py
	@echo ""
	@echo "✅ RAG initialized in data/embeddings/"

refresh-data: mock-data init-rag
	@echo "✅ Data refreshed!"

# ===========================================
# RUNNING THE APPLICATION
# ===========================================
run:
	@echo "🚀 Starting Streamlit dashboard..."
	. .venv/bin/activate && streamlit run app.py

# Runs src/graph.py directly — triggers the full LangGraph pipeline once (no UI) and prints output to terminal.
# Useful for debugging a specific node or testing without launching Streamlit.
run-cli:
	@echo "🔍 Running single diagnosis via CLI (no UI)..."
	. .venv/bin/activate && python -m src.graph

run-batch:
	@echo "📦 Running batch processing..."
	. .venv/bin/activate && python -m src.batch --max 10

run-batch-notify:
	@echo "📦 Running batch processing with Slack notifications..."
	. .venv/bin/activate && python -m src.batch --max 10 --notify

run-batch-report:
	@echo "📦 Running batch processing with report..."
	. .venv/bin/activate && python -m src.batch --max 10 --report batch_report.md
	@echo "📄 Report saved to batch_report.md"

# ===========================================
# TESTING & QUALITY
# ===========================================
test:
	@echo "🧪 Running tests..."
	. .venv/bin/activate && pytest tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	. .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=html
	@echo "📊 Coverage report: htmlcov/index.html"

lint:
	@echo "🔍 Linting code..."
	. .venv/bin/activate && ruff check src/ tests/ scripts/

format:
	@echo "✨ Formatting code..."
	. .venv/bin/activate && ruff format src/ tests/ scripts/

check-env:
	@echo "🔧 Checking environment configuration..."
	@. .venv/bin/activate && python -c "\
from src.utils.config import settings; \
print('DATA_LAYER_MODE:', settings.data_layer_mode); \
print('ACTION_LAYER_MODE:', settings.action_layer_mode); \
print('GCP Project:', settings.google_cloud_project or '⚠️ NOT SET'); \
print('Tier 1 Model:', settings.gemini_tier1_model); \
print('Tier 2 Model:', settings.gemini_tier2_model); \
print('Slack:', '✅ Configured' if settings.has_slack_configured else '⚠️ Not configured'); \
print('Google Ads:', '✅ Configured' if settings.has_google_ads_credentials else '⚠️ Not configured'); \
print('Meta Ads:', '✅ Configured' if settings.has_meta_credentials else '⚠️ Not configured'); \
"

# ===========================================
# EVALS (tests/evals/)
# ===========================================
# eval          — structural checks only (~30s, no GCP needed): schema validation, required fields, guardrail logic
# eval-full     — adds LLM-as-judge scoring (~5 min, requires GCP): diagnosis quality, action coherence
# eval-snapshot — saves a golden snapshot after a full eval run; used as the regression baseline
# eval-compare  — runs full eval and diffs results against the saved snapshot to catch regressions

.PHONY: eval eval-full eval-snapshot eval-compare

eval:
	@echo "🧪 Running quick eval (structural checks, no GCP needed)..."
	. .venv/bin/activate && python -m tests.evals.run_evals

eval-full:
	@echo "🧪 Running full eval with LLM-as-judge (requires GCP)..."
	. .venv/bin/activate && python -m tests.evals.run_evals --full

eval-snapshot:
	@echo "📸 Running full eval + saving golden snapshot for regression detection..."
	. .venv/bin/activate && python -m tests.evals.run_evals --full --save-snapshot

eval-compare:
	@echo "🔍 Running full eval + comparing against saved golden snapshot..."
	. .venv/bin/activate && python -m tests.evals.run_evals --full --compare-snapshot

# ===========================================
# INTEGRATION TESTS
# ===========================================
test-slack:
	@echo "📨 Testing Slack connection..."
	. .venv/bin/activate && python -c "\
from src.notifications.slack import test_slack_connection; \
test_slack_connection()"

test-gemini:
	@echo "🤖 Testing Gemini API connection..."
	. .venv/bin/activate && python -c "\
from src.intelligence.models import get_tier1_model, get_tier2_model; \
print('Testing Tier 1 model...'); \
t1 = get_tier1_model(); \
r1 = t1.invoke('Say hello in 5 words'); \
print('  ✅ Tier 1 OK:', r1.content[:50]); \
print('Testing Tier 2 model...'); \
t2 = get_tier2_model(); \
r2 = t2.invoke('Say hello in 5 words'); \
print('  ✅ Tier 2 OK:', r2.content[:50]); \
"

# ===========================================
# MAINTENANCE & CLEANUP
# ===========================================
clean:
	@echo "🧹 Cleaning generated files..."
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned!"

# WARNING: also removes data/post_mortems/incidents.csv which is the RAG source of truth.
# Any resolutions stored via store_resolution() will be lost.
# Run make init-rag after this to rebuild the vector store from scratch.
clean-data:
	@echo "🧹 Cleaning generated data (including post-mortems and embeddings)..."
	rm -rf data/mock_csv/*.csv
	rm -rf data/post_mortems/*.csv
	rm -rf data/embeddings/*
	@echo "✅ Data cleaned! Run: make mock-data && make init-rag to rebuild."

clean-all: clean clean-data
	@echo "🧹 Removing virtual environment..."
	rm -rf .venv
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	@echo "✅ Full cleanup complete!"

# ===========================================
# DEVELOPMENT HELPERS
# ===========================================
.PHONY: shell notebook

shell:
	@echo "🐍 Starting Python shell with project context..."
	. .venv/bin/activate && python -i -c "\
from src.data_layer import get_marketing_data, get_influencer_data, get_strategy_data, get_market_data; \
from src.graph import run_expedition; \
from datetime import datetime, timedelta; \
print('Available: get_marketing_data(), get_influencer_data(), get_strategy_data(), get_market_data()'); \
print('           run_expedition(anomaly)'); \
"

# Show project stats
stats:
	@echo "📊 Project Statistics"
	@echo "====================="
	@echo "Python files:"
	@find src -name "*.py" | wc -l
	@echo "Lines of code:"
	@find src -name "*.py" -exec cat {} \; | wc -l
	@echo "Mock CSV files:"
	@ls -1 data/mock_csv/*.csv 2>/dev/null | wc -l
	@echo "RAG documents:"
	@wc -l data/post_mortems/incidents.csv 2>/dev/null || echo "0"