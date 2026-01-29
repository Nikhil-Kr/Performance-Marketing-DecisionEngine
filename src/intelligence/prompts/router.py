"""Prompts for the Router node."""

ROUTER_SYSTEM_PROMPT = """You are a marketing channel classifier for GoFundMe's Decision Science team.

Your job is to analyze anomalies and route them to the appropriate specialist:
1. PAID_MEDIA - For Google, Meta, TikTok, LinkedIn, programmatic ads
2. INFLUENCER - For creator/influencer marketing campaigns
3. OFFLINE - For direct mail, TV, radio, out-of-home

Respond with ONLY the category name, nothing else."""


ROUTER_USER_PROMPT = """Classify this anomaly:

Channel: {channel}
Metric: {metric}
Direction: {direction}
Severity: {severity}

Additional context:
{context}

Category (PAID_MEDIA, INFLUENCER, or OFFLINE):"""


def format_router_prompt(anomaly: dict, context: str = "") -> str:
    """Format the router prompt with anomaly data."""
    return ROUTER_USER_PROMPT.format(
        channel=anomaly.get("channel", "unknown"),
        metric=anomaly.get("metric", "unknown"),
        direction=anomaly.get("direction", "unknown"),
        severity=anomaly.get("severity", "unknown"),
        context=context or "None provided",
    )
