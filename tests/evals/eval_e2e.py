"""
Level 5: End-to-End Regression Eval

Runs the complete Expedition pipeline on each scenario and checks
composite quality metrics. Also supports snapshot mode: save a
"golden" run, then compare future runs against it to detect regressions.

This combines signals from all other levels into a single pass/fail:
  - Pipeline completes without error
  - Diagnosis has required structure
  - Router picked correct investigator
  - Critic validation ran
  - Actions were proposed
  - (Optional) Scores haven't degraded vs saved snapshot

Usage:
    # Run regression checks
    python -m tests.evals.eval_e2e

    # Save current outputs as golden snapshot
    python -m tests.evals.eval_e2e --save-snapshot

    # Compare against saved snapshot
    python -m tests.evals.eval_e2e --compare-snapshot
"""
import sys
import os
import json
import argparse
import itertools
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["DATA_LAYER_MODE"] = "mock"

from tests.evals.eval_config import SCENARIOS, PASS_THRESHOLDS

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _run_pipeline(scenario: dict) -> dict:
    """Run the full pipeline and collect all outputs."""
    from src.graph import run_expedition

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

    anomaly = {
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

    initial_state = {
        "selected_anomaly": anomaly,
        "anomalies": [anomaly],
    }

    try:
        result = run_expedition(initial_state)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def eval_e2e_scenario(scenario: dict) -> dict:
    """Run full pipeline on one scenario and score it."""
    run = _run_pipeline(scenario)

    checks = {}

    if not run["success"]:
        return {
            "scenario": scenario["id"],
            "success": False,
            "error": run["error"],
            "checks": {"pipeline_completed": False},
            "score": 0.0,
        }

    result = run["result"]
    diagnosis = result.get("diagnosis") or {}

    # --- Check 1: Pipeline completed ---
    checks["pipeline_completed"] = True

    # --- Check 2: Correct route ---
    actual_route = result.get("channel_category")
    expected_route = scenario["expected_route"]
    checks["correct_route"] = actual_route == expected_route

    # --- Check 3: Diagnosis exists with required fields ---
    checks["has_root_cause"] = bool(diagnosis.get("root_cause"))
    checks["has_evidence"] = len(diagnosis.get("supporting_evidence", [])) > 0
    checks["has_confidence"] = isinstance(diagnosis.get("confidence"), (int, float))
    checks["has_executive_summary"] = bool(diagnosis.get("executive_summary"))

    # --- Check 4: Critic ran ---
    checks["critic_ran"] = result.get("critic_validation") is not None
    checks["critic_has_risk"] = (
        isinstance(result.get("critic_validation", {}).get("hallucination_risk"), (int, float))
    )

    # --- Check 5: Actions proposed ---
    actions = result.get("proposed_actions", [])
    checks["has_actions"] = len(actions) > 0

    # --- Check 6: Actions have valid structure ---
    if actions:
        first = actions[0]
        checks["action_has_type"] = bool(first.get("action_type"))
        checks["action_has_platform"] = bool(first.get("platform"))
        checks["action_has_operation"] = bool(first.get("operation"))
    else:
        checks["action_has_type"] = False
        checks["action_has_platform"] = False
        checks["action_has_operation"] = False

    # --- Check 7: Confidence is reasonable ---
    conf = diagnosis.get("confidence", 0)
    checks["confidence_reasonable"] = 0.1 <= conf <= 1.0 if isinstance(conf, (int, float)) else False

    # --- Check 8: Hallucination risk is reasonable ---
    risk = result.get("critic_validation", {}).get("hallucination_risk", None)
    if isinstance(risk, (int, float)):
        checks["risk_not_extreme"] = risk <= scenario.get("max_hallucination_risk", 0.8)
    else:
        checks["risk_not_extreme"] = False

    # Score: fraction of checks passed
    bool_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    passed_count = sum(1 for v in bool_checks.values() if v)
    total_count = len(bool_checks)
    score = passed_count / total_count if total_count > 0 else 0.0

    # Extract key outputs for snapshot comparison
    snapshot_data = {
        "channel_category": actual_route,
        "root_cause": diagnosis.get("root_cause", ""),
        "confidence": diagnosis.get("confidence"),
        "evidence_count": len(diagnosis.get("supporting_evidence", [])),
        "hallucination_risk": risk,
        "validation_passed": result.get("validation_passed"),
        "action_count": len(actions),
        "action_types": [a.get("action_type") for a in actions],
    }

    return {
        "scenario": scenario["id"],
        "success": True,
        "checks": checks,
        "score": score,
        "passed_checks": passed_count,
        "total_checks": total_count,
        "snapshot_data": snapshot_data,
    }


def save_snapshot(results: list[dict]):
    """Save current results as golden snapshot for future comparison."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    snapshot = {
        "timestamp": timestamp,
        "scenarios": {},
    }
    for r in results:
        if r.get("snapshot_data"):
            snapshot["scenarios"][r["scenario"]] = r["snapshot_data"]

    path = SNAPSHOT_DIR / "golden.json"
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    print(f"\n  💾 Snapshot saved to {path}")
    return path


def compare_snapshot(results: list[dict]) -> dict:
    """Compare current run against saved golden snapshot."""
    path = SNAPSHOT_DIR / "golden.json"
    if not path.exists():
        return {"error": "No golden snapshot found. Run with --save-snapshot first."}

    with open(path) as f:
        golden = json.load(f)

    comparisons = []
    for r in results:
        sid = r["scenario"]
        current = r.get("snapshot_data", {})
        expected = golden.get("scenarios", {}).get(sid)

        if not expected:
            comparisons.append({"scenario": sid, "status": "no_baseline"})
            continue

        diffs = {}

        # Check if route changed
        if current.get("channel_category") != expected.get("channel_category"):
            diffs["route_changed"] = {
                "was": expected["channel_category"],
                "now": current["channel_category"],
            }

        # Check if confidence degraded significantly
        c_now = current.get("confidence") or 0
        c_was = expected.get("confidence") or 0
        if isinstance(c_now, (int, float)) and isinstance(c_was, (int, float)):
            if c_now < c_was - 0.15:
                diffs["confidence_degraded"] = {"was": c_was, "now": c_now}

        # Check if hallucination risk increased significantly
        r_now = current.get("hallucination_risk") or 0
        r_was = expected.get("hallucination_risk") or 0
        if isinstance(r_now, (int, float)) and isinstance(r_was, (int, float)):
            if r_now > r_was + 0.15:
                diffs["risk_increased"] = {"was": r_was, "now": r_now}

        # Check if actions disappeared
        a_now = current.get("action_count", 0)
        a_was = expected.get("action_count", 0)
        if a_now == 0 and a_was > 0:
            diffs["actions_disappeared"] = {"was": a_was, "now": a_now}

        comparisons.append({
            "scenario": sid,
            "status": "regression" if diffs else "stable",
            "diffs": diffs,
        })

    regressions = [c for c in comparisons if c["status"] == "regression"]

    return {
        "golden_timestamp": golden.get("timestamp"),
        "comparisons": comparisons,
        "regression_count": len(regressions),
        "regressions": regressions,
        "passed": len(regressions) == 0,
    }


def eval_consistency(scenarios: list[dict] | None = None, n_runs: int = 3) -> dict:
    """
    Behavioral consistency check — same input, stable output.

    Runs the full pipeline N times on each scenario and measures:
      - Confidence variance: std dev of confidence scores across runs
        (should be < 0.15 — high variance = unstable reasoning)
      - Action type agreement: fraction of run-pairs that agree on
        action types (should be >= 2/3 of pairs)

    A system with high scores here is deterministic enough to trust.
    A system with low scores is "hallucination-adjacent" — it changes
    its mind too easily, meaning outputs can't be relied on.
    """
    import statistics

    scenarios = scenarios or SCENARIOS
    results = []

    for scenario in scenarios:
        runs = [_run_pipeline(scenario) for _ in range(n_runs)]
        successful = [r for r in runs if r["success"]]

        if len(successful) < 2:
            results.append({
                "scenario": scenario["id"],
                "consistency_score": 0.0,
                "passed": False,
                "note": f"Only {len(successful)}/{n_runs} runs succeeded",
            })
            continue

        confidences = []
        action_sets = []
        for r in successful:
            diag = r["result"].get("diagnosis") or {}
            conf = diag.get("confidence")
            if isinstance(conf, (int, float)):
                confidences.append(conf)
            actions = r["result"].get("proposed_actions") or []
            action_sets.append(frozenset(a.get("action_type", "") for a in actions))

        # Confidence stability: normalize std dev against tolerance of 0.15
        if len(confidences) >= 2:
            conf_std = statistics.stdev(confidences)
            conf_score = max(0.0, 1.0 - conf_std / 0.15)
        else:
            conf_score = 1.0  # single value — can't measure variance

        # Action agreement: fraction of all pairs with identical action sets
        pairs = list(itertools.combinations(action_sets, 2))
        if pairs:
            action_score = sum(1 for a, b in pairs if a == b) / len(pairs)
        else:
            action_score = 1.0

        consistency_score = conf_score * 0.5 + action_score * 0.5

        results.append({
            "scenario": scenario["id"],
            "n_runs": n_runs,
            "successful_runs": len(successful),
            "confidence_values": confidences,
            "confidence_std": round(statistics.stdev(confidences), 3) if len(confidences) >= 2 else 0.0,
            "action_sets": [list(s) for s in action_sets],
            "conf_score": round(conf_score, 3),
            "action_score": round(action_score, 3),
            "consistency_score": round(consistency_score, 3),
            "passed": consistency_score >= 0.7,
        })

    composite = sum(r["consistency_score"] for r in results) / len(results) if results else 0.0

    return {
        "test": "consistency",
        "n_runs_per_scenario": n_runs,
        "results": results,
        "composite_score": round(composite, 3),
        "passed": composite >= 0.7,
    }


def run_all(save: bool = False, compare: bool = False, consistency: bool = False) -> dict:
    """Run all Level 5 evals."""
    print("\n" + "=" * 60)
    print("LEVEL 5: END-TO-END REGRESSION")
    print("=" * 60)

    results = []
    for scenario in SCENARIOS:
        print(f"\n  Running: {scenario['id']}...")
        r = eval_e2e_scenario(scenario)
        results.append(r)

        if not r["success"]:
            print(f"    ❌ Pipeline failed: {r.get('error')}")
            continue

        status = "✅" if r["score"] >= 0.8 else "⚠️" if r["score"] >= 0.6 else "❌"
        print(f"    {status} Score: {r['score']:.0%} ({r['passed_checks']}/{r['total_checks']} checks)")

        failed_checks = [k for k, v in r["checks"].items() if v is False]
        if failed_checks:
            for fc in failed_checks:
                print(f"       ↳ failed: {fc}")

    composite = sum(r["score"] for r in results) / len(results) if results else 0.0
    passed = composite >= PASS_THRESHOLDS["e2e_composite"]

    print(f"\n  COMPOSITE SCORE:     {composite:.0%}")
    print(f"  STATUS:              {'✅ PASS' if passed else '❌ FAIL'}")

    # Snapshot operations
    snapshot_result = None
    if save:
        save_snapshot(results)
    if compare:
        snapshot_result = compare_snapshot(results)
        if snapshot_result.get("error"):
            print(f"\n  ⚠️ {snapshot_result['error']}")
        else:
            print(f"\n  Snapshot Comparison (vs {snapshot_result['golden_timestamp']}):")
            for c in snapshot_result["comparisons"]:
                if c["status"] == "regression":
                    print(f"    ⚠️ REGRESSION: {c['scenario']}")
                    for diff_name, diff_val in c["diffs"].items():
                        print(f"       {diff_name}: was={diff_val['was']}, now={diff_val['now']}")
                elif c["status"] == "stable":
                    print(f"    ✅ {c['scenario']}: stable")
                else:
                    print(f"    ➖ {c['scenario']}: no baseline")

            if snapshot_result["passed"]:
                print(f"    No regressions detected ✅")
            else:
                print(f"    {snapshot_result['regression_count']} regression(s) found ❌")

    # Optional consistency check (runs each scenario 3x — slow)
    consistency_result = None
    if consistency:
        print(f"\n  Behavioral Consistency (3 runs per scenario):")
        consistency_result = eval_consistency()
        for r in consistency_result["results"]:
            status = "✅" if r["passed"] else "⚠️"
            print(f"    {status} {r['scenario']}: {r['consistency_score']:.0%} "
                  f"(conf_std={r.get('confidence_std', 0):.2f}, action_agree={r.get('action_score', 0):.0%})")
            if not r["passed"] and r.get("note"):
                print(f"       ↳ {r['note']}")
        print(f"  Consistency Composite: {consistency_result['composite_score']:.0%}")

    return {
        "level": 5,
        "name": "End-to-End Regression",
        "results": results,
        "snapshot_comparison": snapshot_result,
        "consistency": consistency_result,
        "composite_score": composite,
        "passed": passed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-snapshot", action="store_true", help="Save current run as golden snapshot")
    parser.add_argument("--compare-snapshot", action="store_true", help="Compare against golden snapshot")
    parser.add_argument("--consistency", action="store_true", help="Run behavioral consistency check (3x per scenario, slow)")
    args = parser.parse_args()
    run_all(save=args.save_snapshot, compare=args.compare_snapshot, consistency=args.consistency)