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

HISTORICAL CONTEXT RULES:
- You may ONLY reference incident IDs (e.g., INC-2026-xxx) that appear verbatim in the "Historical Context" section below.
- NEVER invent, fabricate, or guess incident IDs. If no historical incidents are provided, say "No directly comparable historical incidents were found" instead of making them up.
- When citing a past incident, quote the exact incident ID and root cause from the provided context.
- Do NOT claim similarity scores, patterns, or recurring trends from historical data unless those exact numbers appear in the provided context.

Your diagnoses must be grounded, actionable, and calibrated."""


EXPLAINER_SYNTHESIS_PROMPT = """Synthesize the following investigation into a diagnosis:

## Anomaly Summary
- **Analysis Period:** {analysis_start} to {analysis_end}
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

CRITICAL REMINDERS:
- Only reference incident IDs that appear EXACTLY in the Historical Context above.
- If the Historical Context says "No similar past incidents found", do NOT invent any.
- Ground every claim in specific numbers from the Investigation Findings.
- Use "likely", "suggests", or "probable" for inferred causes.

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


# ============================================================================
# Retry Prompt (Critic Feedback Loop)
# ============================================================================

EXPLAINER_RETRY_PROMPT = """Your previous diagnosis was rejected by the validation system. Please revise it.

## Anomaly Summary
- **Analysis Period:** {analysis_start} to {analysis_end}
- Channel: {channel}
- Metric: {metric}
- Severity: {severity}
- Direction: {direction} of {deviation_pct}%

## Investigation Findings
{investigation_summary}

## Historical Context (Similar Past Incidents)
{historical_context}

## Your Previous Diagnosis
Root Cause: {previous_root_cause}
Confidence: {previous_confidence}
Evidence: {previous_evidence}

## Critic Feedback (MUST ADDRESS THESE ISSUES)
{critic_feedback}

## Your Task
Revise the diagnosis to address the critic's concerns. Specifically:
1. Remove or qualify any claims flagged as unsupported
2. Add data citations for evidence points
3. Lower confidence if root cause is uncertain
4. Ensure EVERY claim references specific data from the investigation findings
5. NEVER invent incident IDs — only reference incidents from the Historical Context above

Respond in the same JSON format as before:
{{
    "root_cause": "Revised root cause (address critic feedback)",
    "confidence": 0.XX,
    "supporting_evidence": ["Revised evidence with specific data citations"],
    "recommended_actions": ["Revised actions"],
    "executive_summary": "Revised executive summary",
    "director_summary": "Revised director summary",
    "marketer_summary": "Revised marketer summary",
    "technical_details": "Revised technical details including critic response notes"
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
    analysis_start: str = "N/A",
    analysis_end: str = "N/A",
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
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        severity=anomaly.get("severity", "unknown"),
        direction=anomaly.get("direction", "unknown"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        investigation_summary=investigation_summary,
        historical_context=historical_context,
    )


def format_retry_prompt(
    anomaly: dict,
    investigation_summary: str,
    historical_incidents: list[dict],
    previous_diagnosis: dict,
    critic_feedback: str,
    analysis_start: str = "N/A",
    analysis_end: str = "N/A",
) -> str:
    """
    Format the retry prompt with previous diagnosis + critic feedback.
    Enables the critic→explainer feedback loop.
    """
    # Format historical context
    if historical_incidents:
        historical_context = "\n".join([
            HISTORICAL_CONTEXT_TEMPLATE.format(**incident)
            for incident in historical_incidents
        ])
    else:
        historical_context = "No similar past incidents found."
    
    # Format previous evidence
    prev_evidence = "\n".join([
        f"- {e}" for e in previous_diagnosis.get("supporting_evidence", [])
    ])
    
    return EXPLAINER_RETRY_PROMPT.format(
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        severity=anomaly.get("severity", "unknown"),
        direction=anomaly.get("direction", "unknown"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        investigation_summary=investigation_summary,
        historical_context=historical_context,
        previous_root_cause=previous_diagnosis.get("root_cause", "N/A"),
        previous_confidence=previous_diagnosis.get("confidence", "N/A"),
        previous_evidence=prev_evidence,
        critic_feedback=critic_feedback,
    )


def parse_diagnosis_response(response) -> dict:
    """Parse the JSON response from the explainer."""
    import json
    import re
    from src.utils.logging import get_logger
    logger = get_logger("explainer.parser")

    # Gemini 3 returns content as a list of parts; normalize to string
    if isinstance(response, list):
        response = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in response
        )

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    stripped = re.sub(r'^```(?:json)?\s*\n?', '', response.strip())
    stripped = re.sub(r'\n?```\s*$', '', stripped)

    # Attempt 1: Parse the stripped response directly
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 2: Extract JSON object with greedy regex
    try:
        json_match = re.search(r'\{[\s\S]*\}', stripped)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 3: Try fixing common LLM JSON issues (trailing commas, single quotes)
    try:
        cleaned = re.sub(r',\s*([}\]])', r'\1', stripped)  # trailing commas
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, ValueError):
        pass

    logger.error("Failed to parse diagnosis JSON. Response preview: %s", response[:500])

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
