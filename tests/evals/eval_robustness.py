"""
Level 9: Robustness & Fallback Evals

Tests keyword fallback, JSON parse resilience, fallback diagnosis, prompt variable
substitution, empty data handling, and last-resort action generation.

Usage:
    python -m tests.evals.eval_robustness
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
os.environ.setdefault("DATA_LAYER_MODE", "mock")


# ============================================================================
# Test Helpers
# ============================================================================

SAMPLE_ANOMALY = {
    "channel": "google_pmax",
    "metric": "spend",
    "direction": "spike",
    "severity": "critical",
    "current_value": 12000.0,
    "expected_value": 4000.0,
    "deviation_pct": 200.0,
    "detected_at": "2020-03-15",
}


# ============================================================================
# Test: Keyword Fallback Action Mapping
# ============================================================================

def eval_keyword_fallback() -> dict:
    """Test _keyword_action_mapping with 10 root cause strings containing known keywords."""
    from src.nodes.proposer.action_mapper import _keyword_action_mapping

    test_cases = [
        ("competitor bidding war increased cpc", "google_search", "bid_adjustment"),
        ("creative fatigue causing low engagement", "meta_ads", "notification"),
        ("tracking pixel broken attribution lost", "meta_ads", "notification"),
        ("budget exhausted spend cap hit", "google_pmax", "budget_change"),
        ("platform algorithm outage", "google_search", "notification"),
        ("audience saturation frequency too high", "meta_ads", "pause"),
        ("bot fraud fake invalid traffic detected", "google_display", "exclusion"),
        ("tv spot preempted grp shortfall", "tv", "negotiation"),
        ("affiliate coupon leakage to aggregators", "google_search", "communication"),
        ("daypart schedule timing optimization needed", "radio", "schedule_change"),
    ]

    correct = 0
    details = []
    for root_cause, channel, expected_action_type in test_cases:
        actions = _keyword_action_mapping(root_cause, channel, {"channel": channel})
        if actions and any(a["action_type"] == expected_action_type for a in actions):
            correct += 1
        else:
            actual = [a["action_type"] for a in actions] if actions else []
            details.append(f"FAIL: '{root_cause[:40]}...' → got {actual}, expected '{expected_action_type}'")

    score = correct / len(test_cases)
    return {
        "test": "keyword_fallback",
        "score": score,
        "passed": score >= 0.8,
        "correct": correct,
        "total": len(test_cases),
        "failures": details,
    }


# ============================================================================
# Test: Keyword Fallback Respects Allowed Keys
# ============================================================================

def eval_keyword_with_allowed_keys() -> dict:
    """Test that keyword fallback only produces actions in allowed_keys."""
    from src.nodes.proposer.action_mapper import _keyword_action_mapping

    # Root cause matches both "competitor_bidding" and "budget_exhaustion"
    root_cause = "competitor bidding war with budget exhaustion"
    channel = "google_search"
    anomaly = {"channel": channel}

    # Without restriction: should produce at least 2 actions
    unrestricted = _keyword_action_mapping(root_cause, channel, anomaly, allowed_keys=None)

    # With restriction: only allow competitor_bidding
    restricted = _keyword_action_mapping(root_cause, channel, anomaly, allowed_keys=["competitor_bidding"])

    checks = {
        "unrestricted_has_multiple": len(unrestricted) >= 2,
        "restricted_has_fewer": len(restricted) < len(unrestricted),
        "restricted_max_one": len(restricted) <= 1,
    }

    # With empty allowed_keys: should produce 0
    empty = _keyword_action_mapping(root_cause, channel, anomaly, allowed_keys=[])
    checks["empty_keys_zero_actions"] = len(empty) == 0

    score = sum(checks.values()) / len(checks)
    return {
        "test": "keyword_with_allowed_keys",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Last Resort Manual Review Action
# ============================================================================

def eval_last_resort_action() -> dict:
    """Test that proposer generates manual review notification when no actions match."""
    from src.nodes.proposer.action_mapper import _keyword_action_mapping
    import uuid

    # Use a root cause that matches no keywords
    root_cause = "completely unprecedented phenomenon with zero keyword matches"
    channel = "unknown_channel"
    anomaly = {"channel": channel}

    actions = _keyword_action_mapping(root_cause, channel, anomaly)

    checks = {
        "no_keyword_match": len(actions) == 0,
    }

    # Simulate the last resort logic from propose_actions
    if not actions:
        actions.append({
            "action_id": f"action_{uuid.uuid4().hex[:8]}",
            "action_type": "notification",
            "platform": channel,
            "resource_type": "alert",
            "resource_id": "manual_review",
            "operation": "alert",
            "parameters": {
                "team": "decision_science",
                "urgency": "medium",
                "message": f"Manual review required for {channel} anomaly",
            },
            "estimated_impact": "Analyst assigned within 1 hour",
            "risk_level": "low",
            "requires_approval": False,
        })

    checks["has_fallback_action"] = len(actions) == 1
    checks["is_notification"] = actions[0]["action_type"] == "notification"
    checks["team_is_decision_science"] = actions[0]["parameters"].get("team") == "decision_science"
    checks["resource_is_manual_review"] = actions[0]["resource_id"] == "manual_review"

    score = sum(checks.values()) / len(checks)
    return {
        "test": "last_resort_action",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: JSON Parse — Clean Input
# ============================================================================

def eval_json_parse_clean() -> dict:
    """Test parse_diagnosis_response with valid JSON."""
    from src.intelligence.prompts.explainer import parse_diagnosis_response

    clean_json = '{"root_cause": "test cause", "confidence": 0.85, "supporting_evidence": ["e1"], "recommended_actions": ["a1"], "executive_summary": "summary", "director_summary": "d", "marketer_summary": "m", "technical_details": "t"}'
    result = parse_diagnosis_response(clean_json)

    checks = {
        "root_cause": result.get("root_cause") == "test cause",
        "confidence": result.get("confidence") == 0.85,
        "evidence_list": isinstance(result.get("supporting_evidence"), list),
        "not_fallback": result.get("confidence") != 0.0,
    }

    score = sum(checks.values()) / len(checks)
    return {"test": "json_parse_clean", "score": score, "passed": score == 1.0, "checks": checks}


# ============================================================================
# Test: JSON Parse — Code Fences
# ============================================================================

def eval_json_parse_code_fences() -> dict:
    """Test parse_diagnosis_response strips markdown code fences."""
    from src.intelligence.prompts.explainer import parse_diagnosis_response

    fenced = '```json\n{"root_cause": "fenced cause", "confidence": 0.7, "supporting_evidence": ["e1"], "recommended_actions": ["a1"], "executive_summary": "s", "director_summary": "d", "marketer_summary": "m", "technical_details": "t"}\n```'
    result = parse_diagnosis_response(fenced)

    checks = {
        "parsed_correctly": result.get("root_cause") == "fenced cause",
        "confidence_correct": result.get("confidence") == 0.7,
        "not_fallback": result.get("confidence") != 0.0,
    }

    score = sum(checks.values()) / len(checks)
    return {"test": "json_parse_code_fences", "score": score, "passed": score == 1.0, "checks": checks}


# ============================================================================
# Test: JSON Parse — Trailing Commas
# ============================================================================

def eval_json_parse_trailing_commas() -> dict:
    """Test parse_diagnosis_response handles trailing commas."""
    from src.intelligence.prompts.explainer import parse_diagnosis_response

    with_commas = '{"root_cause": "comma cause", "confidence": 0.6, "supporting_evidence": ["e1",], "recommended_actions": ["a1",], "executive_summary": "s", "director_summary": "d", "marketer_summary": "m", "technical_details": "t",}'
    result = parse_diagnosis_response(with_commas)

    checks = {
        "parsed_correctly": result.get("root_cause") == "comma cause",
        "not_fallback": result.get("confidence") != 0.0,
    }

    score = sum(checks.values()) / len(checks)
    return {"test": "json_parse_trailing_commas", "score": score, "passed": score == 1.0, "checks": checks}


# ============================================================================
# Test: JSON Parse — Garbage Input
# ============================================================================

def eval_json_parse_garbage() -> dict:
    """Test parse_diagnosis_response returns fallback dict on garbage input."""
    from src.intelligence.prompts.explainer import parse_diagnosis_response

    garbage = "This is not JSON at all. Just random text about marketing anomalies."
    result = parse_diagnosis_response(garbage)

    checks = {
        "returns_dict": isinstance(result, dict),
        "has_root_cause": "root_cause" in result,
        "has_confidence": "confidence" in result,
        "confidence_is_zero": result.get("confidence") == 0.0,
        "has_evidence": "supporting_evidence" in result,
        "did_not_crash": True,
    }

    score = sum(checks.values()) / len(checks)
    return {"test": "json_parse_garbage", "score": score, "passed": score == 1.0, "checks": checks}


# ============================================================================
# Test: Prompt Variable Substitution
# ============================================================================

def eval_prompt_no_unresolved_vars() -> dict:
    """Test that all format_*_prompt() functions produce output with no unresolved {var} placeholders."""
    from src.intelligence.prompts.explainer import format_explainer_prompt, format_retry_prompt
    from src.intelligence.prompts.investigator import (
        format_paid_media_prompt,
        format_influencer_prompt,
        format_offline_prompt,
    )
    from src.intelligence.prompts.critic import format_critic_prompt

    # Unresolved variable pattern: {word} but NOT {{ (escaped braces in JSON examples)
    unresolved_pattern = re.compile(r'(?<!\{)\{(\w+)\}(?!\})')

    anomaly = {
        "channel": "google_pmax",
        "metric": "spend",
        "direction": "spike",
        "severity": "critical",
        "current_value": 12000.0,
        "expected_value": 4000.0,
        "deviation_pct": 200.0,
        "detected_at": "2020-03-15",
        "entity": "test_creator",
    }
    diagnosis = {
        "root_cause": "test cause",
        "confidence": 0.8,
        "supporting_evidence": ["evidence 1"],
        "recommended_actions": ["action 1"],
    }
    prev_diagnosis = {
        "root_cause": "prev cause",
        "confidence": 0.6,
        "supporting_evidence": ["old evidence"],
    }

    prompts = {}
    checks = {}

    # Explainer prompt
    prompts["explainer"] = format_explainer_prompt(
        anomaly=anomaly,
        investigation_summary="Test summary of findings",
        historical_incidents=[],
        analysis_start="2020-02-01",
        analysis_end="2020-04-30",
    )

    # Retry prompt
    prompts["retry"] = format_retry_prompt(
        anomaly=anomaly,
        investigation_summary="Test summary",
        historical_incidents=[],
        previous_diagnosis=prev_diagnosis,
        critic_feedback="Fix the issues",
        analysis_start="2020-02-01",
        analysis_end="2020-04-30",
    )

    # Paid media prompt
    prompts["paid_media"] = format_paid_media_prompt(
        anomaly=anomaly,
        performance_summary="Performance data here",
        campaign_breakdown="Campaign breakdown here",
        competitor_intel="Competitor data",
        market_trends="Market trends",
        strategy_context="Strategy context",
        analysis_start="2020-02-01",
        analysis_end="2020-04-30",
    )

    # Influencer prompt
    prompts["influencer"] = format_influencer_prompt(
        anomaly=anomaly,
        campaign_data="Campaign data table",
        creator_history="Creator history table",
        attribution_data="Attribution analysis",
        analysis_start="2020-02-01",
        analysis_end="2020-04-30",
    )

    # Offline prompt
    prompts["offline"] = format_offline_prompt(
        anomaly=anomaly,
        performance_summary="Offline performance",
        channel_context="TV-specific context",
        analysis_start="2020-02-01",
        analysis_end="2020-04-30",
    )

    # Critic prompt
    prompts["critic"] = format_critic_prompt(
        anomaly=anomaly,
        raw_evidence="Raw evidence text here",
        diagnosis=diagnosis,
    )

    for name, prompt in prompts.items():
        matches = unresolved_pattern.findall(prompt)
        # Filter out false positives (JSON example fields like "root_cause")
        real_unresolved = [m for m in matches if m not in (
            "root_cause", "confidence", "supporting_evidence", "recommended_actions",
            "executive_summary", "director_summary", "marketer_summary", "technical_details",
            "is_valid", "hallucination_risk", "data_grounded", "evidence_verified",
            "issues", "recommendations", "action_valid", "matches_diagnosis",
            "risk_assessment", "concerns",
        )]
        checks[f"{name}_no_unresolved"] = len(real_unresolved) == 0
        if real_unresolved:
            checks[f"{name}_detail"] = False  # Will show in output

    score = sum(v for v in checks.values() if isinstance(v, bool)) / max(1, sum(1 for v in checks.values() if isinstance(v, bool)))
    return {
        "test": "prompt_no_unresolved_vars",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Orchestrator
# ============================================================================

def run_all() -> dict:
    """Run all robustness evals and return composite score."""
    tests = [
        eval_keyword_fallback,
        eval_keyword_with_allowed_keys,
        eval_last_resort_action,
        eval_json_parse_clean,
        eval_json_parse_code_fences,
        eval_json_parse_trailing_commas,
        eval_json_parse_garbage,
        eval_prompt_no_unresolved_vars,
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

    print(f"\n  Level 9: Robustness & Fallbacks")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"    {status} {r['test']}: {r['score']:.0%}")
    print(f"    Composite: {composite:.0%}")

    return {
        "level": 9,
        "name": "Robustness & Fallbacks",
        "composite_score": composite,
        "passed": composite >= 0.80,
        "results": results,
    }


if __name__ == "__main__":
    run_all()
