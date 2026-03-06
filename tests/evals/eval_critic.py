"""
Level 3: Critic Calibration Eval

Tests whether the Triple-Lock critic correctly:
  - PASSES good diagnoses (specificity)
  - REJECTS hallucinated diagnoses (sensitivity)
  - REJECTS ungrounded/vague diagnoses (sensitivity)

This is critical because a critic that passes everything is useless,
and a critic that rejects everything blocks the pipeline.

Usage:
    python -m tests.evals.eval_critic
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["DATA_LAYER_MODE"] = "mock"

from tests.evals.eval_config import CRITIC_CALIBRATION, PASS_THRESHOLDS
from src.nodes.critic.validator import validate_diagnosis


def _build_state_with_diagnosis(diagnosis: dict, anomaly: dict) -> dict:
    """Build a minimal ExpeditionState with a diagnosis to validate."""
    return {
        "messages": [],
        "diagnosis": diagnosis,
        "selected_anomaly": anomaly,
        "investigation_evidence": {
            "anomaly": anomaly,
            "performance_summary": "Spend increased 3x over last 3 days. ROAS dropped 70%.",
            "campaign_breakdown": "PMax asset group 'Prospecting' responsible for 80% of overspend.",
        },
        "investigation_summary": "Investigation found PMax overspend on YouTube placements.",
        "historical_incidents": [],
        "rag_context": None,
        "critic_validation": None,
        "validation_passed": False,
        "current_node": "critic",
    }


def eval_specificity() -> dict:
    """
    Test: Does the critic PASS a well-grounded, accurate diagnosis?

    Expected: validation_passed = True, hallucination_risk < 0.5
    """
    anomaly = CRITIC_CALIBRATION["anomaly_for_calibration"]
    good = CRITIC_CALIBRATION["good_diagnosis"]
    state = _build_state_with_diagnosis(good, anomaly)

    try:
        result = validate_diagnosis(state)
        passed = result.get("validation_passed", False)
        risk = result.get("critic_validation", {}).get("hallucination_risk", 1.0)
        error = None
    except Exception as e:
        passed = False
        risk = 1.0
        error = str(e)

    return {
        "test": "specificity_good_diagnosis",
        "validation_passed": passed,
        "hallucination_risk": risk,
        "error": error,
        # A good diagnosis should pass
        "correct": passed is True,
    }


def eval_sensitivity_hallucinated() -> dict:
    """
    Test: Does the critic REJECT a diagnosis full of fabricated evidence?

    Expected: validation_passed = False, hallucination_risk > 0.5
    """
    anomaly = CRITIC_CALIBRATION["anomaly_for_calibration"]
    bad = CRITIC_CALIBRATION["bad_diagnosis_hallucinated"]
    state = _build_state_with_diagnosis(bad, anomaly)

    try:
        result = validate_diagnosis(state)
        passed = result.get("validation_passed", False)
        risk = result.get("critic_validation", {}).get("hallucination_risk", 0.0)
        issues = result.get("critic_validation", {}).get("issues", [])
        error = None
    except Exception as e:
        passed = True  # If it errors, that's a failure to reject
        risk = 0.0
        issues = []
        error = str(e)

    return {
        "test": "sensitivity_hallucinated",
        "validation_passed": passed,
        "hallucination_risk": risk,
        "issues_found": issues,
        "error": error,
        # A hallucinated diagnosis should FAIL
        "correct": passed is False,
    }


def eval_sensitivity_ungrounded() -> dict:
    """
    Test: Does the critic REJECT a vague, ungrounded diagnosis?

    Expected: validation_passed = False or hallucination_risk elevated
    """
    anomaly = CRITIC_CALIBRATION["anomaly_for_calibration"]
    bad = CRITIC_CALIBRATION["bad_diagnosis_ungrounded"]
    state = _build_state_with_diagnosis(bad, anomaly)

    try:
        result = validate_diagnosis(state)
        passed = result.get("validation_passed", False)
        risk = result.get("critic_validation", {}).get("hallucination_risk", 0.0)
        issues = result.get("critic_validation", {}).get("issues", [])
        error = None
    except Exception as e:
        passed = True
        risk = 0.0
        issues = []
        error = str(e)

    return {
        "test": "sensitivity_ungrounded",
        "validation_passed": passed,
        "hallucination_risk": risk,
        "issues_found": issues,
        "error": error,
        # An ungrounded diagnosis should FAIL (or at least have elevated risk)
        "correct": passed is False or risk > 0.4,
    }


def eval_risk_ordering() -> dict:
    """
    Test: Is hallucination_risk ordered correctly?

    Expected: good < ungrounded < hallucinated
    (The fabricated diagnosis should score highest risk)
    """
    anomaly = CRITIC_CALIBRATION["anomaly_for_calibration"]

    risks = {}
    for label, diag in [
        ("good", CRITIC_CALIBRATION["good_diagnosis"]),
        ("ungrounded", CRITIC_CALIBRATION["bad_diagnosis_ungrounded"]),
        ("hallucinated", CRITIC_CALIBRATION["bad_diagnosis_hallucinated"]),
    ]:
        state = _build_state_with_diagnosis(diag, anomaly)
        try:
            result = validate_diagnosis(state)
            risk = result.get("critic_validation", {}).get("hallucination_risk", 0.5)
        except Exception:
            risk = 0.5  # neutral on error
        risks[label] = risk

    # Check ordering
    ordered = risks["good"] < risks["hallucinated"]
    partially_ordered = risks["good"] <= risks["ungrounded"] <= risks["hallucinated"]

    return {
        "test": "risk_ordering",
        "risks": risks,
        "good_lt_hallucinated": ordered,
        "fully_ordered": partially_ordered,
        "correct": ordered,  # at minimum, good must be less risky than hallucinated
    }


def run_all() -> dict:
    """Run all Level 3 evals."""
    print("\n" + "=" * 60)
    print("LEVEL 3: CRITIC CALIBRATION")
    print("=" * 60)

    specificity = eval_specificity()
    print(f"\n  Specificity (good → pass):   ", end="")
    if specificity["correct"]:
        print(f"✅ PASS (risk={specificity['hallucination_risk']:.2f})")
    else:
        print(f"❌ FAIL (risk={specificity['hallucination_risk']:.2f})")
        if specificity["error"]:
            print(f"    Error: {specificity['error']}")

    sens_halluc = eval_sensitivity_hallucinated()
    print(f"  Sensitivity (hallucinated → reject): ", end="")
    if sens_halluc["correct"]:
        print(f"✅ PASS (risk={sens_halluc['hallucination_risk']:.2f})")
    else:
        print(f"❌ FAIL (risk={sens_halluc['hallucination_risk']:.2f})")
        if sens_halluc["error"]:
            print(f"    Error: {sens_halluc['error']}")

    sens_unground = eval_sensitivity_ungrounded()
    print(f"  Sensitivity (ungrounded → reject):   ", end="")
    if sens_unground["correct"]:
        print(f"✅ PASS (risk={sens_unground['hallucination_risk']:.2f})")
    else:
        print(f"❌ FAIL (risk={sens_unground['hallucination_risk']:.2f})")

    ordering = eval_risk_ordering()
    print(f"  Risk Ordering (good < hallucinated): ", end="")
    if ordering["correct"]:
        print(f"✅ PASS")
    else:
        print(f"❌ FAIL")
    print(f"    Risks: good={ordering['risks']['good']:.2f}, "
          f"ungrounded={ordering['risks']['ungrounded']:.2f}, "
          f"hallucinated={ordering['risks']['hallucinated']:.2f}")

    # Scoring
    tests = [specificity, sens_halluc, sens_unground, ordering]
    correct_count = sum(1 for t in tests if t["correct"])
    composite = correct_count / len(tests)

    sensitivity = sum(1 for t in [sens_halluc, sens_unground] if t["correct"]) / 2
    specificity_score = 1.0 if specificity["correct"] else 0.0

    print(f"\n  Sensitivity:         {sensitivity:.0%}")
    print(f"  Specificity:         {specificity_score:.0%}")
    print(f"  COMPOSITE SCORE:     {composite:.0%}")
    print(f"  STATUS:              {'✅ PASS' if composite >= 0.75 else '❌ FAIL'}")

    return {
        "level": 3,
        "name": "Critic Calibration",
        "specificity": specificity,
        "sensitivity_hallucinated": sens_halluc,
        "sensitivity_ungrounded": sens_unground,
        "risk_ordering": ordering,
        "sensitivity_score": sensitivity,
        "specificity_score": specificity_score,
        "composite_score": composite,
        "passed": composite >= 0.75,
    }


if __name__ == "__main__":
    run_all()