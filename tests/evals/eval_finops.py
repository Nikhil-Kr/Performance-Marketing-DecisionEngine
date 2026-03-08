"""
Level 10: FinOps & Performance Evals

Tests model tier assignment, LLM parameter configuration,
fallback behavior, and response extraction.

Usage:
    python -m tests.evals.eval_finops
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
os.environ.setdefault("DATA_LAYER_MODE", "mock")


# ============================================================================
# Test: Model Tier Assignment
# ============================================================================

def eval_model_tier_assignment() -> dict:
    """
    Verify that each node uses the correct model tier:
    - Router + Investigators → tier1 (fast/cheap)
    - Explainer + Critic → tier2 (powerful/expensive)
    """
    import ast

    tier_expectations = {
        "src/nodes/router.py": "tier1",
        "src/nodes/investigators/paid_media.py": "tier1",
        "src/nodes/investigators/influencer.py": "tier1",
        "src/nodes/investigators/offline.py": "tier1",
        "src/nodes/explainer/synthesizer.py": "tier2",
        "src/nodes/critic/validator.py": "tier2",
    }

    checks = {}
    for filepath, expected_tier in tier_expectations.items():
        full_path = Path(filepath)
        if not full_path.exists():
            checks[filepath] = False
            continue

        source = full_path.read_text()
        # Look for get_llm_safe("tier1") or get_llm_safe("tier2")
        has_expected = f'get_llm_safe("{expected_tier}")' in source
        checks[filepath] = has_expected

    score = sum(checks.values()) / len(checks) if checks else 0.0
    return {
        "test": "model_tier_assignment",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: Model Tier Parameters
# ============================================================================

def eval_model_tier_parameters() -> dict:
    """
    Verify tier1 and tier2 have correct temperature and max_tokens settings.
    tier1: temperature=0.1, max_tokens=1024
    tier2: temperature=0.3, max_tokens=4096
    """
    from src.intelligence.models import get_llm

    # Read the source to check parameter configuration
    source = Path("src/intelligence/models.py").read_text()

    checks = {
        "tier1_temp_0.1": "temperature=0.1 if tier == \"tier1\"" in source,
        "tier2_temp_0.3": "else 0.3" in source,
        "tier1_max_tokens_1024": "max_tokens=1024 if tier == \"tier1\"" in source,
        "tier2_max_tokens_4096": "else 4096" in source,
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "model_tier_parameters",
        "score": score,
        "passed": score == 1.0,
        "checks": checks,
    }


# ============================================================================
# Test: LLM Fallback to MockLLM
# ============================================================================

def eval_llm_fallback_to_mock() -> dict:
    """
    Verify get_llm_safe() returns a usable LLM and falls back to MockLLM
    when no GCP credentials are available.
    """
    from src.intelligence.models import get_llm_safe, MockLLM

    # Clear LRU cache to get fresh instances
    from src.intelligence.models import get_llm
    get_llm.cache_clear()

    llm_tier1 = get_llm_safe("tier1")
    llm_tier2 = get_llm_safe("tier2")

    checks = {
        "tier1_returns_object": llm_tier1 is not None,
        "tier2_returns_object": llm_tier2 is not None,
        "tier1_has_invoke": hasattr(llm_tier1, "invoke"),
        "tier2_has_invoke": hasattr(llm_tier2, "invoke"),
    }

    # If MockLLM, verify it stores tier info; if real LLM, that's also fine
    if isinstance(llm_tier1, MockLLM):
        checks["tier1_knows_tier"] = llm_tier1.tier == "tier1"
    else:
        checks["tier1_is_real_llm"] = hasattr(llm_tier1, "model_name") or hasattr(llm_tier1, "model")

    if isinstance(llm_tier2, MockLLM):
        checks["tier2_knows_tier"] = llm_tier2.tier == "tier2"
    else:
        checks["tier2_is_real_llm"] = hasattr(llm_tier2, "model_name") or hasattr(llm_tier2, "model")

    # Test explicit fallback: patch credentials away to force MockLLM
    from unittest.mock import patch
    get_llm.cache_clear()
    with patch("src.intelligence.models._has_gcp_credentials", return_value=False):
        mock_t1 = get_llm_safe("tier1")
        checks["forced_fallback_is_mock"] = isinstance(mock_t1, MockLLM)
        if isinstance(mock_t1, MockLLM):
            checks["forced_mock_has_invoke"] = hasattr(mock_t1, "invoke")

    # Clean up LRU cache
    get_llm.cache_clear()

    score = sum(checks.values()) / len(checks)
    return {
        "test": "llm_fallback_to_mock",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Test: Extract Content Formats
# ============================================================================

def eval_extract_content_formats() -> dict:
    """
    Test extract_content() handles both string and list response formats.
    Gemini 3+ returns content as list of blocks; older models return strings.
    """
    from src.intelligence.models import extract_content

    class FakeResponse:
        def __init__(self, content):
            self.content = content

    checks = {}

    # String content
    r1 = FakeResponse("Hello world")
    checks["string_content"] = extract_content(r1) == "Hello world"

    # List content with text blocks
    r2 = FakeResponse([{"type": "text", "text": "Part 1"}, {"type": "text", "text": "Part 2"}])
    result2 = extract_content(r2)
    checks["list_content"] = "Part 1" in result2 and "Part 2" in result2

    # Empty list
    r3 = FakeResponse([])
    checks["empty_list"] = extract_content(r3) == ""

    # Single block list
    r4 = FakeResponse([{"type": "text", "text": "Only block"}])
    checks["single_block"] = "Only block" in extract_content(r4)

    # Mixed block types (non-dict items)
    r5 = FakeResponse(["plain string item"])
    checks["plain_string_item"] = "plain string item" in extract_content(r5)

    score = sum(checks.values()) / len(checks)
    return {
        "test": "extract_content_formats",
        "score": score,
        "passed": score >= 0.80,
        "checks": checks,
    }


# ============================================================================
# Test: MockLLM Response Routing
# ============================================================================

def eval_mock_llm_routing() -> dict:
    """
    Test MockLLM returns contextually appropriate responses based on prompt keywords.
    """
    from src.intelligence.models import MockLLM

    mock = MockLLM("tier1")

    checks = {}

    # Router prompt
    r1 = mock.invoke("Please classify and route this anomaly")
    checks["route_returns_paid_media"] = "PAID_MEDIA" in r1.content

    # Investigation prompt
    r2 = mock.invoke("Investigate this marketing anomaly")
    checks["investigate_returns_findings"] = "Root Cause" in r2.content or "Potential" in r2.content

    # Diagnosis prompt
    r3 = mock.invoke("Synthesize a diagnosis for this anomaly")
    checks["diagnosis_returns_json"] = "root_cause" in r3.content and "confidence" in r3.content

    # Validation prompt
    r4 = mock.invoke("Validate this diagnosis using triple-lock protocol")
    checks["validation_returns_json"] = "is_valid" in r4.content and "hallucination_risk" in r4.content

    # Generic prompt
    r5 = mock.invoke("What is the weather today?")
    checks["generic_returns_mock"] = "Mock" in r5.content

    score = sum(checks.values()) / len(checks)
    return {
        "test": "mock_llm_routing",
        "score": score,
        "passed": score >= 0.80,
        "checks": checks,
    }


# ============================================================================
# Test: Config Model Names
# ============================================================================

def eval_config_model_names() -> dict:
    """
    Verify model configuration has valid Gemini model names.
    """
    from src.utils.config import settings

    checks = {
        "tier1_has_model": bool(settings.gemini_tier1_model),
        "tier2_has_model": bool(settings.gemini_tier2_model),
        "tier1_is_gemini": "gemini" in settings.gemini_tier1_model.lower(),
        "tier2_is_gemini": "gemini" in settings.gemini_tier2_model.lower(),
        "embedding_has_model": bool(settings.embedding_model),
        "tier1_is_fast": any(k in settings.gemini_tier1_model.lower() for k in ["flash", "lite"]),
        "tier2_is_powerful": any(k in settings.gemini_tier2_model.lower() for k in ["pro", "ultra"]),
        "timeout_positive": settings.llm_request_timeout > 0,
    }

    score = sum(checks.values()) / len(checks)
    return {
        "test": "config_model_names",
        "score": score,
        "passed": score >= 0.75,
        "checks": checks,
    }


# ============================================================================
# Orchestrator
# ============================================================================

def run_all() -> dict:
    """Run all FinOps evals and return composite score."""
    tests = [
        eval_model_tier_assignment,
        eval_model_tier_parameters,
        eval_llm_fallback_to_mock,
        eval_extract_content_formats,
        eval_mock_llm_routing,
        eval_config_model_names,
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

    print(f"\n  Level 10: FinOps & Performance")
    for r in results:
        status = "\u2705" if r["passed"] else "\u274c"
        err = f" ({r['error']})" if "error" in r and r.get("score") == 0.0 else ""
        print(f"    {status} {r['test']}: {r['score']:.0%}{err}")
    print(f"    Composite: {composite:.0%}")

    return {
        "level": 10,
        "name": "FinOps & Performance",
        "composite_score": composite,
        "passed": composite >= 0.75,
        "results": results,
    }


if __name__ == "__main__":
    run_all()
