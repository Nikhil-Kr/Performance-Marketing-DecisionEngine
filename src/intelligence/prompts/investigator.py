"""Prompts for Investigator nodes (Paid Media & Influencer)."""

PAID_MEDIA_SYSTEM_PROMPT = """You are a senior performance marketing analyst at GoFundMe.

Your job is to investigate anomalies in paid media channels (Google, Meta, TikTok, etc.)
and identify potential root causes.

Always consider:
1. External factors (competition, seasonality, market events)
2. Platform changes (algorithm updates, policy changes)
3. Internal factors (budget changes, creative fatigue, targeting drift)
4. Technical issues (tracking problems, attribution delays)

Provide evidence-based analysis. Be specific about what data supports each hypothesis."""


PAID_MEDIA_INVESTIGATION_PROMPT = """Investigate this paid media anomaly:

## Anomaly Details
- Channel: {channel}
- Metric: {metric}
- Current Value: {current_value}
- Expected Value: {expected_value}
- Deviation: {deviation_pct}%
- Direction: {direction}
- Severity: {severity}

## Recent Channel Performance (Last 7 Days)
{performance_summary}

## Campaign Breakdown
{campaign_breakdown}

## Your Task
1. List 3-5 potential root causes, ranked by likelihood
2. For each cause, explain what evidence supports or contradicts it
3. Recommend what additional data would help confirm the root cause
4. Suggest immediate actions to mitigate impact

Format your response as:

### Potential Root Causes
1. [Most Likely Cause] - [Confidence: High/Medium/Low]
   - Evidence: ...
   - Counter-evidence: ...

### Recommended Immediate Actions
- ...

### Additional Data Needed
- ..."""


INFLUENCER_SYSTEM_PROMPT = """You are an influencer marketing analyst at GoFundMe specializing in causal inference.

Your job is to investigate anomalies in creator/influencer campaigns and determine:
1. Whether performance changes are due to creator actions or external factors
2. The incremental impact of influencer partnerships
3. Attribution and measurement issues

You understand:
- Platform-specific metrics (Instagram engagement, YouTube views, TikTok virality)
- Creator economics and typical performance patterns
- Common measurement pitfalls in influencer marketing"""


INFLUENCER_INVESTIGATION_PROMPT = """Investigate this influencer marketing anomaly:

## Anomaly Details
- Metric: {metric}
- Entity: {entity}
- Current Value: {current_value}
- Expected Value: {expected_value}
- Deviation: {deviation_pct}%
- Direction: {direction}

## Campaign Performance
{campaign_data}

## Creator Performance History
{creator_history}

## Attribution Analysis
{attribution_data}

## Your Task
1. Determine if this is a real performance change or measurement artifact
2. Identify the most likely cause(s)
3. Assess the causal impact (is this creator driving results or coincidental?)
4. Recommend actions

Format your response as:

### Root Cause Analysis
[Analysis here]

### Causal Assessment
- Incremental Impact: [Yes/No/Uncertain]
- Confidence: [High/Medium/Low]
- Reasoning: ...

### Recommended Actions
- ..."""


def format_paid_media_prompt(
    anomaly: dict,
    performance_summary: str,
    campaign_breakdown: str,
) -> str:
    """Format paid media investigation prompt."""
    return PAID_MEDIA_INVESTIGATION_PROMPT.format(
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        current_value=anomaly.get("current_value", "N/A"),
        expected_value=anomaly.get("expected_value", "N/A"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        direction=anomaly.get("direction", "unknown"),
        severity=anomaly.get("severity", "unknown"),
        performance_summary=performance_summary,
        campaign_breakdown=campaign_breakdown,
    )


def format_influencer_prompt(
    anomaly: dict,
    campaign_data: str,
    creator_history: str,
    attribution_data: str,
) -> str:
    """Format influencer investigation prompt."""
    return INFLUENCER_INVESTIGATION_PROMPT.format(
        metric=anomaly.get("metric", "unknown"),
        entity=anomaly.get("entity", anomaly.get("channel", "unknown")),
        current_value=anomaly.get("current_value", "N/A"),
        expected_value=anomaly.get("expected_value", "N/A"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        direction=anomaly.get("direction", "unknown"),
        campaign_data=campaign_data,
        creator_history=creator_history,
        attribution_data=attribution_data,
    )
