"""Prompts for the Critic node - Triple-Lock Protocol for hallucination prevention."""

CRITIC_SYSTEM_PROMPT = """You are a critical reviewer ensuring diagnoses are accurate and grounded in data.

Your job is to apply the Triple-Lock Protocol:
1. DATA GROUNDING: Every claim must reference specific data points or provided historical context.
2. EVIDENCE VERIFICATION: Conclusions must follow logically from evidence.
3. HALLUCINATION CHECK: Flag any claims that go beyond the provided data.

IMPORTANT: Distinguish between "Hallucination" and "Reasonable Inference".
- HALLUCINATION: Inventing data that doesn't exist (e.g., citing a specific "Change Log ID #123" that isn't in the evidence).
- INFERENCE: Deducing a likely cause based on patterns (e.g., "Spend tripled, which implies a budget increase or targeting expansion").
- Inferences are VALID if they are logical and consistent with the data.

Rate hallucination risk from 0.0 (fully grounded) to 1.0 (completely fabricated)."""


CRITIC_VALIDATION_PROMPT = """Validate this diagnosis against the original data:

## Original Anomaly Data
- Channel: {channel}
- Metric: {metric}
- Current Value: {current_value}
- Expected Value: {expected_value}
- Deviation: {deviation_pct}%

## Raw Evidence Available
(Note: This includes current metrics and retrieved historical context)
{raw_evidence}

## Diagnosis to Validate
Root Cause: {root_cause}
Confidence: {confidence}

Supporting Evidence:
{supporting_evidence}

Recommended Actions:
{recommended_actions}

## Your Task (Triple-Lock Protocol)

### Lock 1: Data Grounding
- Does every claim reference specific data from the raw evidence?
- Note: Historical Context provided in the evidence IS valid data for grounding.

### Lock 2: Evidence Verification  
- Do the conclusions logically follow from the evidence?
- Are logical inferences (like "spend spike -> likely budget change") reasonable?

### Lock 3: Hallucination Check
- Are there any fabricated statistics or made-up details?
- Does the diagnosis claim to know things not in the data?

Respond in this exact JSON format:
{{
    "is_valid": true,
    "hallucination_risk": 0.15,
    "data_grounded": true,
    "evidence_verified": true,
    "issues": [
        "Issue 1 if any",
        "Issue 2 if any"
    ],
    "recommendations": "Specific recommendations to improve the diagnosis if needed"
}}"""


PROPOSER_VALIDATION_PROMPT = """Validate that this proposed action matches the diagnosis:

## Diagnosis
Root Cause: {root_cause}

## Proposed Action
- Type: {action_type}
- Platform: {platform}
- Operation: {operation}
- Parameters: {parameters}
- Estimated Impact: {estimated_impact}

## Validation Questions
1. Does this action address the identified root cause?
2. Is the action proportional to the severity?
3. Are there risks not mentioned?

Respond in JSON:
{{
    "action_valid": true,
    "matches_diagnosis": true,
    "risk_assessment": "low",
    "concerns": []
}}"""


def format_critic_prompt(
    anomaly: dict,
    raw_evidence: str,
    diagnosis: dict,
) -> str:
    """Format the critic validation prompt."""
    
    # Format supporting evidence
    evidence_list = diagnosis.get("supporting_evidence", [])
    evidence_str = "\n".join([f"- {e}" for e in evidence_list])
    
    # Format recommended actions
    actions_list = diagnosis.get("recommended_actions", [])
    actions_str = "\n".join([f"- {a}" for a in actions_list])
    
    return CRITIC_VALIDATION_PROMPT.format(
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        current_value=anomaly.get("current_value", "N/A"),
        expected_value=anomaly.get("expected_value", "N/A"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        raw_evidence=raw_evidence,
        root_cause=diagnosis.get("root_cause", "Not provided"),
        confidence=diagnosis.get("confidence", "N/A"),
        supporting_evidence=evidence_str,
        recommended_actions=actions_str,
    )


def parse_critic_response(response: str) -> dict:
    """Parse the JSON response from the critic."""
    import json
    import re
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            # Ensure required fields
            return {
                "is_valid": result.get("is_valid", False),
                "hallucination_risk": result.get("hallucination_risk", 0.5),
                "data_grounded": result.get("data_grounded", False),
                "evidence_verified": result.get("evidence_verified", False),
                "issues": result.get("issues", []),
                "recommendations": result.get("recommendations", ""),
            }
    except json.JSONDecodeError:
        pass
    
    # Conservative fallback
    return {
        "is_valid": False,
        "hallucination_risk": 0.7,
        "data_grounded": False,
        "evidence_verified": False,
        "issues": ["Failed to parse critic response"],
        "recommendations": "Manual review required",
    }