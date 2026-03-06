"""
Level 1: Router Accuracy Eval

Tests whether route_to_investigator() correctly classifies every known
channel to the right investigator (paid_media / influencer / offline).

This should be 100%. If it's not, it's a code bug, not an LLM issue,
because routing uses rule-based lookup first and only falls back to
LLM for unknown channels.

Usage:
    python -m tests.evals.eval_router
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["DATA_LAYER_MODE"] = "mock"

from tests.evals.eval_config import ROUTING_TRUTH
from src.nodes.router import (
    PAID_MEDIA_CHANNELS,
    INFLUENCER_CHANNELS,
    OFFLINE_CHANNELS,
    route_to_investigator,
)


def eval_rule_based_routing() -> dict:
    """
    Test 1: Verify the hardcoded channel sets match ground truth.
    This doesn't even call the function — just checks the constants.
    """
    results = []

    for channel, expected in ROUTING_TRUTH.items():
        if expected == "paid_media":
            actual_in_set = channel in PAID_MEDIA_CHANNELS
        elif expected == "influencer":
            actual_in_set = channel in INFLUENCER_CHANNELS
        elif expected == "offline":
            actual_in_set = channel in OFFLINE_CHANNELS
        else:
            actual_in_set = False

        passed = actual_in_set
        results.append({
            "channel": channel,
            "expected": expected,
            "in_correct_set": actual_in_set,
            "passed": passed,
        })

    return {
        "test": "rule_based_routing",
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": [r for r in results if not r["passed"]],
        "score": sum(1 for r in results if r["passed"]) / len(results),
    }


def eval_function_routing() -> dict:
    """
    Test 2: Actually call route_to_investigator() with a mock state
    for each channel and verify it returns the correct category.
    """
    results = []

    for channel, expected in ROUTING_TRUTH.items():
        # Build a minimal state with just the anomaly
        state = {
            "messages": [],
            "selected_anomaly": {
                "channel": channel,
                "metric": "cpa",
                "direction": "spike",
                "severity": "high",
            },
            "channel_category": None,
            "current_node": "router",
        }

        try:
            result = route_to_investigator(state)
            actual = result.get("channel_category")
            passed = actual == expected
        except Exception as e:
            actual = f"ERROR: {e}"
            passed = False

        results.append({
            "channel": channel,
            "expected": expected,
            "actual": actual,
            "passed": passed,
        })

    return {
        "test": "function_routing",
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": [r for r in results if not r["passed"]],
        "score": sum(1 for r in results if r["passed"]) / len(results),
    }


def eval_unknown_channel_fallback() -> dict:
    """
    Test 3: Feed in channels NOT in any known set.
    The router should fall back to LLM classification.
    We just check it doesn't crash and returns a valid category.
    """
    unknown_channels = [
        "snapchat_ads",
        "reddit_ads",
        "pinterest",
        "amazon_dsp",
        "twitch_sponsorship",
    ]
    results = []

    for channel in unknown_channels:
        state = {
            "messages": [],
            "selected_anomaly": {
                "channel": channel,
                "metric": "cpa",
                "direction": "spike",
                "severity": "medium",
            },
            "channel_category": None,
            "current_node": "router",
        }

        try:
            result = route_to_investigator(state)
            actual = result.get("channel_category")
            valid = actual in ("paid_media", "influencer", "offline")
            error = None
        except Exception as e:
            actual = None
            valid = False
            error = str(e)

        results.append({
            "channel": channel,
            "returned": actual,
            "valid_category": valid,
            "error": error,
        })

    return {
        "test": "unknown_channel_fallback",
        "total": len(results),
        "valid": sum(1 for r in results if r["valid_category"]),
        "errors": [r for r in results if r["error"]],
        "score": sum(1 for r in results if r["valid_category"]) / len(results),
    }


def run_all() -> dict:
    """Run all Level 1 evals and return composite results."""
    print("\n" + "=" * 60)
    print("LEVEL 1: ROUTER ACCURACY")
    print("=" * 60)

    r1 = eval_rule_based_routing()
    print(f"\n  Rule-Based Sets:     {r1['passed']}/{r1['total']} ({r1['score']:.0%})")
    if r1["failed"]:
        for f in r1["failed"]:
            print(f"    ❌ {f['channel']} → expected {f['expected']}, not in set")

    r2 = eval_function_routing()
    print(f"  Function Routing:    {r2['passed']}/{r2['total']} ({r2['score']:.0%})")
    if r2["failed"]:
        for f in r2["failed"]:
            print(f"    ❌ {f['channel']} → expected {f['expected']}, got {f['actual']}")

    r3 = eval_unknown_channel_fallback()
    print(f"  Unknown Fallback:    {r3['valid']}/{r3['total']} ({r3['score']:.0%})")
    if r3["errors"]:
        for e in r3["errors"]:
            print(f"    ❌ {e['channel']} → {e['error']}")

    composite = (r1["score"] + r2["score"] + r3["score"]) / 3

    print(f"\n  COMPOSITE SCORE:     {composite:.0%}")
    print(f"  STATUS:              {'✅ PASS' if composite >= 0.95 else '❌ FAIL'}")

    return {
        "level": 1,
        "name": "Router Accuracy",
        "rule_based": r1,
        "function": r2,
        "fallback": r3,
        "composite_score": composite,
        "passed": composite >= 0.95,
    }


if __name__ == "__main__":
    run_all()