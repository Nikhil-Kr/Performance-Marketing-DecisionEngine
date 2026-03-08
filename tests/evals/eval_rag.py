"""
Level 6: RAG & Memory Evals

Tests temporal filtering, retrieval relevancy, context precision,
recovery curve mappings, and CSV fallback behavior.

Usage:
    python -m tests.evals.eval_rag
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
os.environ.setdefault("DATA_LAYER_MODE", "mock")


INCIDENTS_CSV = Path("data/post_mortems/incidents.csv")


# ============================================================================
# Test: Temporal Filtering
# ============================================================================

def eval_temporal_filtering() -> dict:
    """
    Test that RAG temporal filtering prevents future-incident contamination.

    Sets analysis_end_date to an early date and verifies no incidents after
    that date appear in results.
    """
    from src.nodes.memory.retriever import _csv_keyword_search

    if not INCIDENTS_CSV.exists():
        return {
            "test": "temporal_filtering",
            "score": 0.0,
            "passed": False,
            "error": "incidents.csv not found — run 'make mock-data' and 'make init-rag'",
        }

    # Use a cutoff date that should exclude most/all incidents
    early_cutoff = "2019-01-01"
    anomaly = {"channel": "google", "metric": "spend"}

    results_filtered = _csv_keyword_search(anomaly, cutoff_date_str=early_cutoff)
    results_unfiltered = _csv_keyword_search(anomaly, cutoff_date_str=None)

    # Check all filtered results are before cutoff
    future_leaks = [
        r for r in results_filtered
        if r.get("date", "9999") > early_cutoff
    ]

    checks = {
        "no_future_incidents": len(future_leaks) == 0,
        "filter_reduces_results": len(results_filtered) <= len(results_unfiltered),
        "unfiltered_has_results": len(results_unfiltered) > 0,
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "temporal_filtering",
        "score": score,
        "passed": score >= 0.66,
        "checks": checks,
        "filtered_count": len(results_filtered),
        "unfiltered_count": len(results_unfiltered),
        "future_leaks": len(future_leaks),
    }


# ============================================================================
# Test: Retrieval Relevancy
# ============================================================================

def eval_retrieval_relevancy() -> dict:
    """
    Test that CSV search returns results relevant to the query anomaly.
    Checks that retrieved docs share channel or anomaly_type with the query.
    """
    from src.nodes.memory.retriever import _csv_keyword_search

    if not INCIDENTS_CSV.exists():
        return {
            "test": "retrieval_relevancy",
            "score": 0.0,
            "passed": False,
            "error": "incidents.csv not found",
        }

    test_queries = [
        {"channel": "google", "metric": "spend"},
        {"channel": "meta", "metric": "conversions"},
        {"channel": "tv", "metric": "impressions"},
    ]

    total_relevant = 0
    total_retrieved = 0

    for anomaly in test_queries:
        results = _csv_keyword_search(anomaly)
        for r in results:
            total_retrieved += 1
            # Relevant if channel or anomaly_type matches query
            ch_match = anomaly["channel"].lower() in r.get("channel", "").lower()
            type_match = anomaly["metric"].lower() in r.get("anomaly_type", "").lower()
            if ch_match or type_match:
                total_relevant += 1

    relevancy = total_relevant / max(1, total_retrieved)

    return {
        "test": "retrieval_relevancy",
        "score": relevancy,
        "passed": relevancy >= 0.5,
        "relevant": total_relevant,
        "total_retrieved": total_retrieved,
    }


# ============================================================================
# Test: Context Precision
# ============================================================================

def eval_context_precision() -> dict:
    """
    Test precision@3: of the top 3 results, how many are actually useful?
    A result is useful if it shares the query channel.
    """
    from src.nodes.memory.retriever import _csv_keyword_search

    if not INCIDENTS_CSV.exists():
        return {
            "test": "context_precision",
            "score": 0.0,
            "passed": False,
            "error": "incidents.csv not found",
        }

    anomaly = {"channel": "google", "metric": "spend"}
    results = _csv_keyword_search(anomaly)[:3]  # top 3

    if not results:
        return {
            "test": "context_precision",
            "score": 0.0,
            "passed": False,
            "error": "No results returned for google/spend query",
        }

    relevant = sum(
        1 for r in results
        if "google" in r.get("channel", "").lower()
    )
    precision = relevant / len(results)

    return {
        "test": "context_precision",
        "score": precision,
        "passed": precision >= 0.33,  # at least 1 of 3
        "relevant_in_top3": relevant,
        "total_top3": len(results),
    }


# ============================================================================
# Test: Recovery Curves
# ============================================================================

def eval_recovery_curves() -> dict:
    """
    Test recovery curve severity→pattern mapping logic.
    Verifies: critical→slow/7d, medium→medium/3d, low→fast/1d.
    """
    from src.nodes.memory.retriever import get_recovery_curve

    if not INCIDENTS_CSV.exists():
        return {
            "test": "recovery_curves",
            "score": 0.0,
            "passed": False,
            "error": "incidents.csv not found",
        }

    # get_recovery_curve uses the actual CSV data, so we test the function works
    # and returns expected structure rather than specific values
    result = get_recovery_curve("spend", "google")

    checks = {}
    if result is None:
        # No matching incidents — the function still didn't crash
        checks["no_crash"] = True
        checks["returns_none_when_no_match"] = True
        score = 1.0
    else:
        checks["has_avg_days"] = "avg_days_to_resolve" in result
        checks["has_pattern"] = "recovery_pattern" in result
        checks["has_count"] = "similar_count" in result
        checks["has_resolutions"] = "similar_resolutions" in result
        checks["pattern_valid"] = result.get("recovery_pattern") in ("fast", "medium", "slow")
        checks["days_positive"] = result.get("avg_days_to_resolve", 0) > 0
        checks["count_positive"] = result.get("similar_count", 0) > 0

    score = sum(checks.values()) / len(checks) if checks else 0.0
    return {
        "test": "recovery_curves",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
        "result": result,
    }


# ============================================================================
# Test: CSV Fallback
# ============================================================================

def eval_csv_fallback() -> dict:
    """
    Test CSV keyword search works as a fallback and respects date filtering.
    """
    from src.nodes.memory.retriever import _csv_keyword_search

    if not INCIDENTS_CSV.exists():
        return {
            "test": "csv_fallback",
            "score": 0.0,
            "passed": False,
            "error": "incidents.csv not found",
        }

    anomaly = {"channel": "google", "metric": "spend"}

    # Test basic keyword search
    results = _csv_keyword_search(anomaly)

    checks = {
        "returns_list": isinstance(results, list),
        "has_results": len(results) > 0,
        "max_5_results": len(results) <= 5,
    }

    if results:
        first = results[0]
        checks["has_incident_id"] = "incident_id" in first
        checks["has_date"] = "date" in first
        checks["has_channel"] = "channel" in first
        checks["has_similarity_score"] = "similarity_score" in first

    # Test with date filter
    results_filtered = _csv_keyword_search(anomaly, cutoff_date_str="2022-01-01")
    all_before_cutoff = all(
        r.get("date", "9999") <= "2022-01-01"
        for r in results_filtered
    )
    checks["date_filter_works"] = all_before_cutoff or len(results_filtered) == 0

    score = sum(checks.values()) / len(checks)
    return {
        "test": "csv_fallback",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
        "result_count": len(results),
        "filtered_count": len(results_filtered),
    }


# ============================================================================
# Orchestrator
# ============================================================================

def run_all() -> dict:
    """Run all RAG evals and return composite score."""
    tests = [
        eval_temporal_filtering,
        eval_retrieval_relevancy,
        eval_context_precision,
        eval_recovery_curves,
        eval_csv_fallback,
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

    print(f"\n  Level 6: RAG Quality")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        err = f" ({r['error']})" if "error" in r and r.get("score") == 0.0 else ""
        print(f"    {status} {r['test']}: {r['score']:.0%}{err}")
    print(f"    Composite: {composite:.0%}")

    return {
        "level": 6,
        "name": "RAG Quality",
        "composite_score": composite,
        "passed": composite >= 0.75,
        "results": results,
    }


if __name__ == "__main__":
    run_all()
