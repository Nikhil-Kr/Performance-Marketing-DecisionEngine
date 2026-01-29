.PHONY: setup install run run-batch test lint format mock-data init-rag clean help test-slack

help:
	@echo "Project Expedition - Available Commands"
	@echo ""
	@echo "  setup        - Full setup (venv, dependencies, .env)"
	@echo "  mock-data    - Generate mock marketing data"
	@echo "  init-rag     - Initialize ChromaDB vector store"
	@echo "  run          - Run Streamlit dashboard"
	@echo "  run-batch    - Process all anomalies in batch mode"
	@echo "  test-slack   - Test Slack webhook connection"
	@echo "  test         - Run tests"
	@echo "  lint         - Lint code"
	@echo "  clean        - Remove generated files"

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -e ".[dev]"
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your GCP project ID"
	@echo "  2. Run: gcloud auth application-default login"
	@echo "  3. Run: make mock-data"
	@echo "  4. Run: make init-rag"
	@echo "  5. Run: make run"

install:
	. .venv/bin/activate && pip install -e ".[dev]"

# Generate mock data
mock-data:
	. .venv/bin/activate && python scripts/generate_mock_data.py

# Initialize RAG with embeddings
init-rag:
	. .venv/bin/activate && python scripts/init_vector_store.py

# Run Streamlit dashboard
run:
	. .venv/bin/activate && streamlit run app.py

# Run batch processing (all anomalies)
run-batch:
	. .venv/bin/activate && python -m src.batch --max 10

# Run batch with Slack notifications
run-batch-notify:
	. .venv/bin/activate && python -m src.batch --max 10 --notify

# Run batch and generate report
run-batch-report:
	. .venv/bin/activate && python -m src.batch --max 10 --report batch_report.md

# Test Slack connection
test-slack:
	. .venv/bin/activate && python -c "from src.notifications.slack import test_slack_connection; test_slack_connection()"

# Run single diagnosis (CLI)
run-cli:
	. .venv/bin/activate && python -m src.graph

# Run tests
test:
	. .venv/bin/activate && pytest tests/ -v

# Lint
lint:
	. .venv/bin/activate && ruff check src/ tests/

# Format
format:
	. .venv/bin/activate && ruff format src/ tests/

# Clean
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	rm -rf data/embeddings
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Full quickstart
quickstart: setup mock-data init-rag run
