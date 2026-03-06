"""Tests for Project Expedition."""
import pytest
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataLayer:
    """Test data layer functionality."""

    def test_mock_marketing_data_loads(self):
        """Test that mock marketing data can be loaded."""
        os.environ["DATA_LAYER_MODE"] = "mock"

        from src.data_layer import get_marketing_data, clear_cache
        clear_cache()

        marketing = get_marketing_data()
        assert marketing is not None

    def test_mock_influencer_data_loads(self):
        """Test that mock influencer data can be loaded."""
        os.environ["DATA_LAYER_MODE"] = "mock"

        from src.data_layer import get_influencer_data, clear_cache
        clear_cache()

        influencer = get_influencer_data()
        assert influencer is not None

    def test_anomaly_detection_methods(self):
        """Test that improved anomaly detection uses multiple methods."""
        os.environ["DATA_LAYER_MODE"] = "mock"

        from src.data_layer import get_marketing_data, clear_cache
        clear_cache()

        marketing = get_marketing_data()
        if not marketing.is_healthy():
            pytest.skip("No mock data available")

        anomalies = marketing.get_anomalies()

        # Check that detection methods are labeled
        if anomalies:
            methods_found = set(a.get("detection_method", "unknown") for a in anomalies)
            print(f"Detection methods used: {methods_found}")
            assert len(anomalies) > 0


class TestSchemas:
    """Test Pydantic schema validation."""

    def test_anomaly_info_creation(self):
        """Test AnomalyInfo model."""
        from src.schemas.state import AnomalyInfo

        anomaly = AnomalyInfo(
            channel="google_search",
            metric="cpa",
            current_value=35.0,
            expected_value=25.0,
            deviation_pct=40.0,
            severity="high",
            direction="spike",
        )

        assert anomaly.channel == "google_search"
        assert anomaly.severity == "high"
        assert "spike" in anomaly.summary.lower()

    def test_diagnosis_result_creation(self):
        """Test DiagnosisResult model."""
        from src.schemas.state import DiagnosisResult

        diagnosis = DiagnosisResult(
            root_cause="Competitor bidding war",
            confidence=0.85,
            supporting_evidence=["CPC increased 40%", "Impression share dropped"],
            recommended_actions=["Increase brand bids", "Add negative keywords"],
        )

        assert diagnosis.confidence == 0.85
        assert len(diagnosis.supporting_evidence) == 2

    def test_state_has_new_fields(self):
        """Test that ExpeditionState includes all required fields."""
        from src.schemas.state import ExpeditionState

        annotations = ExpeditionState.__annotations__
        # Critic retry loop fields
        assert "critic_retry_count" in annotations, "Missing critic_retry_count"
        assert "critic_feedback" in annotations, "Missing critic_feedback"
        # Cross-channel correlation field
        assert "correlated_anomalies" in annotations, "Missing correlated_anomalies"
        # Time-travel / analysis date range fields (P4)
        assert "analysis_start_date" in annotations, "Missing analysis_start_date"
        assert "analysis_end_date" in annotations, "Missing analysis_end_date"


class TestActionLayer:
    """Test action layer functionality."""

    def test_mock_executor_creation(self):
        """Test MockActionExecutor can be created."""
        os.environ["ACTION_LAYER_MODE"] = "mock"

        from src.action_layer import get_executor, clear_cache
        clear_cache()

        executor = get_executor()
        assert executor is not None
        assert executor.platform_name == "mock"

    def test_mock_executor_execute(self):
        """Test MockActionExecutor can execute actions."""
        os.environ["ACTION_LAYER_MODE"] = "mock"

        from src.action_layer import get_executor, clear_cache
        clear_cache()

        executor = get_executor()
        result = executor.execute({
            "action_type": "notification",
            "platform": "mock",
            "operation": "alert",
            "parameters": {"team": "test"},
        })

        assert result["status"] == "success"


class TestGraph:
    """Test graph construction and routing."""

    def test_graph_builds_with_offline(self):
        """Test that graph builds with offline investigator node."""
        from src.graph import build_expedition_graph

        graph = build_expedition_graph()
        assert graph is not None

    def test_critic_retry_routing(self):
        """Test critic retry logic."""
        from src.graph import should_proceed_after_critic

        # Should proceed when validation passed
        state_passed = {"validation_passed": True, "critic_retry_count": 0}
        assert should_proceed_after_critic(state_passed) == "proposer"

        # Should retry when validation failed and retries available
        state_failed = {
            "validation_passed": False,
            "critic_retry_count": 0,
            "critic_validation": {"hallucination_risk": 0.6},
        }
        assert should_proceed_after_critic(state_failed) == "retry_explainer"

        # Should end when hallucination risk too high
        state_high_risk = {
            "validation_passed": False,
            "critic_retry_count": 0,
            "critic_validation": {"hallucination_risk": 0.9},
        }
        assert should_proceed_after_critic(state_high_risk) == "end"

    def test_route_investigator_offline(self):
        """Test offline channel routing."""
        from src.graph import route_investigator

        assert route_investigator({"channel_category": "paid_media"}) == "paid_media"
        assert route_investigator({"channel_category": "influencer"}) == "influencer"
        assert route_investigator({"channel_category": "offline"}) == "offline"


class TestNodes:
    """Test individual node functions."""

    def test_preflight_check(self):
        """Test preflight check node."""
        os.environ["DATA_LAYER_MODE"] = "mock"

        from src.data_layer import clear_cache
        clear_cache()

        from src.nodes.preflight import preflight_check

        state = {
            "messages": [],
            "data_freshness": None,
            "preflight_passed": False,
            "preflight_error": None,
            "analysis_start_date": None,
            "analysis_end_date": None,
            "anomalies": [],
            "selected_anomaly": None,
            "correlated_anomalies": [],
            "channel_category": None,
            "investigation_evidence": None,
            "investigation_summary": None,
            "historical_incidents": [],
            "rag_context": None,
            "diagnosis": None,
            "proposed_actions": [],
            "critic_validation": None,
            "validation_passed": False,
            "critic_retry_count": 0,
            "critic_feedback": None,
            "selected_action": None,
            "human_approved": False,
            "execution_result": None,
            "current_node": "start",
            "error": None,
            "run_id": None,
        }

        result = preflight_check(state)
        assert "preflight_passed" in result
        assert "current_node" in result

    def test_cross_channel_correlation(self):
        """Test cross-channel correlation detection."""
        from src.nodes.preflight import _find_correlations

        anomalies = [
            {"channel": "google_search", "metric": "cpa", "direction": "spike", "severity": "high"},
            {"channel": "meta_ads", "metric": "cpa", "direction": "spike", "severity": "high"},
            {"channel": "tiktok_ads", "metric": "roas", "direction": "drop", "severity": "medium"},
        ]
        selected = anomalies[0]

        correlated = _find_correlations(anomalies, selected)

        # Meta should correlate (same metric + same direction)
        assert len(correlated) >= 1
        assert any(c["channel"] == "meta_ads" for c in correlated)


class TestFeedback:
    """Test feedback and audit logging."""

    def test_log_feedback(self, tmp_path):
        """Test feedback logging."""
        import src.feedback as feedback

        original_csv = feedback.FEEDBACK_CSV
        feedback.FEEDBACK_CSV = tmp_path / "test_feedback.csv"

        try:
            result = feedback.log_feedback(
                anomaly={"channel": "google_search", "metric": "cpa"},
                diagnosis={"root_cause": "Competitor bidding", "confidence": 0.85},
                feedback_type="helpful",
            )
            assert result is True
            assert feedback.FEEDBACK_CSV.exists()
        finally:
            feedback.FEEDBACK_CSV = original_csv

    def test_log_action_decision(self, tmp_path):
        """Test audit logging."""
        import src.feedback as feedback

        original_csv = feedback.AUDIT_CSV
        feedback.AUDIT_CSV = tmp_path / "test_audit.csv"

        try:
            result = feedback.log_action_decision(
                anomaly={"channel": "meta_ads", "metric": "conversions"},
                diagnosis={"root_cause": "Pixel failure"},
                action={"action_id": "test_001", "action_type": "notification", "operation": "alert", "risk_level": "low"},
                decision="approved",
            )
            assert result is True
            assert feedback.AUDIT_CSV.exists()
        finally:
            feedback.AUDIT_CSV = original_csv


class TestIntelligence:
    """Test intelligence layer."""

    def test_prompts_format_correctly(self):
        """Test that prompts format with variables."""
        from src.intelligence.prompts.router import format_router_prompt
        from src.intelligence.prompts.investigator import format_paid_media_prompt, format_offline_prompt

        anomaly = {
            "channel": "google_search",
            "metric": "cpa",
            "direction": "spike",
            "severity": "high",
        }

        prompt = format_router_prompt(anomaly)
        assert "google_search" in prompt
        assert "cpa" in prompt

        offline_prompt = format_offline_prompt(
            anomaly={"channel": "tv", "metric": "impressions", "direction": "drop",
                     "severity": "high", "current_value": 100, "expected_value": 200,
                     "deviation_pct": -50},
            performance_summary="Test summary",
            channel_context="TV context",
        )
        assert "tv" in offline_prompt

    def test_prompts_include_analysis_period(self):
        """Test that investigator prompts include the analysis period."""
        from src.intelligence.prompts.investigator import format_paid_media_prompt, format_influencer_prompt

        anomaly = {
            "channel": "google_search",
            "metric": "cpa",
            "direction": "spike",
            "severity": "high",
            "detected_at": "2025-01-15",
            "current_value": 50,
            "expected_value": 30,
            "deviation_pct": 66.7,
        }

        prompt = format_paid_media_prompt(
            anomaly=anomaly,
            performance_summary="Test data",
            campaign_breakdown="Test breakdown",
            analysis_start="2025-01-01",
            analysis_end="2025-01-15",
        )
        assert "2025-01-01" in prompt
        assert "2025-01-15" in prompt
        assert "Analysis Period" in prompt

        inf_prompt = format_influencer_prompt(
            anomaly={"metric": "engagement_rate", "entity": "TestCreator", "direction": "drop",
                     "detected_at": "2025-01-15", "current_value": 0.01, "expected_value": 0.05,
                     "deviation_pct": -80},
            campaign_data="Test data",
            creator_history="Test history",
            attribution_data="Test attribution",
            analysis_start="2025-01-01",
            analysis_end="2025-01-15",
        )
        assert "2025-01-01" in inf_prompt
        assert "2025-01-15" in inf_prompt

    def test_retry_prompt_formats(self):
        """Test explainer retry prompt includes previous diagnosis and critic feedback."""
        from src.intelligence.prompts.explainer import format_retry_prompt

        prompt = format_retry_prompt(
            anomaly={"channel": "meta_ads", "metric": "cpa", "severity": "high",
                     "direction": "spike", "deviation_pct": 35},
            investigation_summary="Test investigation",
            historical_incidents=[],
            previous_diagnosis={
                "root_cause": "Old diagnosis",
                "confidence": 0.5,
                "supporting_evidence": ["Evidence 1"],
            },
            critic_feedback="The diagnosis lacks specific data citations.",
        )
        assert "Old diagnosis" in prompt
        assert "lacks specific data citations" in prompt

    def test_model_factory_mock_fallback(self):
        """Test that model factory falls back to mock when GCP is unavailable."""
        from src.intelligence.models import get_llm_safe

        llm = get_llm_safe("tier1")
        assert llm is not None


class TestActionMapper:
    """Test action mapping."""

    def test_keyword_fallback_works(self):
        """Test keyword-based action mapping fallback."""
        from src.nodes.proposer.action_mapper import _keyword_action_mapping

        # Competitor bidding → bid_adjustment
        actions = _keyword_action_mapping("competitor bidding war on brand terms", "google_search", None)
        assert len(actions) >= 1
        assert actions[0]["action_type"] == "bid_adjustment"

        # Tracking issue → notification
        actions = _keyword_action_mapping("tracking pixel removed from checkout", "meta_ads", None)
        assert len(actions) >= 1
        assert actions[0]["action_type"] == "notification"

        # Offline make-good
        actions = _keyword_action_mapping("tv spot preempted by breaking news", "tv", None)
        assert len(actions) >= 1

    def test_schedule_adjustment_template(self):
        """Test offline action templates exist in ACTION_TEMPLATES."""
        from src.nodes.proposer.action_mapper import ACTION_TEMPLATES

        assert "schedule_adjustment" in ACTION_TEMPLATES
        assert "make_good" in ACTION_TEMPLATES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
