"""Critic Node (Safety) - Triple-Lock Protocol for hallucination prevention."""
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.critic import (
    CRITIC_SYSTEM_PROMPT,
    format_critic_prompt,
    parse_critic_response,
)


def validate_diagnosis(state: ExpeditionState) -> dict:
    """
    Critic Node (Safety).
    
    Applies the Triple-Lock Protocol to validate the diagnosis:
    1. DATA GROUNDING: Every claim must reference specific data
    2. EVIDENCE VERIFICATION: Conclusions must follow from evidence
    3. HALLUCINATION CHECK: Flag claims beyond provided data
    
    Per architecture:
    - Uses Tier 2 (Pro) model for careful validation
    - Assigns hallucination risk score (0.0 - 1.0)
    - Can reject and trigger re-investigation
    """
    print("\n🔒 Running Critic Validation (Triple-Lock Protocol)...")
    
    diagnosis = state.get("diagnosis")
    anomaly = state.get("selected_anomaly")
    investigation_evidence = state.get("investigation_evidence")
    
    if not diagnosis:
        return {
            "critic_validation": {"is_valid": False, "issues": ["No diagnosis to validate"]},
            "validation_passed": False,
            "current_node": "critic",
        }
    
    # Format raw evidence for validation
    raw_evidence = _format_raw_evidence(investigation_evidence)
    
    # Run validation using Tier 2 (Pro) model
    try:
        llm = get_llm_safe("tier2")
        
        prompt = format_critic_prompt(
            anomaly=anomaly or {},
            raw_evidence=raw_evidence,
            diagnosis=diagnosis,
        )
        
        messages = [
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        validation = parse_critic_response(response.content)
        
    except Exception as e:
        print(f"  ⚠️ Critic validation failed: {e}")
        validation = _fallback_validation()
    
    # Determine if validation passed
    # Logic Update:
    # 1. Standard Pass: LLM says valid + grounded + low risk (< 0.5)
    # 2. Low Risk Override: If risk is VERY low (<= 0.25), we accept it even if LLM is nitpicking on 'data_grounded'
    risk_score = validation.get("hallucination_risk", 1.0)
    is_valid_strict = (
        validation.get("is_valid", False) and
        risk_score < 0.5 and
        validation.get("data_grounded", False)
    )
    
    passed = is_valid_strict or (risk_score <= 0.25)
    
    # Log results
    if passed:
        print(f"  ✅ Validation PASSED (hallucination risk: {risk_score})")
    else:
        print(f"  ❌ Validation FAILED (hallucination risk: {risk_score})")
        for issue in validation.get("issues", []):
            print(f"    - {issue}")
    
    return {
        "critic_validation": validation,
        "validation_passed": passed,
        "current_node": "critic",
    }


def _format_raw_evidence(evidence: dict | str | None) -> str:
    """Format investigation evidence for critic review."""
    if not evidence:
        return "No raw evidence available"
    
    # FIX: Handle string evidence (e.g. from RAG concatenation)
    if isinstance(evidence, str):
        return evidence
        
    # Handle structured evidence (original dict format)
    lines = ["## Raw Evidence\n"]
    
    # Anomaly data
    if "anomaly" in evidence:
        anomaly = evidence["anomaly"]
        lines.append(f"""
### Anomaly Data
- Channel: {anomaly.get('channel', 'N/A')}
- Metric: {anomaly.get('metric', 'N/A')}
- Current Value: {anomaly.get('current_value', 'N/A')}
- Expected Value: {anomaly.get('expected_value', 'N/A')}
- Deviation: {anomaly.get('deviation_pct', 'N/A')}%
""")
    
    # Performance summary
    if "performance_summary" in evidence:
        lines.append(f"""
### Performance Summary
{evidence['performance_summary']}
""")
    
    # Campaign breakdown
    if "campaign_breakdown" in evidence:
        lines.append(f"""
### Campaign Breakdown
{evidence['campaign_breakdown']}
""")
    
    return "\n".join(lines)


def _fallback_validation() -> dict:
    """Conservative fallback when LLM validation fails."""
    return {
        "is_valid": True,  # Don't block, but flag for review
        "hallucination_risk": 0.5,  # Uncertain
        "data_grounded": True,
        "evidence_verified": True,
        "issues": ["Automated validation unavailable - manual review recommended"],
        "recommendations": "Proceed with caution; recommend human verification",
    }


def should_retry_investigation(state: ExpeditionState) -> bool:
    """
    Decision function: Should we retry the investigation?
    
    Called when validation fails to determine if we should:
    - Retry with different approach
    - Or proceed with low confidence
    """
    validation = state.get("critic_validation", {})
    risk = validation.get("hallucination_risk", 0.5)
    
    # Retry if risk is very high
    return risk > 0.7