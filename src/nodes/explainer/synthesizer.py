# """Explainer Node - Synthesizes diagnosis with multi-persona explanations."""
# from src.schemas.state import ExpeditionState
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.explainer import (
#     EXPLAINER_SYSTEM_PROMPT,
#     format_explainer_prompt,
#     parse_diagnosis_response,
# )


# def generate_explanation(state: ExpeditionState) -> dict:
#     """
#     Explainer Node.
    
#     Synthesizes investigation findings and historical context
#     into a complete diagnosis with multi-persona explanations.
    
#     Per architecture:
#     - Uses Tier 2 (Pro) model for complex reasoning
#     - Generates explanations for: Executive, Director, Marketer, Data Scientist
#     - Outputs structured diagnosis with confidence scores
#     """
#     print("\n📝 Generating Diagnosis (Explainer)...")
    
#     anomaly = state.get("selected_anomaly")
#     investigation_summary = state.get("investigation_summary", "")
#     historical_incidents = state.get("historical_incidents", [])
    
#     if not anomaly:
#         return {
#             "diagnosis": None,
#             "current_node": "explainer",
#             "error": "No anomaly to explain",
#         }
    
#     # Generate diagnosis using Tier 2 (Pro) model
#     try:
#         llm = get_llm_safe("tier2")
        
#         prompt = format_explainer_prompt(
#             anomaly=anomaly,
#             investigation_summary=investigation_summary,
#             historical_incidents=historical_incidents,
#         )
        
#         messages = [
#             {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ]
        
#         response = llm.invoke(messages)
        
#         # Parse the JSON response
#         diagnosis = parse_diagnosis_response(response.content)
        
#         print(f"  ✅ Diagnosis generated (confidence: {diagnosis.get('confidence', 'N/A')})")
#         print(f"  📋 Root cause: {diagnosis.get('root_cause', 'Unknown')[:100]}...")
        
#     except Exception as e:
#         print(f"  ⚠️ Diagnosis generation failed: {e}")
#         diagnosis = _create_fallback_diagnosis(anomaly, investigation_summary)
    
#     return {
#         "diagnosis": diagnosis,
#         "current_node": "explainer",
#     }


# def _create_fallback_diagnosis(anomaly: dict, investigation_summary: str) -> dict:
#     """Create a basic diagnosis when LLM fails."""
#     return {
#         "root_cause": f"Anomaly detected in {anomaly.get('channel', 'unknown')}: {anomaly.get('metric', 'unknown')} {anomaly.get('direction', 'changed')}",
#         "confidence": 0.3,
#         "supporting_evidence": [
#             f"Metric deviated by {anomaly.get('deviation_pct', 'N/A')}%",
#             "Automated analysis unavailable - manual review required",
#         ],
#         "recommended_actions": [
#             "Review channel performance manually",
#             "Check for recent platform changes",
#             "Verify tracking implementation",
#         ],
#         "executive_summary": f"A {anomaly.get('severity', 'unknown')} severity anomaly was detected in {anomaly.get('channel', 'unknown')}. Manual investigation recommended.",
#         "director_summary": "Automated analysis encountered an error. Please assign an analyst to investigate manually.",
#         "marketer_summary": f"Check {anomaly.get('channel', 'the channel')} for unusual activity. Review campaign settings and recent changes.",
#         "technical_details": f"Investigation summary: {investigation_summary[:500] if investigation_summary else 'Not available'}",
#     }

# src/nodes/explainer/synthesizer.py

from src.schemas.state import ExpeditionState
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.explainer import (
    EXPLAINER_SYSTEM_PROMPT,
    format_explainer_prompt,
    parse_diagnosis_response,
)

ROOT_CAUSE_ACTION_MAP = {
    "auction_pressure": [
        "bid_increase",
        "budget_reallocation",
        "brand_defense",
    ],
    "audience_saturation": [
        "budget_decrease",
        "audience_refresh",
    ],
    "creative_fatigue": [
        "creative_refresh",
    ],
    "tracking_break": [
        "fix_tracking",
        "pause_spend",
    ],
    "landing_page_issue": [
        "landing_page_fix",
    ],
    "seasonality": [
        "budget_reallocation",
    ],
    "platform_change": [
        "monitor_only",
    ],
    # ✅ NEW: localized, non-structural issue
    "localized_campaign_issue": [
        "continue_investment",
        "manual_review",
    ],
    "unknown": [
        "manual_review",
    ],
}

def infer_root_cause_category(root_cause: str) -> str:
    text = (root_cause or "").lower()

    # --- STRATEGIC / LOCALIZED CASE ---
    if any(k in text for k in [
        "isolated",
        "single campaign",
        "largest campaign",
        "localized",
        "short-term dip",
    ]) and any(k in text for k in [
        "channel value",
        "high value",
        "strategic",
        "room to grow",
        "marginal roas",
        "mta",
    ]):
        return "localized_campaign_issue"

    if any(k in text for k in ["auction", "competitor", "bidding"]):
        return "auction_pressure"
    if any(k in text for k in ["frequency", "saturation", "fatigue"]):
        return "audience_saturation"
    if "creative" in text:
        return "creative_fatigue"
    if any(k in text for k in ["tracking", "pixel", "attribution"]):
        return "tracking_break"
    if any(k in text for k in ["landing", "checkout", "site"]):
        return "landing_page_issue"
    if "season" in text:
        return "seasonality"
    if any(k in text for k in ["policy", "platform", "algorithm"]):
        return "platform_change"

    return "unknown"

def generate_explanation(state: ExpeditionState) -> dict:
    print("\n📝 Generating Diagnosis (Explainer)")

    anomaly = state.get("selected_anomaly")
    investigation_summary = state.get("investigation_summary", "")
    historical_incidents = state.get("historical_incidents", [])

    if not anomaly:
        return {
            "diagnosis": None,
            "current_node": "explainer",
        }

    llm = get_llm_safe("tier2")

    response = llm.invoke([
        {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
        {"role": "user", "content": format_explainer_prompt(
            anomaly=anomaly,
            investigation_summary=investigation_summary,
            historical_incidents=historical_incidents,
        )},
    ])

    diagnosis = parse_diagnosis_response(response.content)

    root_category = infer_root_cause_category(diagnosis.get("root_cause"))

    diagnosis["root_cause_category"] = root_category
    diagnosis["allowed_action_keys"] = ROOT_CAUSE_ACTION_MAP[root_category]

    print(f"  🎯 Root cause category: {root_category}")
    print(f"  🔑 Allowed actions: {diagnosis['allowed_action_keys']}")

    return {
        "diagnosis": diagnosis,
        "current_node": "explainer",
    }

