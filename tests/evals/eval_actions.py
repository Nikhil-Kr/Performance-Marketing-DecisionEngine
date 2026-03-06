"""
Level 4: Action Appropriateness Eval

Given a diagnosis, does the proposer recommend the right types of actions?

Checks:
  1. Does it propose at least one action? (not empty)
  2. Are the action types sensible for the scenario? (expected types)
  3. Does it avoid inappropriate actions? (e.g., "pause" for a pixel issue)
  4. Is the platform correct? (google_ads for google channels, etc.)
  5. Do actions have complete payloads? (all required fields present)

Usage:
    python -m tests.evals.eval_actions
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["DATA_LAYER_MODE"] = "mock"

from tests.evals.eval_config import SCENARIOS, ACTION_SCORING, PASS_THRESHOLDS
from src.nodes.proposer.action_mapper import propose_actions


def _build_state_with_diagnosis(scenario: dict, root_cause_override: str = None) -> dict:
    """Build a minimal state as if the explainer just ran."""
    injected = scenario["injected_anomaly"]
    direction = injected.get("direction", "spike")
    custom = scenario.get("synthetic_values", {})

    # Use the ground truth cause as the diagnosis root cause.
    # This tests whether the proposer picks the right actions given
    # a CORRECT diagnosis — isolating the proposer from upstream errors.
    root_cause = root_cause_override or scenario["ground_truth_cause"]

    if custom:
        current_value = custom["current_value"]
        expected_value = custom["expected_value"]
        deviation_pct = custom["deviation_pct"]
    elif direction == "spike":
        current_value = 12000.0
        expected_value = 4000.0
        deviation_pct = 200.0
    else:
        current_value = 200.0
        expected_value = 4000.0
        deviation_pct = -95.0

    return {
        "messages": [],
        "selected_anomaly": {
            "channel": injected["channel"],
            "metric": injected.get("metric", "cpa"),
            "direction": direction,
            "severity": injected.get("severity", "high"),
            "current_value": current_value,
            "expected_value": expected_value,
            "deviation_pct": deviation_pct,
        },
        "diagnosis": {
            "root_cause": root_cause,
            "confidence": 0.85,
            "supporting_evidence": ["Test evidence"],
            "recommended_actions": ["Adjust bidding strategy"],
            "executive_summary": "Test summary.",
        },
        "proposed_actions": [],
        "current_node": "explainer",
    }


def eval_action_types(scenario: dict) -> dict:
    """Check whether proposed action types match expected types for this scenario."""
    state = _build_state_with_diagnosis(scenario)

    try:
        result = propose_actions(state)
        actions = result.get("proposed_actions", [])
    except Exception as e:
        return {
            "scenario": scenario["id"],
            "error": str(e),
            "score": 0.0,
        }

    if not actions:
        return {
            "scenario": scenario["id"],
            "actions": [],
            "has_actions": False,
            "score": 0.0,
        }

    expected = set(scenario.get("expected_action_types", []))
    inappropriate = set(scenario.get("inappropriate_actions", []))
    proposed_types = [a.get("action_type") for a in actions]

    # Score each proposed action
    action_scores = []
    for a_type in proposed_types:
        if a_type in expected:
            action_scores.append(("exact", ACTION_SCORING["exact_match"]))
        elif a_type in inappropriate:
            action_scores.append(("inappropriate", ACTION_SCORING["inappropriate"]))
        elif a_type == "notification":
            # Notification is always at least partially appropriate
            action_scores.append(("partial", ACTION_SCORING["partial_match"]))
        else:
            action_scores.append(("partial", ACTION_SCORING["partial_match"]))

    # Check if at least one expected action type was proposed
    expected_hit = bool(expected & set(proposed_types))

    # Average score across all proposed actions
    avg_score = sum(s for _, s in action_scores) / len(action_scores) if action_scores else 0.0

    # Bonus for hitting expected types, penalty for missing them entirely
    if expected_hit:
        avg_score = min(1.0, avg_score + 0.1)
    elif expected:
        avg_score = max(0.0, avg_score - 0.2)

    return {
        "scenario": scenario["id"],
        "proposed_types": proposed_types,
        "expected_types": list(expected),
        "inappropriate_types": list(inappropriate),
        "action_scores": action_scores,
        "expected_hit": expected_hit,
        "has_actions": True,
        "score": avg_score,
    }


def eval_platform_correctness(scenario: dict) -> dict:
    """Check whether actions target the correct platform."""
    state = _build_state_with_diagnosis(scenario)

    try:
        result = propose_actions(state)
        actions = result.get("proposed_actions", [])
    except Exception as e:
        return {"scenario": scenario["id"], "error": str(e), "score": 0.0}

    if not actions:
        return {"scenario": scenario["id"], "score": 0.0}

    expected_platform = scenario.get("expected_platform")
    if not expected_platform:
        return {"scenario": scenario["id"], "score": 1.0, "note": "no platform expectation"}

    correct = 0
    for action in actions:
        platform = action.get("platform", "")
        # Notification actions may target any platform, so don't penalize
        if action.get("action_type") == "notification":
            correct += 1
        elif platform == expected_platform:
            correct += 1

    score = correct / len(actions) if actions else 0.0

    return {
        "scenario": scenario["id"],
        "expected_platform": expected_platform,
        "action_platforms": [a.get("platform") for a in actions],
        "correct_count": correct,
        "total": len(actions),
        "score": score,
    }


def eval_payload_completeness(scenario: dict) -> dict:
    """Check whether action payloads have all required fields."""
    state = _build_state_with_diagnosis(scenario)

    try:
        result = propose_actions(state)
        actions = result.get("proposed_actions", [])
    except Exception as e:
        return {"scenario": scenario["id"], "error": str(e), "score": 0.0}

    required_fields = [
        "action_id",
        "action_type",
        "platform",
        "operation",
        "parameters",
        "estimated_impact",
        "risk_level",
    ]

    scores = []
    issues = []
    for i, action in enumerate(actions):
        present = sum(1 for f in required_fields if f in action and action[f] is not None)
        score = present / len(required_fields)
        scores.append(score)
        missing = [f for f in required_fields if f not in action or action[f] is None]
        if missing:
            issues.append({"action_index": i, "missing": missing})

    avg_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "scenario": scenario["id"],
        "action_count": len(actions),
        "payload_scores": scores,
        "issues": issues,
        "score": avg_score,
    }


def eval_no_action_on_empty_diagnosis() -> dict:
    """Edge case: what happens if diagnosis is None/empty?"""
    state = {
        "messages": [],
        "selected_anomaly": {"channel": "google_search", "metric": "cpa"},
        "diagnosis": None,
        "proposed_actions": [],
        "current_node": "explainer",
    }

    try:
        result = propose_actions(state)
        actions = result.get("proposed_actions", [])
        error_msg = result.get("error")
        # Should gracefully return empty actions, not crash
        correct = len(actions) == 0 and error_msg is not None
    except Exception as e:
        correct = False
        error_msg = str(e)

    return {
        "test": "empty_diagnosis_handling",
        "correct": correct,
        "error": error_msg,
        "score": 1.0 if correct else 0.0,
    }


def run_all() -> dict:
    """Run all Level 4 evals."""
    print("\n" + "=" * 60)
    print("LEVEL 4: ACTION APPROPRIATENESS")
    print("=" * 60)

    all_type_results = []
    all_platform_results = []
    all_payload_results = []

    for scenario in SCENARIOS:
        types = eval_action_types(scenario)
        platform = eval_platform_correctness(scenario)
        payload = eval_payload_completeness(scenario)

        all_type_results.append(types)
        all_platform_results.append(platform)
        all_payload_results.append(payload)

        print(f"\n  {scenario['id']}:")
        print(f"    Action Types:    {types['score']:.0%}  proposed={types.get('proposed_types', [])}")
        if not types.get("expected_hit") and types.get("expected_types"):
            print(f"      ⚠️ Expected {types['expected_types']} but none were proposed")
        print(f"    Platform:        {platform['score']:.0%}")
        print(f"    Payload:         {payload['score']:.0%}")

    # Edge case
    empty = eval_no_action_on_empty_diagnosis()
    print(f"\n  Edge Case (empty diagnosis): {'✅' if empty['correct'] else '❌'}")

    # Composite
    type_avg = sum(r["score"] for r in all_type_results) / len(all_type_results) if all_type_results else 0.0
    platform_avg = sum(r["score"] for r in all_platform_results) / len(all_platform_results) if all_platform_results else 0.0
    payload_avg = sum(r["score"] for r in all_payload_results) / len(all_payload_results) if all_payload_results else 0.0

    composite = (
        type_avg * 0.5 +
        platform_avg * 0.25 +
        payload_avg * 0.2 +
        empty["score"] * 0.05
    )

    passed = composite >= PASS_THRESHOLDS["action_appropriateness"]

    print(f"\n  Type Avg:            {type_avg:.0%}")
    print(f"  Platform Avg:        {platform_avg:.0%}")
    print(f"  Payload Avg:         {payload_avg:.0%}")
    print(f"  COMPOSITE SCORE:     {composite:.0%}")
    print(f"  STATUS:              {'✅ PASS' if passed else '❌ FAIL'}")

    return {
        "level": 4,
        "name": "Action Appropriateness",
        "type_results": all_type_results,
        "platform_results": all_platform_results,
        "payload_results": all_payload_results,
        "edge_empty": empty,
        "type_avg": type_avg,
        "platform_avg": platform_avg,
        "payload_avg": payload_avg,
        "composite_score": composite,
        "passed": passed,
    }


if __name__ == "__main__":
    run_all()