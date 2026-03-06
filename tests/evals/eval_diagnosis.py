"""
Level 2: Diagnosis Correctness Eval

Runs the full pipeline on each known scenario and uses LLM-as-judge
to score whether the diagnosis matches the known ground truth.

Two modes:
  - MockLLM mode (fast, free): structural checks only — verifies the
    pipeline doesn't crash and output shapes are correct
  - Real Gemini mode (slow, costs money): full LLM-as-judge scoring
    on accuracy, groundedness, and completeness

Usage:
    # Structural checks only (MockLLM)
    python -m tests.evals.eval_diagnosis

    # Full LLM-as-judge (requires GCP credentials)
    python -m tests.evals.eval_diagnosis --real-llm
"""
import sys
import os
import re
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["DATA_LAYER_MODE"] = "mock"

from tests.evals.eval_config import (
    SCENARIOS,
    DIAGNOSIS_GRADER_SYSTEM,
    DIAGNOSIS_GRADER_USER,
    PASS_THRESHOLDS,
)


def _run_pipeline_for_anomaly(anomaly: dict) -> dict:
    """Run the full Expedition pipeline on a single anomaly."""
    from src.graph import run_expedition

    initial_state = {
        "selected_anomaly": anomaly,
        "anomalies": [anomaly],
    }

    try:
        result = run_expedition(initial_state)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_synthetic_anomaly(scenario: dict) -> dict:
    """
    Build a full anomaly dict from scenario config.
    Uses scenario-specific synthetic_values when provided,
    otherwise falls back to direction-appropriate defaults.
    """
    injected = scenario["injected_anomaly"]
    direction = injected.get("direction", "spike")
    custom = scenario.get("synthetic_values", {})

    if custom:
        current_value = custom["current_value"]
        expected_value = custom["expected_value"]
        deviation_pct = custom["deviation_pct"]
        z_score = 4.5 if direction == "spike" else -4.5
    elif direction == "spike":
        current_value = 12000.0
        expected_value = 4000.0
        deviation_pct = 200.0
        z_score = 4.5
    else:  # drop
        current_value = 200.0
        expected_value = 4000.0
        deviation_pct = -95.0
        z_score = -4.5

    return {
        "channel": injected["channel"],
        "metric": injected.get("metric", "cpa"),
        "direction": direction,
        "severity": injected.get("severity", "high"),
        "current_value": current_value,
        "expected_value": expected_value,
        "deviation_pct": deviation_pct,
        "z_score": z_score,
        "detected_at": "2026-03-04T00:00:00",
        "_id": scenario["id"],
    }


def check_grounding(diagnosis: dict, result: dict) -> dict:
    """
    Data grounding verifier — catches hallucinated numbers.

    Extracts all numeric values from the diagnosis text (dollar amounts,
    percentages, multipliers, large integers) and checks whether each
    appears in the raw evidence payload that was actually fed to the LLM.

    A number that appears in the diagnosis but NOT in the evidence was
    either invented by the LLM or drawn from its training priors — both
    are hallucinations in the context of this investigation.

    Returns:
        grounding_score: 1.0 = all numbers grounded, 0.0 = all fabricated
        numbers_checked: count of numeric values extracted from diagnosis
        ungrounded_numbers: list of numbers not found in evidence
        passed: grounding_score >= 0.8
    """
    # Collect all evidence text: investigation evidence + anomaly values
    evidence_parts = []
    evidence = result.get("investigation_evidence") or {}
    anomaly = result.get("selected_anomaly") or {}

    for val in evidence.values():
        if isinstance(val, str):
            evidence_parts.append(val)
        elif isinstance(val, dict):
            evidence_parts.append(json.dumps(val))

    # Always include the anomaly's own numeric fields as grounded sources
    for key in ("current_value", "expected_value", "deviation_pct", "z_score"):
        if key in anomaly:
            evidence_parts.append(str(anomaly[key]))

    evidence_str = " ".join(evidence_parts).lower()

    # Build the full diagnosis text corpus
    diagnosis_text = " ".join(filter(None, [
        diagnosis.get("root_cause", ""),
        " ".join(diagnosis.get("supporting_evidence", [])),
        diagnosis.get("executive_summary", ""),
    ])).lower()

    # Extract dollar amounts ($1,234), percentages (45%), multipliers (3x),
    # and large standalone integers (4+ digits, e.g. "12000")
    number_patterns = re.findall(
        r'\$[\d,]+(?:\.\d+)?'       # $1,234 or $12,000.50
        r'|[\d]+(?:\.\d+)?%'        # 45% or 3.5%
        r'|[\d]+(?:\.\d+)?x\b'      # 3x or 2.5x
        r'|\b[\d]{4,}\b',           # 4+ digit integers like 12000
        diagnosis_text,
    )

    if not number_patterns:
        # No specific numbers claimed — can't verify but can't penalise
        return {
            "grounding_score": 1.0,
            "numbers_checked": 0,
            "ungrounded_numbers": [],
            "passed": True,
        }

    ungrounded = []
    for num in number_patterns:
        # Normalize for comparison: strip $, %, x, commas
        normalized = re.sub(r'[$%x,]', '', num).strip()
        # Also try rounding-tolerant match (integer part only for decimals)
        int_part = normalized.split('.')[0]
        if normalized not in evidence_str and int_part not in evidence_str:
            ungrounded.append(num)

    grounding_score = 1.0 - (len(ungrounded) / len(number_patterns))

    return {
        "grounding_score": round(grounding_score, 3),
        "numbers_checked": len(number_patterns),
        "ungrounded_numbers": ungrounded,
        "passed": grounding_score >= 0.8,
    }


def eval_grounding(scenarios: list[dict] | None = None) -> dict:
    """
    Grounding eval — runs pipeline and verifies diagnosis numbers
    are traceable back to the evidence payload (no hallucinated specifics).
    """
    scenarios = scenarios or SCENARIOS
    results = []

    for scenario in scenarios:
        anomaly = _build_synthetic_anomaly(scenario)
        run = _run_pipeline_for_anomaly(anomaly)

        if not run["success"]:
            results.append({
                "scenario": scenario["id"],
                "error": run["error"],
                "grounding_score": 0.0,
                "passed": False,
            })
            continue

        result = run["result"]
        diagnosis = result.get("diagnosis") or {}
        grounding = check_grounding(diagnosis, result)

        results.append({
            "scenario": scenario["id"],
            **grounding,
        })

    composite = sum(r["grounding_score"] for r in results) / len(results) if results else 0.0

    return {
        "test": "grounding",
        "results": results,
        "composite_score": composite,
    }


def eval_structural(scenarios: list[dict] | None = None) -> dict:
    """
    Structural checks (works with MockLLM — no GCP needed).

    Verifies:
      1. Pipeline completes without error
      2. Diagnosis dict has required keys
      3. Confidence is a float 0-1
      4. Supporting evidence is a non-empty list
      5. Root cause is a non-empty string
      6. Proposed actions is a non-empty list
    """
    scenarios = scenarios or SCENARIOS
    results = []

    for scenario in scenarios:
        anomaly = _build_synthetic_anomaly(scenario)
        run = _run_pipeline_for_anomaly(anomaly)

        checks = {}

        if not run["success"]:
            checks = {
                "pipeline_completed": False,
                "error": run["error"],
            }
            results.append({"scenario": scenario["id"], "checks": checks, "score": 0.0})
            continue

        result = run["result"]
        diagnosis = result.get("diagnosis") or {}

        checks["pipeline_completed"] = True
        checks["has_diagnosis"] = diagnosis != {}
        checks["has_root_cause"] = bool(diagnosis.get("root_cause"))
        checks["has_evidence"] = len(diagnosis.get("supporting_evidence", [])) > 0
        checks["confidence_valid"] = (
            isinstance(diagnosis.get("confidence"), (int, float))
            and 0 <= diagnosis.get("confidence", -1) <= 1
        )
        checks["has_actions"] = len(result.get("proposed_actions", [])) > 0
        checks["has_critic_validation"] = result.get("critic_validation") is not None
        checks["has_executive_summary"] = bool(diagnosis.get("executive_summary"))

        passed = sum(1 for v in checks.values() if v is True)
        total = sum(1 for v in checks.values() if isinstance(v, bool))
        score = passed / total if total > 0 else 0.0

        results.append({
            "scenario": scenario["id"],
            "checks": checks,
            "score": score,
        })

    composite = sum(r["score"] for r in results) / len(results) if results else 0.0

    return {
        "test": "structural",
        "results": results,
        "composite_score": composite,
    }


def eval_llm_judge(scenarios: list[dict] | None = None) -> dict:
    """
    LLM-as-judge evaluation (requires real Gemini).

    For each scenario:
      1. Runs full pipeline
      2. Sends diagnosis + ground truth to a grader LLM
      3. Grader scores accuracy, groundedness, completeness (1-5 each)
      4. Checks required/forbidden themes
    """
    from src.intelligence.models import get_llm_safe

    scenarios = scenarios or SCENARIOS
    grader = get_llm_safe("tier2")
    results = []

    for scenario in scenarios:
        print(f"\n  Evaluating: {scenario['id']}...")

        anomaly = _build_synthetic_anomaly(scenario)
        run = _run_pipeline_for_anomaly(anomaly)

        if not run["success"]:
            results.append({
                "scenario": scenario["id"],
                "error": run["error"],
                "scores": {"accuracy": 0, "groundedness": 0, "completeness": 0},
            })
            continue

        result = run["result"]
        diagnosis = result.get("diagnosis") or {}

        # Build grader prompt
        grader_prompt = DIAGNOSIS_GRADER_USER.format(
            ground_truth=scenario["ground_truth_cause"],
            required_themes=", ".join(scenario["required_themes"]),
            forbidden_themes=", ".join(scenario["forbidden_themes"]),
            diagnosis_root_cause=diagnosis.get("root_cause", "N/A"),
            diagnosis_confidence=diagnosis.get("confidence", "N/A"),
            diagnosis_evidence=json.dumps(diagnosis.get("supporting_evidence", []), indent=2),
            diagnosis_summary=diagnosis.get("executive_summary", "N/A"),
        )

        try:
            messages = [
                {"role": "system", "content": DIAGNOSIS_GRADER_SYSTEM},
                {"role": "user", "content": grader_prompt},
            ]
            from src.intelligence.models import extract_content
            response = grader.invoke(messages)
            raw = extract_content(response).strip()

            # Parse JSON from response (handle markdown fences)
            clean = raw.replace("```json", "").replace("```", "").strip()
            grades = json.loads(clean)
        except Exception as e:
            print(f"    ⚠️ Grader failed: {e}")
            grades = {
                "accuracy": 1, "groundedness": 1, "completeness": 1,
                "reasoning": f"Grader error: {e}",
                "required_themes_present": [],
                "required_themes_missing": scenario["required_themes"],
                "forbidden_themes_found": [],
            }

        # Normalize 1-5 → 0.0-1.0
        scores = {
            "accuracy": (grades.get("accuracy", 1) - 1) / 4,
            "groundedness": (grades.get("groundedness", 1) - 1) / 4,
            "completeness": (grades.get("completeness", 1) - 1) / 4,
        }

        # Theme penalties
        missing = grades.get("required_themes_missing", [])
        forbidden_found = grades.get("forbidden_themes_found", [])
        theme_penalty = (
            len(missing) * 0.1 +    # -0.1 per missing required theme
            len(forbidden_found) * 0.15  # -0.15 per forbidden theme found
        )

        composite = max(0.0, (
            scores["accuracy"] * 0.5 +
            scores["groundedness"] * 0.3 +
            scores["completeness"] * 0.2 -
            theme_penalty
        ))

        results.append({
            "scenario": scenario["id"],
            "raw_grades": grades,
            "scores": scores,
            "theme_penalty": theme_penalty,
            "composite": composite,
            "reasoning": grades.get("reasoning", ""),
        })

    overall = sum(r.get("composite", 0) for r in results) / len(results) if results else 0.0

    return {
        "test": "llm_judge",
        "results": results,
        "composite_score": overall,
    }


def run_all(use_real_llm: bool = False) -> dict:
    """Run all Level 2 evals."""
    print("\n" + "=" * 60)
    print("LEVEL 2: DIAGNOSIS CORRECTNESS")
    print("=" * 60)

    # Always run structural
    structural = eval_structural()
    print(f"\n  Structural Checks:")
    for r in structural["results"]:
        status = "✅" if r["score"] >= 0.8 else "❌"
        print(f"    {status} {r['scenario']}: {r['score']:.0%}")
        failed = [k for k, v in r["checks"].items() if v is False]
        if failed:
            for f in failed:
                print(f"       ↳ missing: {f}")
    print(f"  Structural Composite: {structural['composite_score']:.0%}")

    # Always run grounding verifier
    grounding = eval_grounding()
    print(f"\n  Grounding Verifier (numbers in diagnosis vs evidence):")
    for r in grounding["results"]:
        if "error" in r:
            print(f"    ❌ {r['scenario']}: pipeline error")
            continue
        status = "✅" if r["passed"] else "⚠️"
        print(f"    {status} {r['scenario']}: {r['grounding_score']:.0%} ({r['numbers_checked']} numbers checked)")
        if r["ungrounded_numbers"]:
            print(f"       ↳ ungrounded: {r['ungrounded_numbers']}")
    print(f"  Grounding Composite: {grounding['composite_score']:.0%}")

    # LLM judge only if requested
    llm_judge = None
    if use_real_llm:
        print(f"\n  LLM-as-Judge (using real Gemini):")
        llm_judge = eval_llm_judge()
        for r in llm_judge["results"]:
            if "error" in r:
                print(f"    ❌ {r['scenario']}: pipeline error")
                continue
            s = r["scores"]
            print(f"    {r['scenario']}:")
            print(f"       Accuracy:      {s['accuracy']:.0%}")
            print(f"       Groundedness:  {s['groundedness']:.0%}")
            print(f"       Completeness:  {s['completeness']:.0%}")
            if r["theme_penalty"] > 0:
                print(f"       Theme Penalty: -{r['theme_penalty']:.0%}")
            print(f"       Composite:     {r['composite']:.0%}")
            print(f"       Reasoning:     {r['reasoning']}")
        print(f"  LLM Judge Composite: {llm_judge['composite_score']:.0%}")
    else:
        print(f"\n  (Skipping LLM-as-judge — run with --real-llm for full eval)")

    # Composite:
    #   Quick mode:  structural 60% + grounding 40%
    #   Full mode:   structural 20% + grounding 20% + llm_judge 60%
    if llm_judge:
        composite = (
            structural["composite_score"] * 0.20 +
            grounding["composite_score"] * 0.20 +
            llm_judge["composite_score"] * 0.60
        )
    else:
        composite = (
            structural["composite_score"] * 0.60 +
            grounding["composite_score"] * 0.40
        )

    passed = composite >= PASS_THRESHOLDS["diagnosis_accuracy"]
    print(f"\n  COMPOSITE SCORE:     {composite:.0%}")
    print(f"  STATUS:              {'✅ PASS' if passed else '❌ FAIL'}")

    return {
        "level": 2,
        "name": "Diagnosis Correctness",
        "structural": structural,
        "grounding": grounding,
        "llm_judge": llm_judge,
        "composite_score": composite,
        "passed": passed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-llm", action="store_true", help="Use real Gemini for LLM-as-judge")
    args = parser.parse_args()
    run_all(use_real_llm=args.real_llm)