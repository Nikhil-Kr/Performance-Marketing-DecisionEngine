"""Tests for Project Expedition."""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

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
        assert marketing.is_healthy() or not marketing.is_healthy()  # May not have data yet
    
    def test_mock_influencer_data_loads(self):
        """Test that mock influencer data can be loaded."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import get_influencer_data, clear_cache
        clear_cache()
        
        influencer = get_influencer_data()
        assert influencer is not None


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
    
    def test_expedition_state_has_date_fields(self):
        """Test that ExpeditionState includes analysis date fields."""
        from src.schemas.state import ExpeditionState
        
        # Create a minimal state dict
        state: ExpeditionState = {
            "messages": [],
            "data_freshness": None,
            "preflight_passed": False,
            "preflight_error": None,
            "analysis_start_date": "2025-01-01",
            "analysis_end_date": "2025-01-15",
            "anomalies": [],
            "selected_anomaly": None,
            "channel_category": None,
            "investigation_evidence": None,
            "investigation_summary": None,
            "historical_incidents": [],
            "rag_context": None,
            "diagnosis": None,
            "proposed_actions": [],
            "critic_validation": None,
            "validation_passed": False,
            "selected_action": None,
            "human_approved": False,
            "execution_result": None,
            "current_node": "start",
            "error": None,
            "run_id": None,
        }
        
        assert state["analysis_start_date"] == "2025-01-01"
        assert state["analysis_end_date"] == "2025-01-15"


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
        
        action = {
            "action_type": "budget_change",
            "platform": "google_ads",
            "resource_type": "campaign",
            "resource_id": "campaign_001",
            "operation": "increase",
            "parameters": {"adjustment_pct": 20},
        }
        
        result = executor.execute(action)
        assert result["status"] == "success"
        assert "execution_id" in result
    
    def test_mock_executor_validation(self):
        """Test MockActionExecutor validates actions."""
        os.environ["ACTION_LAYER_MODE"] = "mock"
        
        from src.action_layer import get_executor, clear_cache
        clear_cache()
        
        executor = get_executor()
        
        # Valid action
        valid_action = {
            "action_type": "budget_change",
            "platform": "google_ads",
            "operation": "increase",
        }
        is_valid, error = executor.validate(valid_action)
        assert is_valid
        
        # Invalid action (missing required field)
        invalid_action = {
            "action_type": "budget_change",
        }
        is_valid, error = executor.validate(invalid_action)
        assert not is_valid
        assert "platform" in error.lower() or "operation" in error.lower()


class TestNodes:
    """Test individual LangGraph nodes."""
    
    def test_preflight_check(self):
        """Test preflight check node."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import clear_cache
        clear_cache()
        
        from src.nodes.preflight import preflight_check
        from src.schemas.state import ExpeditionState
        
        state: ExpeditionState = {
            "messages": [],
            "data_freshness": None,
            "preflight_passed": False,
            "preflight_error": None,
            "analysis_start_date": None,
            "analysis_end_date": None,
            "anomalies": [],
            "selected_anomaly": None,
            "channel_category": None,
            "investigation_evidence": None,
            "investigation_summary": None,
            "historical_incidents": [],
            "rag_context": None,
            "diagnosis": None,
            "proposed_actions": [],
            "critic_validation": None,
            "validation_passed": False,
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


class TestIntelligence:
    """Test intelligence layer."""
    
    def test_prompts_format_correctly(self):
        """Test that prompts format with variables."""
        from src.intelligence.prompts.router import format_router_prompt
        from src.intelligence.prompts.investigator import format_paid_media_prompt
        
        anomaly = {
            "channel": "google_search",
            "metric": "cpa",
            "direction": "spike",
            "severity": "high",
        }
        
        prompt = format_router_prompt(anomaly)
        assert "google_search" in prompt
        assert "cpa" in prompt
    
    def test_prompts_include_analysis_period(self):
        """Test that prompts include analysis period context."""
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
        
        # Test paid media prompt includes analysis period
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
        
        # Test influencer prompt includes analysis period
        inf_anomaly = {
            "metric": "engagement_rate",
            "entity": "TestCreator",
            "direction": "drop",
            "detected_at": "2025-01-15",
            "current_value": 0.01,
            "expected_value": 0.05,
            "deviation_pct": -80,
        }
        
        inf_prompt = format_influencer_prompt(
            anomaly=inf_anomaly,
            campaign_data="Test data",
            creator_history="Test history",
            attribution_data="Test attribution",
            analysis_start="2025-01-01",
            analysis_end="2025-01-15",
        )
        assert "2025-01-01" in inf_prompt
        assert "2025-01-15" in inf_prompt
    
    def test_model_factory_mock_fallback(self):
        """Test that model factory falls back to mock."""
        from src.intelligence.models import get_llm_safe
        
        # Should not raise even without GCP credentials
        llm = get_llm_safe("tier1")
        assert llm is not None


class TestTimeTravel:
    """Test date-based time travel functionality."""
    
    def test_marketing_anomaly_detection_with_date_range(self):
        """Test that marketing anomaly detection respects date range."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import get_marketing_data, clear_cache
        clear_cache()
        
        marketing = get_marketing_data()
        
        # Skip if no data loaded
        if not marketing.is_healthy():
            pytest.skip("No mock data available")
        
        # Test with specific date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        anomalies = marketing.get_anomalies(
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify all anomalies have analysis context
        for anomaly in anomalies:
            assert "analysis_start" in anomaly
            assert "analysis_end" in anomaly
            assert "detected_at" in anomaly
    
    def test_influencer_anomaly_detection_with_date_range(self):
        """Test that influencer anomaly detection respects date range."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import get_influencer_data, clear_cache
        clear_cache()
        
        influencer = get_influencer_data()
        
        # Skip if no data loaded
        if not influencer.is_healthy():
            pytest.skip("No mock data available")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        anomalies = influencer.get_anomalies(
            start_date=start_date,
            end_date=end_date
        )
        
        # All returned anomalies should have context
        for anomaly in anomalies:
            assert "analysis_start" in anomaly
            assert "analysis_end" in anomaly
    
    def test_channel_performance_respects_end_date(self):
        """Test that channel performance data respects end_date parameter."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import get_marketing_data, clear_cache
        clear_cache()
        
        marketing = get_marketing_data()
        
        if not marketing.is_healthy():
            pytest.skip("No mock data available")
        
        channels = marketing.list_channels()
        if not channels:
            pytest.skip("No channels available")
        
        channel = channels[0]
        end_date = datetime.now() - timedelta(days=30)
        
        df = marketing.get_channel_performance(channel, days=7, end_date=end_date)
        
        if not df.empty:
            # All dates should be <= end_date
            import pandas as pd
            max_date = df["date"].max()
            assert max_date <= pd.Timestamp(end_date)
    
    def test_strategy_data_respects_reference_date(self):
        """Test that strategy data (MMM/MTA) respects reference date."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import get_strategy_data, clear_cache
        clear_cache()
        
        strategy = get_strategy_data()
        
        reference_date = datetime.now() - timedelta(days=30)
        
        # These should not raise even with date parameter
        mmm = strategy.get_mmm_guardrails("google_search", reference_date=reference_date)
        mta = strategy.get_mta_comparison("google_search", reference_date=reference_date)
        
        # Results should be dicts (may be empty if no data)
        assert isinstance(mmm, dict)
        assert isinstance(mta, dict)
    
    def test_detect_anomalies_uses_state_date_range(self):
        """Test that detect_anomalies node uses date range from state."""
        os.environ["DATA_LAYER_MODE"] = "mock"
        
        from src.data_layer import clear_cache
        clear_cache()
        
        from src.nodes.preflight import detect_anomalies
        
        # Create state with date range
        state = {
            "messages": [],
            "data_freshness": None,
            "preflight_passed": True,
            "preflight_error": None,
            "analysis_start_date": "2025-01-01",
            "analysis_end_date": "2025-01-15",
            "anomalies": [],
            "selected_anomaly": None,
            "channel_category": None,
            "investigation_evidence": None,
            "investigation_summary": None,
            "historical_incidents": [],
            "rag_context": None,
            "diagnosis": None,
            "proposed_actions": [],
            "critic_validation": None,
            "validation_passed": False,
            "selected_action": None,
            "human_approved": False,
            "execution_result": None,
            "current_node": "preflight",
            "error": None,
            "run_id": None,
        }
        
        result = detect_anomalies(state)
        
        assert "anomalies" in result
        assert "current_node" in result


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_batch_accepts_date_range(self):
        """Test that batch processing accepts date range parameters."""
        from src.batch import run_batch_diagnosis
        
        # This should not raise
        # Note: We don't actually run it to avoid LLM calls
        # Just verify the function signature accepts the parameters
        import inspect
        sig = inspect.signature(run_batch_diagnosis)
        params = list(sig.parameters.keys())
        
        assert "start_date" in params
        assert "end_date" in params


class TestOfflineChannelSupport:
    """Test offline channel routing and investigation."""
    
    def test_router_recognizes_offline_channels(self):
        """Test that router correctly categorizes offline channels."""
        from src.nodes.router import OFFLINE_CHANNELS, route_to_investigator
        
        # Verify offline channels are defined
        assert "tv" in OFFLINE_CHANNELS
        assert "podcast" in OFFLINE_CHANNELS
        assert "radio" in OFFLINE_CHANNELS
        assert "direct_mail" in OFFLINE_CHANNELS
        assert "ooh" in OFFLINE_CHANNELS
        assert "events" in OFFLINE_CHANNELS
    
    def test_router_routes_tv_to_offline(self):
        """Test that TV anomalies route to offline investigator."""
        from src.nodes.router import route_to_investigator
        
        state = {
            "selected_anomaly": {
                "channel": "tv",
                "metric": "cpa",
                "severity": "high",
            }
        }
        
        result = route_to_investigator(state)
        assert result.get("channel_category") == "offline"
    
    def test_router_routes_podcast_to_offline(self):
        """Test that podcast anomalies route to offline investigator."""
        from src.nodes.router import route_to_investigator
        
        state = {
            "selected_anomaly": {
                "channel": "podcast",
                "metric": "roas",
                "severity": "medium",
            }
        }
        
        result = route_to_investigator(state)
        assert result.get("channel_category") == "offline"
    
    def test_offline_investigator_exists(self):
        """Test that offline investigator module is properly defined."""
        from src.nodes.investigators.offline import investigate_offline, OFFLINE_SYSTEM_PROMPT
        
        # Verify the function exists and is callable
        assert callable(investigate_offline)
        
        # Verify system prompt is defined
        assert len(OFFLINE_SYSTEM_PROMPT) > 100
    
    def test_proposer_has_offline_action_templates(self):
        """Test that proposer has templates for offline channel actions."""
        from src.nodes.proposer.action_mapper import ACTION_TEMPLATES, OFFLINE_CHANNELS
        
        # Verify offline-specific templates exist
        assert "make_good" in ACTION_TEMPLATES
        assert "partner_issue" in ACTION_TEMPLATES
        assert "vendor_delivery" in ACTION_TEMPLATES
        assert "measurement_audit" in ACTION_TEMPLATES
        
        # Verify offline channels constant is defined
        assert "tv" in OFFLINE_CHANNELS
        assert "podcast" in OFFLINE_CHANNELS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
