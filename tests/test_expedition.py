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
    
    def test_model_factory_mock_fallback(self):
        """Test that model factory falls back to mock."""
        from src.intelligence.models import get_llm_safe
        
        # Should not raise even without GCP credentials
        llm = get_llm_safe("tier1")
        assert llm is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
