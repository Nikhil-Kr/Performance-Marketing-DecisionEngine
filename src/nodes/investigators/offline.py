"""Offline Channel Investigator Node - Analyzes TV, Radio, OOH, Events, Podcast, Direct Mail."""
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data
from src.intelligence.models import get_llm_safe, extract_content
from src.intelligence.prompts.investigator import (
    OFFLINE_SYSTEM_PROMPT,
    format_offline_prompt,
)
from src.nodes.investigators.utils import (
    extract_analysis_dates, fetch_market_context, format_correlation_context,
)
from src.utils.logging import get_logger

logger = get_logger("investigator.offline")


def investigate_offline(state: ExpeditionState) -> dict:
    """
    Offline Channel Investigator Node.

    Specialized investigator for offline channels (TV, Radio, OOH, Events, Podcast, Direct Mail).
    Now includes market intelligence (competitor signals, market trends), strategy context
    (MMM saturation, MTA), and respects the analysis date range selected in the UI.

    Uses Tier 1 (Flash) model for initial analysis.
    """
    logger.info("Investigating Offline Channel...")

    anomaly = state.get("selected_anomaly")
    correlated = state.get("correlated_anomalies", [])

    if not anomaly:
        return {
            "investigation_evidence": None,
            "investigation_summary": "No anomaly to investigate",
            "current_node": "investigate_offline",
        }

    channel = anomaly.get("channel", "unknown")

    # --- Resolve analysis date range (P4: time-travel) ---
    analysis_start, analysis_end = extract_analysis_dates(state, anomaly)
    analysis_days = max((analysis_end - analysis_start).days, 1)
    lookback_days = min(analysis_days, 14)

    logger.info("Analysis Period: %s to %s", analysis_start.strftime('%Y-%m-%d'), analysis_end.strftime('%Y-%m-%d'))

    # --- 1. Internal performance data (time-travel enabled) ---
    marketing = get_marketing_data()
    performance_df = marketing.get_channel_performance(channel, days=lookback_days, end_date=analysis_end)
    performance_summary = (
        _summarize_offline_performance(performance_df, channel) if not performance_df.empty
        else "No performance data available"
    )

    # --- 2. Market intelligence + strategy context (time-travel enabled) ---
    market_ctx = fetch_market_context(channel, analysis_end, analysis_days)
    competitor_intel = market_ctx["competitor_intel"]
    market_trends = market_ctx["market_trends"]
    strategy_text = market_ctx["strategy_context"]

    # Combine strategy with offline-specific guidance
    offline_context_text = _get_channel_context(channel)
    channel_context = f"{strategy_text}\n\n{offline_context_text}"

    # Correlation context
    correlation_context = format_correlation_context(correlated) if correlated else ""

    # --- Package raw evidence ---
    raw_evidence = {
        "channel": channel,
        "anomaly": anomaly,
        "performance_summary": performance_summary,
        "channel_context": channel_context,
        "competitor_intel": competitor_intel,
        "market_trends": market_trends,
        "correlation_context": correlation_context,
        "recent_metrics": performance_df.tail(7).to_dict() if not performance_df.empty else {},
        "analysis_start": analysis_start.strftime("%Y-%m-%d"),
        "analysis_end": analysis_end.strftime("%Y-%m-%d"),
    }

    # --- 4. Build prompt and call LLM ---
    # Prepend market/competitor intelligence into performance context for the offline prompt
    full_performance = (
        f"{performance_summary}\n\n"
        f"## Competitive Intelligence\n{competitor_intel}\n\n"
        f"## Market Trends\n{market_trends}"
    )

    try:
        llm = get_llm_safe("tier1")

        prompt = format_offline_prompt(
            anomaly=anomaly,
            performance_summary=full_performance,
            channel_context=channel_context,
            correlation_context=correlation_context,
            analysis_start=analysis_start.strftime("%Y-%m-%d"),
            analysis_end=analysis_end.strftime("%Y-%m-%d"),
        )

        messages = [
            {"role": "system", "content": OFFLINE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = llm.invoke(messages)
        investigation_summary = extract_content(response)
        logger.info("Offline investigation complete for %s", channel)

    except Exception as e:
        logger.error("LLM investigation failed: %s", e, exc_info=True)
        investigation_summary = f"Investigation error: {str(e)}"

    return {
        "investigation_evidence": raw_evidence,
        "investigation_summary": investigation_summary,
        "current_node": "investigate_offline",
    }


def _summarize_offline_performance(df, channel: str) -> str:
    """Create a text summary tailored to offline channel metrics."""
    lines = []
    offline_metrics = {
        "tv": ["spend", "impressions", "conversions", "cpa", "roas"],
        "radio": ["spend", "impressions", "conversions", "cpa"],
        "ooh": ["spend", "impressions", "cpa"],
        "events": ["spend", "conversions", "cpa", "roas"],
        "podcast": ["spend", "clicks", "conversions", "cpa", "roas"],
        "direct_mail": ["spend", "conversions", "cpa", "roas"],
    }
    metrics_to_check = offline_metrics.get(channel, ["spend", "cpa", "roas", "conversions"])
    for metric in metrics_to_check:
        if metric in df.columns:
            recent_avg = df[metric].tail(3).mean()
            prior_avg = df[metric].head(len(df) - 3).mean()
            if prior_avg > 0:
                change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
                trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
                lines.append(f"- {metric.upper()}: {recent_avg:.2f} ({trend} {change_pct:+.1f}% vs prior)")
    if channel == "tv" and "impressions" in df.columns:
        total_impressions = df["impressions"].tail(7).sum()
        lines.append(f"- Est. GRPs (7-day): {total_impressions / 1000:.0f}k impressions delivered")
    if channel == "direct_mail" and "conversions" in df.columns:
        total_spend = df["spend"].tail(7).sum()
        total_conv = df["conversions"].tail(7).sum()
        response_rate = total_conv / max(total_spend / 5, 1) * 100
        lines.append(f"- Est. Response Rate: {response_rate:.2f}%")
    return "\n".join(lines) if lines else "No metrics available"


def _get_channel_context(channel: str) -> str:
    """Return channel-specific investigation context and common issues."""
    contexts = {
        "tv": """### TV Channel Context
- Linear TV spots can be preempted by breaking news or sports events
- CTV/OTT inventory has frequency capping and viewability concerns
- Nielsen measurement has 2-3 day reporting lag
- Make-goods are standard remedy for under-delivered GRPs
- Check for daypart shifts (primetime vs daytime performance)""",
        "radio": """### Radio Channel Context
- Spot delivery verification through affidavit reports
- Drive-time (AM/PM commute) vs midday performance varies significantly
- Market-specific issues (weather, local events) affect listenership
- Streaming radio (iHeart, Spotify) has different measurement than terrestrial""",
        "ooh": """### OOH (Out-of-Home) Channel Context
- Billboard/transit impression estimates based on traffic data
- Geofencing and mobile measurement for attribution
- Weather and construction can block visibility
- Digital OOH has rotation and share-of-voice considerations""",
        "events": """### Events Channel Context
- Attendance tracking (registered vs actual) affects CPA
- Lead quality varies by event type (conference vs trade show)
- High upfront cost with delayed conversion attribution
- Seasonal patterns (Q1 trade shows, Q3 conferences)""",
        "podcast": """### Podcast Channel Context
- Downloads vs listens vs completions are different metrics
- Host-read vs produced ads have different engagement rates
- Promo code and vanity URL tracking for attribution
- Episode release timing affects download volume
- IAB certification standards for measurement""",
        "direct_mail": """### Direct Mail Channel Context
- Response rates typically 1-5% depending on list quality
- Delivery timing: 3-10 business days for standard, 1-3 for express
- List fatigue and suppression file management
- Seasonal patterns (holiday mail volume affects delivery)
- A/B testing requires sufficient volume per variant""",
    }
    return contexts.get(channel, f"### Offline Channel Considerations\n- Attribution is typically modeled, not directly tracked\n- Consider 4-8 week lag for brand lift impact")

