# """Prompts for Investigator nodes (Paid Media & Influencer)."""

# PAID_MEDIA_SYSTEM_PROMPT = """You are a senior performance marketing analyst at GoFundMe.

# Your job is to investigate anomalies in paid media channels (Google, Meta, TikTok, etc.)
# and identify potential root causes.

# Always consider:
# 1. External factors (competition, seasonality, market events)
# 2. Platform changes (algorithm updates, policy changes)
# 3. Internal factors (budget changes, creative fatigue, targeting drift)
# 4. Technical issues (tracking problems, attribution delays)

# Provide evidence-based analysis. Be specific about what data supports each hypothesis."""


# PAID_MEDIA_INVESTIGATION_PROMPT = """Investigate this paid media anomaly:

# ## Anomaly Details
# - Channel: {channel}
# - Metric: {metric}
# - Current Value: {current_value}
# - Expected Value: {expected_value}
# - Deviation: {deviation_pct}%
# - Direction: {direction}
# - Severity: {severity}

# ## Recent Channel Performance (Last 7 Days)
# {performance_summary}

# ## Campaign Breakdown
# {campaign_breakdown}

# ## Your Task
# 1. List 3-5 potential root causes, ranked by likelihood
# 2. For each cause, explain what evidence supports or contradicts it
# 3. Recommend what additional data would help confirm the root cause
# 4. Suggest immediate actions to mitigate impact

# Format your response as:

# ### Potential Root Causes
# 1. [Most Likely Cause] - [Confidence: High/Medium/Low]
#    - Evidence: ...
#    - Counter-evidence: ...

# ### Recommended Immediate Actions
# - ...

# ### Additional Data Needed
# - ..."""


# INFLUENCER_SYSTEM_PROMPT = """You are an influencer marketing analyst at GoFundMe specializing in causal inference.

# Your job is to investigate anomalies in creator/influencer campaigns and determine:
# 1. Whether performance changes are due to creator actions or external factors
# 2. The incremental impact of influencer partnerships
# 3. Attribution and measurement issues

# You understand:
# - Platform-specific metrics (Instagram engagement, YouTube views, TikTok virality)
# - Creator economics and typical performance patterns
# - Common measurement pitfalls in influencer marketing"""


# INFLUENCER_INVESTIGATION_PROMPT = """Investigate this influencer marketing anomaly:

# ## Anomaly Details
# - Metric: {metric}
# - Entity: {entity}
# - Current Value: {current_value}
# - Expected Value: {expected_value}
# - Deviation: {deviation_pct}%
# - Direction: {direction}

# ## Campaign Performance
# {campaign_data}

# ## Creator Performance History
# {creator_history}

# ## Attribution Analysis
# {attribution_data}

# ## Your Task
# 1. Determine if this is a real performance change or measurement artifact
# 2. Identify the most likely cause(s)
# 3. Assess the causal impact (is this creator driving results or coincidental?)
# 4. Recommend actions

# Format your response as:

# ### Root Cause Analysis
# [Analysis here]

# ### Causal Assessment
# - Incremental Impact: [Yes/No/Uncertain]
# - Confidence: [High/Medium/Low]
# - Reasoning: ...

# ### Recommended Actions
# - ..."""


# def format_paid_media_prompt(
#     anomaly: dict,
#     performance_summary: str,
#     campaign_breakdown: str,
# ) -> str:
#     """Format paid media investigation prompt."""
#     return PAID_MEDIA_INVESTIGATION_PROMPT.format(
#         channel=anomaly.get("channel", "unknown"),
#         metric=anomaly.get("metric", "unknown"),
#         current_value=anomaly.get("current_value", "N/A"),
#         expected_value=anomaly.get("expected_value", "N/A"),
#         deviation_pct=anomaly.get("deviation_pct", "N/A"),
#         direction=anomaly.get("direction", "unknown"),
#         severity=anomaly.get("severity", "unknown"),
#         performance_summary=performance_summary,
#         campaign_breakdown=campaign_breakdown,
#     )


# def format_influencer_prompt(
#     anomaly: dict,
#     campaign_data: str,
#     creator_history: str,
#     attribution_data: str,
# ) -> str:
#     """Format influencer investigation prompt."""
#     return INFLUENCER_INVESTIGATION_PROMPT.format(
#         metric=anomaly.get("metric", "unknown"),
#         entity=anomaly.get("entity", anomaly.get("channel", "unknown")),
#         current_value=anomaly.get("current_value", "N/A"),
#         expected_value=anomaly.get("expected_value", "N/A"),
#         deviation_pct=anomaly.get("deviation_pct", "N/A"),
#         direction=anomaly.get("direction", "unknown"),
#         campaign_data=campaign_data,
#         creator_history=creator_history,
#         attribution_data=attribution_data,
#     )
# <----- TIER 3 & 4 --------->
# """Prompts for Investigator nodes (Paid Media & Influencer)."""

# PAID_MEDIA_SYSTEM_PROMPT = """You are a senior performance marketing analyst at GoFundMe.

# Your job is to investigate anomalies in paid media channels (Google, Meta, TikTok, etc.)
# and identify potential root causes.

# Always consider:
# 1. Internal factors (budget changes, creative fatigue, targeting drift)
# 2. External factors (competitor bidding, market demand changes)
# 3. Strategic context (MMM saturation, MTA vs Last-Click discrepancies)
# 4. Technical issues (tracking problems, attribution delays)

# Provide evidence-based analysis. Use Multi-Touch Attribution (MTA) data to verify if performance drops are real or just attribution artifacts."""


# PAID_MEDIA_INVESTIGATION_PROMPT = """Investigate this paid media anomaly:

# ## Analysis Context
# - **Analysis Period:** {analysis_start} to {analysis_end}
# - Focus your investigation on data and events within this time window.

# ## Anomaly Details
# - Date: {date}
# - Channel: {channel}
# - Metric: {metric}
# - Current Value: {current_value}
# - Expected Value: {expected_value}
# - Deviation: {deviation_pct}%
# - Direction: {direction}
# - Severity: {severity}

# ## Recent Channel Performance (within analysis period)
# {performance_summary}

# ## Campaign Breakdown
# {campaign_breakdown}

# ## Competitive Intelligence
# {competitor_intel}

# ## Market Trends
# {market_trends}

# ## Strategic Context (MMM & MTA)
# {strategy_context}

# ## Your Task
# 1. List 3-5 potential root causes, ranked by likelihood.
# 2. Analyze External Factors (Competitors) and Strategy (MTA/MMM).
# 3. Suggest immediate actions.

# Format your response as:

# ### Potential Root Causes
# 1. [Most Likely Cause] - [Confidence: High/Medium/Low]
#    - Evidence: ...
#    - Counter-evidence: ...

# ### Strategic Insights
# - MTA Analysis: ...
# - MMM Saturation: ...

# ### Recommended Immediate Actions
# - ..."""


# INFLUENCER_SYSTEM_PROMPT = """You are an influencer marketing analyst at GoFundMe specializing in causal inference.

# Your job is to investigate anomalies in creator/influencer campaigns and determine:
# 1. Whether performance changes are due to creator actions or external factors
# 2. The incremental impact of influencer partnerships
# 3. Attribution and measurement issues

# You understand:
# - Platform-specific metrics (Instagram engagement, YouTube views, TikTok virality)
# - Creator economics and typical performance patterns
# - Common measurement pitfalls in influencer marketing"""


# INFLUENCER_INVESTIGATION_PROMPT = """Investigate this influencer marketing anomaly:

# ## Analysis Context
# - **Analysis Period:** {analysis_start} to {analysis_end}
# - Focus your investigation on data and events within this time window.

# ## Anomaly Details
# - Date: {date}
# - Metric: {metric}
# - Entity: {entity}
# - Current Value: {current_value}
# - Expected Value: {expected_value}
# - Deviation: {deviation_pct}%
# - Direction: {direction}

# ## Campaign Performance
# {campaign_data}

# ## Creator Performance History
# {creator_history}

# ## Attribution Analysis
# {attribution_data}

# ## Your Task
# 1. Determine if this is a real performance change or measurement artifact.
# 2. Assess the causal impact (is this creator driving results or coincidental?).
# 3. Recommend actions.

# Format your response as:

# ### Root Cause Analysis
# [Analysis here]

# ### Causal Assessment
# - Incremental Impact: [Yes/No/Uncertain]
# - Confidence: [High/Medium/Low]
# - Reasoning: ...

# ### Recommended Actions
# - ..."""


# def format_paid_media_prompt(
#     anomaly: dict,
#     performance_summary: str,
#     campaign_breakdown: str,
#     competitor_intel: str = "N/A",
#     market_trends: str = "N/A",
#     strategy_context: str = "N/A",
#     analysis_start: str = "N/A",
#     analysis_end: str = "N/A",
# ) -> str:
#     """Format paid media investigation prompt with analysis period context."""
#     return PAID_MEDIA_INVESTIGATION_PROMPT.format(
#         analysis_start=analysis_start,
#         analysis_end=analysis_end,
#         date=anomaly.get("detected_at", "Unknown"),
#         channel=anomaly.get("channel", "unknown"),
#         metric=anomaly.get("metric", "unknown"),
#         current_value=anomaly.get("current_value", "N/A"),
#         expected_value=anomaly.get("expected_value", "N/A"),
#         deviation_pct=anomaly.get("deviation_pct", "N/A"),
#         direction=anomaly.get("direction", "unknown"),
#         severity=anomaly.get("severity", "unknown"),
#         performance_summary=performance_summary,
#         campaign_breakdown=campaign_breakdown,
#         competitor_intel=competitor_intel,
#         market_trends=market_trends,
#         strategy_context=strategy_context,
#     )


# def format_influencer_prompt(
#     anomaly: dict,
#     campaign_data: str,
#     creator_history: str,
#     attribution_data: str,
#     analysis_start: str = "N/A",
#     analysis_end: str = "N/A",
# ) -> str:
#     """Format influencer investigation prompt with analysis period context."""
#     return INFLUENCER_INVESTIGATION_PROMPT.format(
#         analysis_start=analysis_start,
#         analysis_end=analysis_end,
#         date=anomaly.get("detected_at", "Unknown"),
#         metric=anomaly.get("metric", "unknown"),
#         entity=anomaly.get("entity", anomaly.get("channel", "unknown")),
#         current_value=anomaly.get("current_value", "N/A"),
#         expected_value=anomaly.get("expected_value", "N/A"),
#         deviation_pct=anomaly.get("deviation_pct", "N/A"),
#         direction=anomaly.get("direction", "unknown"),
#         campaign_data=campaign_data,
#         creator_history=creator_history,
#         attribution_data=attribution_data,
#     )

## <--------- Updated - 3/3 --------->
"""Prompts for Investigator nodes (Paid Media, Influencer, & Offline)."""

PAID_MEDIA_SYSTEM_PROMPT = """You are a senior performance marketing analyst at GoFundMe.

Your job is to investigate anomalies in paid media channels (Google, Meta, TikTok, etc.)
and identify potential root causes.

Always consider:
1. External factors (competition, seasonality, market events)
2. Platform changes (algorithm updates, policy changes)
3. Internal factors (budget changes, creative fatigue, targeting drift)
4. Technical issues (tracking problems, attribution delays)
5. Cross-channel signals (if other channels show similar patterns, consider shared root causes)

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
{correlation_context}

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
{correlation_context}

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


# ============================================================================
# NEW: Offline Channel Prompts (Improvement #5)
# ============================================================================

OFFLINE_SYSTEM_PROMPT = """You are a senior marketing analyst at GoFundMe specializing in offline and traditional media channels.

Your job is to investigate anomalies in offline channels including:
- TV (Linear & CTV/OTT): GRP delivery, preemptions, frequency, Nielsen measurement
- Radio: Spot delivery, daypart performance, streaming vs terrestrial
- OOH (Out-of-Home): Billboard/transit impressions, geofencing, weather/construction
- Events: Attendance, lead quality, cost per attendee, seasonal patterns
- Podcast: Download rates, completion rates, host-read effectiveness, promo codes
- Direct Mail: Response rates, delivery timing, list quality, seasonal volume

Key differences from digital:
- Measurement is often delayed (Nielsen 2-3 day lag, mail delivery 3-10 days)
- Attribution is indirect (brand lift studies, MMM, promo codes vs pixel tracking)
- Make-goods and negotiations are standard remediation (not just bid/budget changes)
- External factors (weather, news events, postal delays) affect offline more than digital

Always ground your analysis in the data provided. Use probability language when root causes are not proven."""


OFFLINE_INVESTIGATION_PROMPT = """Investigate this offline channel anomaly:

## Anomaly Details
- Channel: {channel}
- Metric: {metric}
- Current Value: {current_value}
- Expected Value: {expected_value}
- Deviation: {deviation_pct}%
- Direction: {direction}
- Severity: {severity}

## Recent Channel Performance
{performance_summary}

## Channel-Specific Context
{channel_context}
{correlation_context}

## Your Task
1. List 3-5 potential root causes specific to this offline channel, ranked by likelihood
2. For each cause, explain what evidence supports or contradicts it
3. Consider measurement/reporting artifacts that could explain the anomaly
4. Recommend offline-specific remediation (make-goods, partner negotiations, schedule adjustments)

Format your response as:

### Potential Root Causes
1. [Most Likely Cause] - [Confidence: High/Medium/Low]
   - Evidence: ...
   - Counter-evidence: ...

### Measurement Considerations
- [Any measurement or reporting artifacts that could explain this]

### Recommended Actions
- [Offline-specific remediation steps]

### Additional Data Needed
- ..."""


# ============================================================================
# Format Functions
# ============================================================================

def format_paid_media_prompt(
    anomaly: dict,
    performance_summary: str,
    campaign_breakdown: str,
    correlation_context: str = "",
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
        correlation_context=correlation_context,
    )


def format_influencer_prompt(
    anomaly: dict,
    campaign_data: str,
    creator_history: str,
    attribution_data: str,
    correlation_context: str = "",
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
        correlation_context=correlation_context,
    )


def format_offline_prompt(
    anomaly: dict,
    performance_summary: str,
    channel_context: str,
    correlation_context: str = "",
) -> str:
    """Format offline channel investigation prompt."""
    return OFFLINE_INVESTIGATION_PROMPT.format(
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        current_value=anomaly.get("current_value", "N/A"),
        expected_value=anomaly.get("expected_value", "N/A"),
        deviation_pct=anomaly.get("deviation_pct", "N/A"),
        direction=anomaly.get("direction", "unknown"),
        severity=anomaly.get("severity", "unknown"),
        performance_summary=performance_summary,
        channel_context=channel_context,
        correlation_context=correlation_context,
    )
