"""
Expedition Eval Suite — Orchestrator

Runs all 5 evaluation levels and produces a combined scorecard.

Usage:
    # Quick mode: structural + deterministic checks only (MockLLM, ~30 seconds)
    python -m tests.evals.run_evals

    # Full mode: includes LLM-as-judge scoring (requires GCP credentials, ~2 minutes)
    python -m tests.evals.run_evals --full

    # Full mode + save snapshot for future regression comparison
    python -m tests.evals.run_evals --full --save-snapshot

    # Compare against saved snapshot
    python -m tests.evals.run_evals --compare-snapshot

Eval Levels:
    1. Router Accuracy       — deterministic channel → investigator mapping
    2. Diagnosis Correctness — structural checks + optional LLM-as-judge
    3. Critic Calibration    — does critic pass good / reject bad diagnoses?
    4. Action Appropriateness— are proposed actions sensible for the scenario?
    5. E2E Regression        — full pipeline smoke test + snapshot comparison
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["DATA_LAYER_MODE"] = "mock"

from tests.evals.eval_config import PASS_THRESHOLDS


def run_evals(
    full: bool = False,
    save_snapshot: bool = False,
    compare_snapshot: bool = False,
    consistency: bool = False,
) -> dict:
    """Run all eval levels and produce scorecard."""

    print("\n" + "=" * 70)
    print("  🧪 EXPEDITION EVAL SUITE")
    print(f"  Mode: {'FULL (with LLM-as-judge)' if full else 'QUICK (structural only)'}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # Level 1: Router
    from tests.evals.eval_router import run_all as run_router
    results["level_1"] = run_router()

    # Level 2: Diagnosis
    from tests.evals.eval_diagnosis import run_all as run_diagnosis
    results["level_2"] = run_diagnosis(use_real_llm=full)

    # Level 3: Critic
    from tests.evals.eval_critic import run_all as run_critic
    results["level_3"] = run_critic()

    # Level 4: Actions
    from tests.evals.eval_actions import run_all as run_actions
    results["level_4"] = run_actions()

    # Level 5: E2E
    from tests.evals.eval_e2e import run_all as run_e2e
    results["level_5"] = run_e2e(save=save_snapshot, compare=compare_snapshot, consistency=consistency)

    # ========================================================================
    # SCORECARD
    # ========================================================================

    print("\n" + "=" * 70)
    print("  📊 SCORECARD")
    print("=" * 70)

    scorecard = []
    for level_key in ["level_1", "level_2", "level_3", "level_4", "level_5"]:
        r = results[level_key]
        level_num = r["level"]
        name = r["name"]
        score = r["composite_score"]
        passed = r["passed"]
        status = "✅ PASS" if passed else "❌ FAIL"

        scorecard.append({
            "level": level_num,
            "name": name,
            "score": score,
            "passed": passed,
        })

        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  Level {level_num}: {name:<25} {bar} {score:>5.0%}  {status}")

    # Overall composite
    weights = {1: 0.10, 2: 0.35, 3: 0.20, 4: 0.15, 5: 0.20}
    overall = sum(
        s["score"] * weights[s["level"]]
        for s in scorecard
    )
    all_passed = all(s["passed"] for s in scorecard)

    print(f"\n  {'─' * 60}")
    bar = "█" * int(overall * 20) + "░" * (20 - int(overall * 20))
    print(f"  OVERALL:                            {bar} {overall:>5.0%}")

    if all_passed:
        print(f"\n  🎉 ALL LEVELS PASSED")
    else:
        failed = [s for s in scorecard if not s["passed"]]
        print(f"\n  ⚠️  {len(failed)} LEVEL(S) FAILED:")
        for f in failed:
            print(f"     - Level {f['level']}: {f['name']} ({f['score']:.0%})")

    # Snapshot comparison summary
    snapshot = results["level_5"].get("snapshot_comparison")
    if snapshot and not snapshot.get("error"):
        reg_count = snapshot.get("regression_count", 0)
        if reg_count > 0:
            print(f"\n  ⚠️  {reg_count} REGRESSION(S) vs golden snapshot")
        else:
            print(f"\n  ✅ No regressions vs golden snapshot")

    print("\n" + "=" * 70)

    # Save full report
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "full" if full else "quick",
        "scorecard": scorecard,
        "overall_score": overall,
        "all_passed": all_passed,
    }

    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"  Report saved: {report_path}")

    return {
        "scorecard": scorecard,
        "overall_score": overall,
        "all_passed": all_passed,
        "levels": results,
        "report_path": str(report_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expedition Eval Suite")
    parser.add_argument(
        "--full", action="store_true",
        help="Run in full mode with LLM-as-judge (requires GCP credentials)"
    )
    parser.add_argument(
        "--save-snapshot", action="store_true",
        help="Save current outputs as golden snapshot for regression comparison"
    )
    parser.add_argument(
        "--compare-snapshot", action="store_true",
        help="Compare against saved golden snapshot"
    )
    parser.add_argument(
        "--consistency", action="store_true",
        help="Run behavioral consistency check (3 runs per scenario, slow)"
    )
    args = parser.parse_args()

    run_evals(
        full=args.full,
        save_snapshot=args.save_snapshot,
        compare_snapshot=args.compare_snapshot,
        consistency=args.consistency,
    )