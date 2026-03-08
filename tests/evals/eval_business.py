"""
Level 11: Business & UX Evals

Tests feedback logging, audit trail, state schema completeness,
multi-persona diagnosis, preflight structure, and store_resolution.

Usage:
    python -m tests.evals.eval_business
"""
import sys
import csv
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
os.environ.setdefault("DATA_LAYER_MODE", "mock")


# ============================================================================
# Test: Feedback Logging
# ============================================================================

def eval_feedback_logging() -> dict:
    """
    Test log_feedback() writes correct CSV row with expected fields.
    Uses a temp directory to avoid polluting real feedback data.
    """
    from src.feedback import log_feedback, FEEDBACK_FIELDS

    anomaly = {"channel": "google_pmax", "metric": "spend"}
    diagnosis = {"root_cause": "Competitor bidding war", "confidence": 0.78}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "feedback_log.csv"
        tmp_dir = Path(tmpdir)

        with patch("src.feedback.FEEDBACK_CSV", tmp_csv), \
             patch("src.feedback.FEEDBACK_DIR", tmp_dir):
            result = log_feedback(anomaly, diagnosis, "helpful")

        checks = {
            "returns_true": result is True,
            "csv_created": tmp_csv.exists(),
        }

        if tmp_csv.exists():
            with open(tmp_csv) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            checks["one_row"] = len(rows) == 1
            if rows:
                row = rows[0]
                checks["has_timestamp"] = bool(row.get("timestamp"))
                checks["channel_correct"] = row.get("anomaly_channel") == "google_pmax"
                checks["feedback_type"] = row.get("feedback_type") == "helpful"
                checks["feedback_value"] = row.get("feedback_value") == "1"
                checks["has_confidence"] = row.get("diagnosis_confidence") == "0.78"

    score = sum(checks.values()) / len(checks)
    return {
        "test": "feedback_logging",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Audit Trail Logging
# ============================================================================

def eval_audit_logging() -> dict:
    """
    Test log_action_decision() writes correct CSV row for approve/reject.
    """
    from src.feedback import log_action_decision, AUDIT_FIELDS

    anomaly = {"channel": "meta_ads", "metric": "conversions"}
    diagnosis = {"root_cause": "Tracking pixel broken"}
    action = {
        "action_id": "ACT-001",
        "action_type": "notification",
        "operation": "Alert engineering team",
        "risk_level": "low",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "action_log.csv"
        tmp_dir = Path(tmpdir)

        with patch("src.feedback.AUDIT_CSV", tmp_csv), \
             patch("src.feedback.AUDIT_DIR", tmp_dir):
            r1 = log_action_decision(anomaly, diagnosis, action, "approved")
            r2 = log_action_decision(anomaly, diagnosis, action, "rejected")

        checks = {
            "approve_returns_true": r1 is True,
            "reject_returns_true": r2 is True,
            "csv_created": tmp_csv.exists(),
        }

        if tmp_csv.exists():
            with open(tmp_csv) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            checks["two_rows"] = len(rows) == 2
            if len(rows) >= 2:
                checks["first_approved"] = rows[0]["decision"] == "approved"
                checks["second_rejected"] = rows[1]["decision"] == "rejected"
                checks["action_id_correct"] = rows[0]["action_id"] == "ACT-001"
                checks["channel_correct"] = rows[0]["anomaly_channel"] == "meta_ads"
                checks["has_timestamp"] = bool(rows[0].get("timestamp"))
                checks["has_risk_level"] = rows[0]["risk_level"] == "low"

    score = sum(checks.values()) / len(checks)
    return {
        "test": "audit_logging",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Audit Stats
# ============================================================================

def eval_audit_stats() -> dict:
    """
    Test get_audit_stats() returns correct counts after logging decisions.
    """
    from src.feedback import log_action_decision, get_audit_stats

    anomaly = {"channel": "google_search", "metric": "cpa"}
    diagnosis = {"root_cause": "Budget cap hit"}
    action = {"action_id": "ACT-002", "action_type": "budget_change",
              "operation": "Increase budget", "risk_level": "medium"}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "action_log.csv"
        tmp_dir = Path(tmpdir)

        with patch("src.feedback.AUDIT_CSV", tmp_csv), \
             patch("src.feedback.AUDIT_DIR", tmp_dir):
            log_action_decision(anomaly, diagnosis, action, "approved")
            log_action_decision(anomaly, diagnosis, action, "approved")
            log_action_decision(anomaly, diagnosis, action, "rejected")

            stats = get_audit_stats()

        checks = {
            "total_is_3": stats["total"] == 3,
            "approved_is_2": stats["approved"] == 2,
            "rejected_is_1": stats["rejected"] == 1,
        }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "audit_stats",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: State Schema Completeness
# ============================================================================

def eval_state_schema_completeness() -> dict:
    """
    Verify ExpeditionState TypedDict has all required fields for the pipeline.
    """
    from src.schemas.state import ExpeditionState
    import typing

    # Get all annotated fields from the TypedDict
    hints = typing.get_type_hints(ExpeditionState)

    required_fields = [
        # Conversation
        "messages",
        # Pre-flight
        "data_freshness", "preflight_passed", "preflight_error",
        # Detection
        "anomalies", "selected_anomaly", "correlated_anomalies",
        # Router
        "channel_category",
        # Investigation
        "investigation_evidence", "investigation_summary",
        # RAG
        "historical_incidents", "rag_context",
        # Explainer
        "diagnosis",
        # Proposer
        "proposed_actions",
        # Critic
        "critic_validation", "validation_passed",
        "critic_retry_count", "critic_feedback",
        # Action layer
        "selected_action", "human_approved", "execution_result",
        # Date range
        "analysis_start_date", "analysis_end_date",
        # Meta
        "current_node", "error", "run_id",
    ]

    checks = {}
    for field in required_fields:
        checks[field] = field in hints

    score = sum(checks.values()) / len(checks)
    return {
        "test": "state_schema_completeness",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
        "total_fields": len(hints),
        "required_fields": len(required_fields),
    }


# ============================================================================
# Test: State Initialization Defaults
# ============================================================================

def eval_state_initialization() -> dict:
    """
    Test that run_expedition() initializes all state fields with sensible defaults.
    Verifies no required field is missing from the initial state.
    """
    from src.graph import run_expedition

    # Read source to check initial state construction (don't actually run the graph)
    source = Path("src/graph.py").read_text()

    # Check that key default values are set in run_expedition
    required_defaults = {
        "messages": '"messages": []',
        "preflight_passed": '"preflight_passed": False',
        "anomalies": '"anomalies": []',
        "proposed_actions": '"proposed_actions": []',
        "validation_passed": '"validation_passed": False',
        "critic_retry_count": '"critic_retry_count": 0',
        "human_approved": '"human_approved": False',
        "current_node": '"current_node": "start"',
    }

    checks = {}
    for name, pattern in required_defaults.items():
        checks[f"default_{name}"] = pattern in source

    score = sum(checks.values()) / len(checks)
    return {
        "test": "state_initialization",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Diagnosis Multi-Persona Fields
# ============================================================================

def eval_diagnosis_multi_persona() -> dict:
    """
    Test DiagnosisResult schema includes all 4 persona explanation fields.
    """
    from src.schemas.state import DiagnosisResult

    persona_fields = [
        "executive_summary",
        "director_summary",
        "marketer_summary",
        "technical_details",
    ]

    model_fields = DiagnosisResult.model_fields

    checks = {}
    for field in persona_fields:
        checks[f"has_{field}"] = field in model_fields

    # Also check core fields
    core_fields = ["root_cause", "confidence", "supporting_evidence", "recommended_actions"]
    for field in core_fields:
        checks[f"core_{field}"] = field in model_fields

    # Test instantiation with all personas
    try:
        d = DiagnosisResult(
            root_cause="Test root cause",
            confidence=0.8,
            supporting_evidence=["Evidence 1"],
            recommended_actions=["Action 1"],
            executive_summary="Executive view",
            director_summary="Director view",
            marketer_summary="Marketer view",
            technical_details="Technical view",
        )
        checks["instantiation_ok"] = True
        checks["confidence_bounded"] = 0.0 <= d.confidence <= 1.0
    except Exception:
        checks["instantiation_ok"] = False

    score = sum(checks.values()) / len(checks)
    return {
        "test": "diagnosis_multi_persona",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: Preflight Structure
# ============================================================================

def eval_preflight_structure() -> dict:
    """
    Test preflight_check() returns expected keys and types.
    """
    from src.nodes.preflight import preflight_check

    state = {
        "messages": [],
        "preflight_passed": False,
        "preflight_error": None,
        "data_freshness": None,
        "current_node": "start",
    }

    result = preflight_check(state)

    checks = {
        "returns_dict": isinstance(result, dict),
        "has_preflight_passed": "preflight_passed" in result,
        "has_current_node": "current_node" in result,
        "has_data_freshness": "data_freshness" in result,
        "passed_is_bool": isinstance(result.get("preflight_passed"), bool),
        "current_node_is_preflight": result.get("current_node") == "preflight",
    }

    # In mock mode, preflight should pass
    if result.get("preflight_passed"):
        checks["freshness_is_dict"] = isinstance(result.get("data_freshness"), dict)
    else:
        checks["error_is_string"] = isinstance(result.get("preflight_error"), str)

    score = sum(checks.values()) / len(checks)
    return {
        "test": "preflight_structure",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Store Resolution Structure
# ============================================================================

def eval_store_resolution_structure() -> dict:
    """
    Test store_resolution() creates an incident with correct fields.
    Uses temp CSV to avoid polluting real data.
    """
    from src.nodes.memory.retriever import store_resolution

    anomaly = {"channel": "google_search", "metric": "cpa", "severity": "high"}
    diagnosis = {"root_cause": "Competitor bidding war", "confidence": 0.85}
    actions = [
        {"operation": "Increase brand bids by 20%"},
        {"operation": "Add negative keywords"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "incidents.csv"

        with patch("src.nodes.memory.retriever.INCIDENTS_CSV", tmp_csv), \
             patch("src.nodes.memory.retriever.CHROMA_DIR", Path(tmpdir) / "nonexistent"):
            result = store_resolution(anomaly, diagnosis, actions)

        checks = {
            "returns_true": result is True,
            "csv_created": tmp_csv.exists(),
        }

        if tmp_csv.exists():
            with open(tmp_csv) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            checks["one_row"] = len(rows) == 1
            if rows:
                row = rows[0]
                checks["has_incident_id"] = row.get("incident_id", "").startswith("INC-")
                checks["has_date"] = bool(row.get("date"))
                checks["channel_correct"] = row.get("channel") == "google_search"
                checks["has_anomaly_type"] = "cpa" in row.get("anomaly_type", "")
                checks["has_root_cause"] = "Competitor" in row.get("root_cause", "")
                checks["has_resolution"] = "Increase" in row.get("resolution", "")
                checks["severity_correct"] = row.get("severity") == "high"

    score = sum(checks.values()) / len(checks)
    return {
        "test": "store_resolution_structure",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Graph Node Connectivity
# ============================================================================

def eval_graph_node_connectivity() -> dict:
    """
    Verify the LangGraph has all expected nodes and edges.
    """
    source = Path("src/graph.py").read_text()

    expected_nodes = [
        "preflight", "detect", "abort", "no_anomalies",
        "router", "paid_media", "influencer", "offline",
        "memory", "explainer", "critic", "retry_explainer", "proposer",
    ]

    expected_edges = [
        ("paid_media", "memory"),
        ("influencer", "memory"),
        ("offline", "memory"),
        ("memory", "explainer"),
        ("explainer", "critic"),
        ("retry_explainer", "explainer"),
        ("proposer", "END"),
    ]

    checks = {}

    # Check nodes exist
    for node in expected_nodes:
        checks[f"node_{node}"] = f'add_node("{node}"' in source

    # Check edges exist
    for src_node, dst in expected_edges:
        if dst == "END":
            checks[f"edge_{src_node}_END"] = f'add_edge("{src_node}", END)' in source
        else:
            checks[f"edge_{src_node}_{dst}"] = f'add_edge("{src_node}", "{dst}")' in source

    score = sum(checks.values()) / len(checks)
    return {
        "test": "graph_node_connectivity",
        "score": score,
        "passed": score >= 0.90,
        "checks": checks,
    }


# ============================================================================
# Orchestrator
# ============================================================================

def run_all() -> dict:
    """Run all Business & UX evals and return composite score."""
    tests = [
        eval_feedback_logging,
        eval_audit_logging,
        eval_audit_stats,
        eval_state_schema_completeness,
        eval_state_initialization,
        eval_diagnosis_multi_persona,
        eval_preflight_structure,
        eval_store_resolution_structure,
        eval_graph_node_connectivity,
    ]

    results = []
    for test_fn in tests:
        try:
            result = test_fn()
        except Exception as e:
            result = {"test": test_fn.__name__, "score": 0.0, "passed": False, "error": str(e)}
        results.append(result)

    scores = [r["score"] for r in results]
    composite = sum(scores) / len(scores) if scores else 0.0

    print(f"\n  Level 11: Business & UX")
    for r in results:
        status = "\u2705" if r["passed"] else "\u274c"
        err = f" ({r['error']})" if "error" in r and r.get("score") == 0.0 else ""
        print(f"    {status} {r['test']}: {r['score']:.0%}{err}")
    print(f"    Composite: {composite:.0%}")

    return {
        "level": 11,
        "name": "Business & UX",
        "composite_score": composite,
        "passed": composite >= 0.75,
        "results": results,
    }


if __name__ == "__main__":
    run_all()
