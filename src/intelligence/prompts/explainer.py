"""Prompts for the Explainer node - generates multi-persona diagnoses with structured actions."""

# Action catalog that the LLM can choose from
ACTION_CATALOG = """
## Available Action Templates

You MUST select actions from this catalog. Use the exact template_id.

### Budget Actions
- `budget_increase`: Increase campaign budget (use when: spend exhausted, missing opportunity, need more volume)
- `budget_decrease`: Decrease campaign budget (use when: wasteful spend, poor efficiency, CPA too high)

### Bid Actions  
- `bid_increase`: Increase bids/targets (use when: losing impression share, need more reach, competitors outbidding)
- `bid_decrease`: Decrease bids/targets (use when: CPC/CPA too high, need better efficiency)

### Campaign Control
- `pause_campaign`: Pause campaign temporarily (use when: severe issues, need to stop bleeding, fraud detected)
- `enable_campaign`: Re-enable paused campaign (use when: issue resolved, ready to resume)

### Team Notifications
- `creative_fatigue`: Alert creative team (use when: ad fatigue, declining CTR, stale creative)
- `tracking_issue`: Alert engineering team (use when: pixel issues, attribution problems, tracking gaps)
- `platform_issue`: Alert ops team (use when: platform bugs, algorithm changes, external issues)
- `manual_review`: Request analyst review (use when: unclear situation, need deeper investigation)

### Fraud & Compliance
- `bot_traffic`: Block fraudulent traffic (use when: invalid clicks, bot patterns detected)
- `influencer_fraud`: Address influencer fraud (use when: fake engagement, contract violation)

### Offline Media
- `make_good`: Request make-good from vendor (use when: under-delivery, preemptions, missed spots)
- `partner_issue`: Contact partner/vendor (use when: tracking issues, delivery problems)
- `vendor_delivery`: Follow up on vendor delivery (use when: inventory issues, flight problems)
- `measurement_audit`: Request measurement audit (use when: data discrepancies, model concerns)
"""

EXPLAINER_SYSTEM_PROMPT = """You are a senior decision scientist who synthesizes analysis into clear, actionable diagnoses.

You create explanations tailored to different audiences:
1. EXECUTIVE: C-suite level - business impact, strategic implications, one-paragraph summary
2. DIRECTOR: Marketing leadership - tactical recommendations, resource implications
3. MARKETER: Channel managers - specific actions, platform details
4. DATA_SCIENTIST: Technical team - methodology, statistical details, data quality notes

CRITICAL RULES:
1. Your recommended actions in the JSON MUST use template_ids from the action catalog
2. The actions must MATCH your diagnosis - if you say "reduce spend", use "budget_decrease" not "budget_increase"
3. Be specific about WHY each action is recommended

TRIPLE-LOCK COMPLIANCE RULES:
- DATA GROUNDING: Cite specific metrics and numbers from the findings.
- INFERENCE CLARITY: Distinguish between observed facts and logical inferences. 
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

{action_catalog}

## Your Task
Generate a complete diagnosis. You MUST select appropriate actions from the catalog above.

IMPORTANT: Your actions must ALIGN with your diagnosis:
- If CPA spiked and you recommend reducing spend → use "budget_decrease"
- If ROAS dropped due to competition and you want to fight back → use "bid_increase"  
- If there's fraud → use "pause_campaign" + "bot_traffic" or "influencer_fraud"
- If creative is stale → use "creative_fatigue" + optionally "budget_decrease" to reduce waste

Respond in this exact JSON format:
{{
    "root_cause": "Primary root cause in one sentence",
    "confidence": 0.85,
    "supporting_evidence": [
        "Evidence point 1 (cite specific numbers)",
        "Evidence point 2",
        "Evidence point 3"
    ],
    "actions": [
        {{
            "template_id": "budget_decrease",
            "reason": "CPA increased 35% - reduce spend until efficiency improves",
            "priority": "high",
            "parameters": {{"adjustment_pct": 25}}
        }},
        {{
            "template_id": "creative_fatigue",
            "reason": "CTR dropped 20% suggesting ad fatigue",
            "priority": "medium",
            "parameters": {{}}
        }}
    ],
    "executive_summary": "One paragraph for C-suite: business impact, strategic implication, recommended decision",
    "director_summary": "Two paragraphs for marketing leadership: tactical situation, resource needs, timeline",
    "marketer_summary": "Detailed section for channel managers: specific platform actions, settings to change",
    "technical_details": "For data scientists: methodology notes, data quality issues, statistical caveats"
}}

Remember: The actions array must contain valid template_ids that MATCH your diagnosis."""


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
        action_catalog=ACTION_CATALOG,
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
            parsed = json.loads(json_match.group())
            
            # Validate actions exist and have template_ids
            if "actions" in parsed and isinstance(parsed["actions"], list):
                valid_actions = []
                for action in parsed["actions"]:
                    if isinstance(action, dict) and "template_id" in action:
                        valid_actions.append(action)
                parsed["actions"] = valid_actions
            else:
                # Fallback: try to extract from recommended_actions text
                parsed["actions"] = []
            
            return parsed
            
    except json.JSONDecodeError:
        pass
    
    # Fallback: return structured error
    return {
        "root_cause": "Unable to parse diagnosis",
        "confidence": 0.0,
        "supporting_evidence": ["Parser error - raw response available"],
        "actions": [],
        "executive_summary": response[:500] if response else "No response",
        "director_summary": "",
        "marketer_summary": "",
        "technical_details": f"Parse error. Raw response: {response}",
    }