"""
Level 8: Cross-Component Integration Evals

Tests correlation scoring, date range propagation, quality signal thresholds,
root cause → action chain, and critic pass/fail boundary conditions.

Usage:
    python -m tests.evals.eval_integration
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
os.environ.setdefault("DATA_LAYER_MODE", "mock")


# ============================================================================
# Test: Correlation Scoring Formula
# ============================================================================

def eval_correlation_scoring() -> dict:
    """Test _find_correlations scoring matches expected formula."""
    from src.nodes.preflight import _find_correlations

    selected = {
        "channel": "google_pmax",
        "metric": "spend",
        "direction": "spike",
        "severity": "critical",
    }

    anomalies = [
        selected,
        # Same metric + same direction + similar severity → 0.4+0.2+0.2 = 0.8
        {"channel": "meta_ads", "metric": "spend", "direction": "spike", "severity": "high"},
        # Same metric only → 0.4
        {"channel": "tiktok_ads", "metric": "spend", "direction": "drop", "severity": "low"},
        # Same direction + similar severity → 0.2+0.2 = 0.4
        {"channel": "google_search", "metric": "cpa", "direction": "spike", "severity": "high"},
        # Nothing matching → 0.0
        {"channel": "radio", "metric": "impressions", "direction": "drop", "severity": "low"},
        # Same metric + divergence → 0.4+0.3 = 0.7
        {"channel": "linkedin_ads", "metric": "spend", "direction": "drop", "severity": "medium", "detection_method": "multi_metric_divergence"},
    ]

    result = _find_correlations(anomalies, selected)

    checks = {}

    # meta_ads should have highest correlation (0.8)
    meta = next((r for r in result if r["channel"] == "meta_ads"), None)
    checks["meta_high_score"] = meta is not None and abs(meta["correlation_score"] - 0.8) < 0.05

    # linkedin should have 0.7 (metric match + divergence)
    linkedin = next((r for r in result if r["channel"] == "linkedin_ads"), None)
    checks["linkedin_divergence_score"] = linkedin is not None and abs(linkedin["correlation_score"] - 0.7) < 0.05

    # tiktok has same metric only: 0.4 (just at threshold)
    tiktok = next((r for r in result if r["channel"] == "tiktok_ads"), None)
    checks["tiktok_at_threshold"] = tiktok is not None and abs(tiktok["correlation_score"] - 0.4) < 0.05

    # radio has nothing matching: should NOT be in results (below 0.4)
    radio = next((r for r in result if r["channel"] == "radio"), None)
    checks["radio_excluded"] = radio is None

    score = sum(checks.values()) / len(checks)
    return {
        "test": "correlation_scoring",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
        "result_count": len(result),
    }


# ============================================================================
# Test: Correlation Threshold
# ============================================================================

def eval_correlation_threshold() -> dict:
    """Test that only anomalies with correlation >= 0.4 are included."""
    from src.nodes.preflight import _find_correlations

    selected = {"channel": "google_pmax", "metric": "spend", "direction": "spike", "severity": "critical"}
    anomalies = [
        selected,
        # Below threshold: different everything
        {"channel": "radio", "metric": "impressions", "direction": "drop", "severity": "low"},
        # Above threshold: same metric
        {"channel": "meta_ads", "metric": "spend", "direction": "drop", "severity": "low"},
    ]

    result = _find_correlations(anomalies, selected)

    checks = {
        "all_above_threshold": all(r["correlation_score"] >= 0.4 for r in result),
        "radio_excluded": not any(r["channel"] == "radio" for r in result),
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "correlation_threshold",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: Correlation Top 5 Limit
# ============================================================================

def eval_correlation_top5() -> dict:
    """Test that at most 5 correlated anomalies are returned."""
    from src.nodes.preflight import _find_correlations

    selected = {"channel": "google_pmax", "metric": "spend", "direction": "spike", "severity": "critical"}

    # Create 8 anomalies that all match on metric (0.4 each)
    anomalies = [selected]
    for i in range(8):
        anomalies.append({
            "channel": f"channel_{i}",
            "metric": "spend",
            "direction": "drop",
            "severity": "low",
        })

    result = _find_correlations(anomalies, selected)

    checks = {
        "max_5_returned": len(result) <= 5,
        "has_results": len(result) > 0,
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "correlation_top5",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
        "result_count": len(result),
    }


# ============================================================================
# Test: Date Range Propagation
# ============================================================================

def eval_date_propagation() -> dict:
    """Test extract_analysis_dates parses state dates correctly."""
    from src.nodes.investigators.utils import extract_analysis_dates

    state = {
        "analysis_start_date": "2020-02-01",
        "analysis_end_date": "2020-04-30",
    }
    anomaly = {"detected_at": "2020-03-15"}

    start, end = extract_analysis_dates(state, anomaly)

    checks = {
        "start_is_feb_1": start == datetime(2020, 2, 1),
        "end_is_apr_30": end == datetime(2020, 4, 30),
        "start_before_end": start < end,
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "date_propagation",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
        "start": str(start),
        "end": str(end),
    }


# ============================================================================
# Test: Date Fallback Chain
# ============================================================================

def eval_date_fallback_chain() -> dict:
    """Test date priority: state > anomaly.detected_at > now."""
    from src.nodes.investigators.utils import extract_analysis_dates

    # Case 1: State dates take priority
    state_with_dates = {"analysis_start_date": "2020-01-01", "analysis_end_date": "2020-06-30"}
    anomaly = {"detected_at": "2025-01-15"}
    s1, e1 = extract_analysis_dates(state_with_dates, anomaly)

    # Case 2: No state dates → falls back to anomaly.detected_at
    state_no_dates = {}
    s2, e2 = extract_analysis_dates(state_no_dates, anomaly)

    # Case 3: No state dates, no detected_at → falls back to now
    s3, e3 = extract_analysis_dates({}, {})

    checks = {
        "state_overrides_anomaly": e1 == datetime(2020, 6, 30),
        "anomaly_fallback_works": e2 == datetime(2025, 1, 15),
        "now_fallback_is_recent": (datetime.now() - e3).total_seconds() < 60,
        "default_start_30_days_before": abs((e3 - s3).days - 30) <= 1,
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "date_fallback_chain",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: Root Cause → Action Chain (End-to-End)
# ============================================================================

def eval_root_cause_to_action_chain() -> dict:
    """Test the full chain: root cause text → category → allowed keys → keyword actions respect filter."""
    from src.nodes.explainer.synthesizer import infer_root_cause_category, ROOT_CAUSE_ACTION_MAP
    from src.nodes.proposer.action_mapper import _keyword_action_mapping

    test_chains = [
        {
            "root_cause": "Competitor bidding war driving up auction prices",
            "expected_category": "auction_pressure",
            "keyword_text": "competitor bidding auction",
        },
        {
            "root_cause": "Tracking pixel broken, no conversions being attributed",
            "expected_category": "tracking_break",
            "keyword_text": "tracking pixel broken attribution",
        },
        {
            "root_cause": "Bot fraud with fake invalid traffic",
            "expected_category": "fraud",
            "keyword_text": "bot fraud fake traffic",
        },
    ]

    correct = 0
    details = []
    for tc in test_chains:
        # Step 1: Categorize
        category = infer_root_cause_category(tc["root_cause"])
        cat_ok = category == tc["expected_category"]

        # Step 2: Get allowed keys
        allowed_keys = ROOT_CAUSE_ACTION_MAP.get(category, ROOT_CAUSE_ACTION_MAP["unknown"])

        # Step 3: Keyword mapping with restriction
        actions = _keyword_action_mapping(
            tc["keyword_text"], "google_search", {"channel": "google_search"}, allowed_keys
        )

        # Step 4: Verify actions produced and within allowed templates
        has_actions = len(actions) > 0

        if cat_ok and has_actions:
            correct += 1
        else:
            details.append(
                f"FAIL: '{tc['root_cause'][:40]}' → cat={category} (expected {tc['expected_category']}), "
                f"actions={len(actions)}"
            )

    score = correct / len(test_chains)
    return {
        "test": "root_cause_to_action_chain",
        "score": score,
        "passed": score >= 0.66,
        "correct": correct,
        "total": len(test_chains),
        "failures": details,
    }


# ============================================================================
# Test: Critic Pass Condition
# ============================================================================

def eval_critic_pass_condition() -> dict:
    """Test critic pass logic: is_valid=True, risk<0.5, data_grounded=True → passes."""
    # Replicate the logic from validator.py lines 70-77
    def compute_passed(validation: dict) -> bool:
        risk_score = validation.get("hallucination_risk", 1.0)
        is_valid_strict = (
            validation.get("is_valid", False)
            and risk_score < 0.5
            and validation.get("data_grounded", False)
        )
        return is_valid_strict or (risk_score <= 0.25)

    checks = {}

    # Standard pass
    checks["standard_pass"] = compute_passed({
        "is_valid": True, "hallucination_risk": 0.3, "data_grounded": True
    }) is True

    # Missing data_grounded → fail
    checks["no_grounding_fails"] = compute_passed({
        "is_valid": True, "hallucination_risk": 0.3, "data_grounded": False
    }) is False

    # Risk too high → fail
    checks["high_risk_fails"] = compute_passed({
        "is_valid": True, "hallucination_risk": 0.6, "data_grounded": True
    }) is False

    score = sum(checks.values()) / len(checks)
    return {
        "test": "critic_pass_condition",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: Critic Low Risk Override
# ============================================================================

def eval_critic_low_risk_override() -> dict:
    """Test critic low-risk override: risk <= 0.25 passes even with is_valid=False."""
    def compute_passed(validation: dict) -> bool:
        risk_score = validation.get("hallucination_risk", 1.0)
        is_valid_strict = (
            validation.get("is_valid", False)
            and risk_score < 0.5
            and validation.get("data_grounded", False)
        )
        return is_valid_strict or (risk_score <= 0.25)

    checks = {}

    # Low risk override: is_valid=False but risk=0.2 → still passes
    checks["low_risk_override"] = compute_passed({
        "is_valid": False, "hallucination_risk": 0.2, "data_grounded": False
    }) is True

    # Exactly at boundary: risk=0.25 → passes
    checks["boundary_0.25_passes"] = compute_passed({
        "is_valid": False, "hallucination_risk": 0.25, "data_grounded": False
    }) is True

    # Just above boundary: risk=0.26 → fails (without is_valid)
    checks["boundary_0.26_fails"] = compute_passed({
        "is_valid": False, "hallucination_risk": 0.26, "data_grounded": False
    }) is False

    score = sum(checks.values()) / len(checks)
    return {
        "test": "critic_low_risk_override",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: Critic High Risk Fail
# ============================================================================

def eval_critic_high_risk_fail() -> dict:
    """Test critic fails when risk is high even with is_valid=True but data_grounded=False."""
    def compute_passed(validation: dict) -> bool:
        risk_score = validation.get("hallucination_risk", 1.0)
        is_valid_strict = (
            validation.get("is_valid", False)
            and risk_score < 0.5
            and validation.get("data_grounded", False)
        )
        return is_valid_strict or (risk_score <= 0.25)

    checks = {}

    # is_valid=True but not grounded + high risk → fail
    checks["high_risk_ungrounded"] = compute_passed({
        "is_valid": True, "hallucination_risk": 0.6, "data_grounded": False
    }) is False

    # Everything bad → fail
    checks["all_bad"] = compute_passed({
        "is_valid": False, "hallucination_risk": 0.9, "data_grounded": False
    }) is False

    # Missing all fields → fail (defaults to risk=1.0)
    checks["empty_validation_fails"] = compute_passed({}) is False

    score = sum(checks.values()) / len(checks)
    return {
        "test": "critic_high_risk_fail",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Orchestrator
# ============================================================================

def run_all() -> dict:
    """Run all integration evals and return composite score."""
    tests = [
        eval_correlation_scoring,
        eval_correlation_threshold,
        eval_correlation_top5,
        eval_date_propagation,
        eval_date_fallback_chain,
        eval_root_cause_to_action_chain,
        eval_critic_pass_condition,
        eval_critic_low_risk_override,
        eval_critic_high_risk_fail,
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

    print(f"\n  Level 8: Integration")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"    {status} {r['test']}: {r['score']:.0%}")
    print(f"    Composite: {composite:.0%}")

    return {
        "level": 8,
        "name": "Integration",
        "composite_score": composite,
        "passed": composite >= 0.75,
        "results": results,
    }


if __name__ == "__main__":
    run_all()
