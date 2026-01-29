"""Prompts for the Explainer node - generates multi-persona diagnoses."""

EXPLAINER_SYSTEM_PROMPT = """You are a senior decision scientist who synthesizes analysis into clear, actionable diagnoses.

You create explanations tailored to different audiences:
1. EXECUTIVE: C-suite level - business impact, strategic implications, one-paragraph summary
2. DIRECTOR: Marketing leadership - tactical recommendations, resource implications
3. MARKETER: Channel managers - specific actions, platform details
4. DATA_SCIENTIST: Technical team - methodology, statistical details, data quality notes

TRIPLE-LOCK COMPLIANCE RULES:
- DATA GROUNDING: Cite specific metrics and numbers from the findings.
- INFERENCE CLARITY: Distinguish between observed facts and logical inferences. 
  - Bad: "The budget was increased." (If no changelog exists)
  - Good: "The 300% spend spike suggests a likely budget increase."
- UNCERTAINTY: Use probability language (likely, probable, potential) when root causes are not 100% proven by data.

Your diagnoses must be grounded, actionable, and calibrated."""


EXPLAINER_SYNTHESIS_PROMPT = """Synthesize the following investigation into a diagnosis:

## Anomaly Summary
- Channel: {channel}
- Metric: {metric}  
- Severity: {severity}
- Direction: {direction} of {deviation_pct}%

## Investigation Findings
{investigation_summary}

## Historical Context (Similar Past Incidents)
{historical_context}

## Your Task
Generate a complete diagnosis with explanations for all four personas.

Respond in this exact JSON format:
{{
    "root_cause": "Primary root cause in one sentence (use 'suggests' or 'likely' if inferred)",
    "confidence": 0.85,
    "supporting_evidence": [
        "Evidence point 1 (cite specific numbers)",
        "Evidence point 2",
        "Evidence point 3"
    ],
    "recommended_actions": [
        "Action 1",
        "Action 2",
        "Action 3"
    ],
    "executive_summary": "One paragraph for C-suite: business impact, strategic implication, recommended decision",
    "director_summary": "Two paragraphs for marketing leadership: tactical situation, resource needs, timeline",
    "marketer_summary": "Detailed section for channel managers: specific platform actions, settings to change, campaigns to adjust",
    "technical_details": "For data scientists: methodology notes, data quality issues, statistical caveats"
}}"""


HISTORICAL_CONTEXT_TEMPLATE = """### Similar Incident: {incident_id} ({date})
- Channel: {channel}
- Anomaly: {anomaly_type}
- Root Cause: {root_cause}
- Resolution: {resolution}
- Similarity Score: {similarity_score:.2f}
"""


def format_explainer_prompt(
    anomaly: dict,
    investigation_summary: str,
    historical_incidents: list[dict],
) -> str:
    """Format the explainer synthesis prompt."""
    
    # Format historical context
    if historical_incidents:
        historical_context = "\n".join([
            HISTORICAL_CONTEXT_TEMPLATE.format(**incident)
            for incident in historical_incidents
        ])
    else:
        historical_context = "No similar past incidents found."
    
    return EXPLAINER_SYNTHESIS_PROMPT.format(
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        severity=anomaly.get("severity", "unknown"),
        direction=anomaly.get("direction", "unknown"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        investigation_summary=investigation_summary,
        historical_context=historical_context,
    )


def parse_diagnosis_response(response: str) -> dict:
    """Parse the JSON response from the explainer."""
    import json
    import re
    
    # Try to extract JSON from response
    try:
        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    # Fallback: return structured error
    return {
        "root_cause": "Unable to parse diagnosis",
        "confidence": 0.0,
        "supporting_evidence": ["Parser error - raw response available"],
        "recommended_actions": ["Review raw analysis manually"],
        "executive_summary": response[:500],
        "director_summary": "",
        "marketer_summary": "",
        "technical_details": f"Parse error. Raw response: {response}",
    }