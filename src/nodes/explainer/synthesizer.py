"""Explainer Node - Synthesizes diagnosis with multi-persona explanations."""
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.explainer import (
    EXPLAINER_SYSTEM_PROMPT,
    format_explainer_prompt,
    parse_diagnosis_response,
)


def generate_explanation(state: ExpeditionState) -> dict:
    """
    Explainer Node.
    
    Synthesizes investigation findings and historical context
    into a complete diagnosis with multi-persona explanations.
    
    Per architecture:
    - Uses Tier 2 (Pro) model for complex reasoning
    - Generates explanations for: Executive, Director, Marketer, Data Scientist
    - Outputs structured diagnosis with confidence scores
    """
    print("\n📝 Generating Diagnosis (Explainer)...")
    
    anomaly = state.get("selected_anomaly")
    investigation_summary = state.get("investigation_summary", "")
    historical_incidents = state.get("historical_incidents", [])
    
    if not anomaly:
        return {
            "diagnosis": None,
            "current_node": "explainer",
            "error": "No anomaly to explain",
        }
    
    # Generate diagnosis using Tier 2 (Pro) model
    try:
        llm = get_llm_safe("tier2")
        
        prompt = format_explainer_prompt(
            anomaly=anomaly,
            investigation_summary=investigation_summary,
            historical_incidents=historical_incidents,
        )
        
        messages = [
            {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        
        # Parse the JSON response
        diagnosis = parse_diagnosis_response(response.content)
        
        print(f"  ✅ Diagnosis generated (confidence: {diagnosis.get('confidence', 'N/A')})")
        print(f"  📋 Root cause: {diagnosis.get('root_cause', 'Unknown')[:100]}...")
        
    except Exception as e:
        print(f"  ⚠️ Diagnosis generation failed: {e}")
        diagnosis = _create_fallback_diagnosis(anomaly, investigation_summary)
    
    return {
        "diagnosis": diagnosis,
        "current_node": "explainer",
    }


def _create_fallback_diagnosis(anomaly: dict, investigation_summary: str) -> dict:
    """Create a basic diagnosis when LLM fails."""
    return {
        "root_cause": f"Anomaly detected in {anomaly.get('channel', 'unknown')}: {anomaly.get('metric', 'unknown')} {anomaly.get('direction', 'changed')}",
        "confidence": 0.3,
        "supporting_evidence": [
            f"Metric deviated by {anomaly.get('deviation_pct', 'N/A')}%",
            "Automated analysis unavailable - manual review required",
        ],
        "recommended_actions": [
            "Review channel performance manually",
            "Check for recent platform changes",
            "Verify tracking implementation",
        ],
        "executive_summary": f"A {anomaly.get('severity', 'unknown')} severity anomaly was detected in {anomaly.get('channel', 'unknown')}. Manual investigation recommended.",
        "director_summary": "Automated analysis encountered an error. Please assign an analyst to investigate manually.",
        "marketer_summary": f"Check {anomaly.get('channel', 'the channel')} for unusual activity. Review campaign settings and recent changes.",
        "technical_details": f"Investigation summary: {investigation_summary[:500] if investigation_summary else 'Not available'}",
    }
