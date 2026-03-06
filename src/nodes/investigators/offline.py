# """Offline Media Investigator Node - Handles TV, Podcast, Radio, Direct Mail, etc."""
# from datetime import datetime, timedelta
# import pandas as pd
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_marketing_data, get_market_data, get_strategy_data
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.investigator import PAID_MEDIA_SYSTEM_PROMPT, format_paid_media_prompt


# # Offline channels that this investigator handles
# OFFLINE_CHANNELS = {"direct_mail", "tv", "radio", "ooh", "events", "podcast"}


# def investigate_offline(state: ExpeditionState) -> dict:
#     """
#     Investigates anomalies in offline media channels (TV, Podcast, Radio, etc.).
    
#     Uses the same structure as paid_media investigator but with
#     offline-specific context and analysis.
    
#     Uses the analysis date range from state (user-selected) to ensure
#     all data fetching and context is bounded appropriately.
#     """
#     print("\n🔬 Investigating Offline Media...")
    
#     anomaly = state.get("selected_anomaly")
#     if not anomaly:
#         return {"investigation_summary": "No anomaly selected."}

#     channel = anomaly.get("channel")
    
#     # EXTRACT ANALYSIS DATE RANGE FROM STATE (prioritize state over anomaly)
#     analysis_start = None
#     analysis_end = None
    
#     # Try state first (user's selected range)
#     if state.get("analysis_start_date"):
#         try:
#             analysis_start = datetime.strptime(state["analysis_start_date"], "%Y-%m-%d")
#         except (ValueError, TypeError):
#             pass
            
#     if state.get("analysis_end_date"):
#         try:
#             analysis_end = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
#         except (ValueError, TypeError):
#             pass
    
#     # Fallback to anomaly's detected_at if state doesn't have dates
#     if not analysis_end:
#         try:
#             detect_date_str = anomaly.get("detected_at")
#             if detect_date_str:
#                 analysis_end = datetime.strptime(detect_date_str, "%Y-%m-%d")
#             else:
#                 analysis_end = datetime.now()
#         except Exception:
#             analysis_end = datetime.now()
    
#     # Default start to 30 days before end if not specified
#     if not analysis_start:
#         analysis_start = analysis_end - timedelta(days=30)
    
#     # Calculate days in the analysis window for lookback
#     analysis_days = (analysis_end - analysis_start).days
#     lookback_days = min(analysis_days, 14)  # Cap at 14 for readability
        
#     print(f"  📅 Analysis Period: {analysis_start.strftime('%Y-%m-%d')} to {analysis_end.strftime('%Y-%m-%d')}")
    
#     # 1. Internal Data (Time-Travel enabled with analysis range)
#     marketing = get_marketing_data()
#     performance = marketing.get_channel_performance(channel, days=lookback_days, end_date=analysis_end)
#     breakdown = marketing.get_campaign_breakdown(channel, days=lookback_days, end_date=analysis_end)
    
#     # 2. Market Intelligence (Time-Travel enabled)
#     market = get_market_data()
#     competitors = market.get_competitor_signals(channel, reference_date=analysis_end)
#     trends = market.get_market_interest(days=analysis_days, end_date=analysis_end)
    
#     # 3. Strategy Data (Time-Travel enabled)
#     strategy = get_strategy_data()
#     mmm = strategy.get_mmm_guardrails(channel, reference_date=analysis_end) 
#     mta = strategy.get_mta_comparison(channel, reference_date=analysis_end)
    
#     # Format Contexts
#     competitor_text = _format_competitors(competitors)
#     trend_text = _format_trends(trends)
#     strategy_text = _format_strategy(mmm, mta)
    
#     # Add offline-specific context
#     offline_context = _get_offline_context(channel, anomaly)
    
#     # 4. Format Prompt (includes analysis period context)
#     # We reuse the paid_media prompt format since it's comprehensive
#     prompt = format_paid_media_prompt(
#         anomaly=anomaly,
#         performance_summary=performance.to_markdown(index=False) if not performance.empty else "No data available",
#         campaign_breakdown=breakdown.to_markdown(index=False) if not breakdown.empty else "No data available",
#         competitor_intel=competitor_text,
#         market_trends=trend_text,
#         strategy_context=f"{strategy_text}\n\n{offline_context}",
#         analysis_start=analysis_start.strftime('%Y-%m-%d'),
#         analysis_end=analysis_end.strftime('%Y-%m-%d'),
#     )
    
#     # 5. Call LLM
#     try:
#         llm = get_llm_safe("tier1")
#         messages = [
#             {"role": "system", "content": OFFLINE_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt}
#         ]
#         response = llm.invoke(messages)
#         content = response.content
        
#     except Exception as e:
#         print(f"  ⚠️ Investigation failed: {e}")
#         content = f"Investigation error: {str(e)}"
    
#     print("  ✅ Investigation complete")
    
#     return {
#         "investigation_summary": content,
#         "investigation_evidence": prompt,
#         "current_node": "investigate_offline"
#     }


# # System prompt specific to offline media
# OFFLINE_SYSTEM_PROMPT = """You are an expert marketing analyst specializing in offline media channels: TV, Radio, Podcast, Direct Mail, Out-of-Home (OOH), and Events.

# Your investigation style:
# 1. Consider offline-specific factors: GRP delivery, make-good credits, flight timing, inventory quality
# 2. Think about brand lift and long attribution windows (offline often has 4-8 week lag)
# 3. Consider external factors: seasonality, competitor TV presence, PR events
# 4. Remember offline metrics are often modeled/estimated, not directly tracked

# Investigation Framework:
# 1. IDENTIFY patterns in the data (leading indicators, timing, geographic spread)
# 2. HYPOTHESIZE potential root causes with confidence levels
# 3. RECOMMEND specific next steps (vendor follow-up, measurement audits, creative refresh)

# Format your response with:
# - ## Summary (1-2 sentences)
# - ## Potential Root Causes (ranked by likelihood)
# - ## Offline-Specific Considerations
# - ## Recommended Actions
# """


# def _format_competitors(signals: list) -> str:
#     if not signals: 
#         return "No significant competitor activity detected in this period."
#     lines = [f"- {s.get('date')}: {s.get('competitor')} ({s.get('activity_type')}) - {s.get('details')}" for s in signals]
#     return "\n".join(lines)


# def _format_trends(trends: list) -> str:
#     if not trends: 
#         return "No market trend data available."
#     recent = trends[-5:]  # Show last 5 points leading up to the anomaly
#     lines = [f"- {t.get('date')}: Interest Score {t.get('interest_score')}" for t in recent]
#     return "\n".join(lines)


# def _format_strategy(mmm: dict, mta: dict) -> str:
#     lines = []
#     if mmm:
#         lines.append("### MMM Saturation Analysis")
#         lines.append(f"- Saturation Point: ${mmm.get('saturation_point_daily', 'N/A')}/day")
#         lines.append(f"- Marginal ROAS: {mmm.get('current_marginal_roas', 'N/A')}")
#         lines.append(f"- Recommendation: {mmm.get('recommendation', 'N/A').upper()}")
#     else:
#         lines.append("### MMM Analysis: Not available")
        
#     if mta:
#         lines.append("\n### MTA Attribution Comparison")
#         lines.append(f"- Last Click ROAS: {mta.get('last_click_roas', 'N/A')}")
#         lines.append(f"- MTA ROAS: {mta.get('data_driven_roas', 'N/A')}")
#         diff = mta.get('data_driven_roas', 0) - mta.get('last_click_roas', 0)
#         if diff > 0.5: 
#             lines.append("  *NOTE: Channel is undervalued by Last Click (common for offline).*")
#         elif diff < -0.5: 
#             lines.append("  *NOTE: Channel is overvalued by Last Click.*")
#     else:
#         lines.append("\n### MTA Analysis: Not available")
        
#     return "\n".join(lines)


# def _get_offline_context(channel: str, anomaly: dict) -> str:
#     """Generate offline-specific context based on channel type."""
#     channel_lower = channel.lower()
    
#     contexts = {
#         "tv": """### TV-Specific Considerations
# - Check for pre-emptions or make-good credits owed
# - Verify GRP delivery against contracted rates
# - Consider daypart mix changes
# - Review competitive share of voice in key markets""",
        
#         "podcast": """### Podcast-Specific Considerations
# - Attribution window is typically 14-30 days
# - Check host-read vs. programmatic mix
# - Verify download metrics vs. listener estimates
# - Consider category saturation (many podcast listeners overlap)""",
        
#         "radio": """### Radio-Specific Considerations
# - Check for format changes at key stations
# - Verify reach/frequency delivery
# - Consider streaming radio cannibalization
# - Review drive-time vs. midday mix""",
        
#         "direct_mail": """### Direct Mail-Specific Considerations
# - Check delivery timing and postal delays
# - Verify list quality and suppression accuracy
# - Consider response lag (typically 2-4 weeks)
# - Review creative fatigue on recurring campaigns""",
        
#         "ooh": """### Out-of-Home Specific Considerations
# - Check for construction or visibility issues at units
# - Verify traffic count data accuracy
# - Consider weather impacts on pedestrian traffic
# - Review digital vs. static unit mix""",
        
#         "events": """### Events-Specific Considerations
# - Review attendance vs. projections
# - Check lead quality and follow-up conversion
# - Consider post-event content amplification
# - Verify sponsorship placement visibility""",
#     }
    
#     return contexts.get(channel_lower, """### Offline Channel Considerations
# - Attribution is typically modeled, not directly tracked
# - Consider 4-8 week lag for brand lift impact
# - Check vendor-reported vs. third-party measurement discrepancies""")

## <--------- V3 - Specialized Offline Context, No Date Range (Previous Active) --------->

# ## <--------- Updated - 3/3 --------->
# """Offline Channel Investigator - V3 used marketing data only, no market/strategy, no date range."""
# def investigate_offline(state) -> dict: ...  (no analysis_start/end, no competitor/strategy data)
# def _summarize_offline_performance(df, channel): ...
# def _get_channel_context(channel): ...
# def _format_correlation_context(correlated): ...

## <--------- V4 - Market + Strategy Intelligence + Date Range Restored --------->

"""Offline Channel Investigator Node - Analyzes TV, Radio, OOH, Events, Podcast, Direct Mail."""
from datetime import datetime, timedelta
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data, get_market_data, get_strategy_data
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.investigator import (
    OFFLINE_SYSTEM_PROMPT,
    format_offline_prompt,
)


def investigate_offline(state: ExpeditionState) -> dict:
    """
    Offline Channel Investigator Node.

    Specialized investigator for offline channels (TV, Radio, OOH, Events, Podcast, Direct Mail).
    Now includes market intelligence (competitor signals, market trends), strategy context
    (MMM saturation, MTA), and respects the analysis date range selected in the UI.

    Uses Tier 1 (Flash) model for initial analysis.
    """
    print("\n📺 Investigating Offline Channel...")

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
    analysis_start = None
    analysis_end = None

    if state.get("analysis_start_date"):
        try:
            analysis_start = datetime.strptime(state["analysis_start_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    if state.get("analysis_end_date"):
        try:
            analysis_end = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    if not analysis_end:
        try:
            detect_str = anomaly.get("detected_at")
            analysis_end = datetime.strptime(detect_str, "%Y-%m-%d") if detect_str else datetime.now()
        except Exception:
            analysis_end = datetime.now()

    if not analysis_start:
        analysis_start = analysis_end - timedelta(days=30)

    analysis_days = max((analysis_end - analysis_start).days, 1)
    lookback_days = min(analysis_days, 14)

    print(f"  📅 Analysis Period: {analysis_start.strftime('%Y-%m-%d')} to {analysis_end.strftime('%Y-%m-%d')}")

    # --- 1. Internal performance data (time-travel enabled) ---
    marketing = get_marketing_data()
    performance_df = marketing.get_channel_performance(channel, days=lookback_days, end_date=analysis_end)
    performance_summary = (
        _summarize_offline_performance(performance_df, channel) if not performance_df.empty
        else "No performance data available"
    )

    # --- 2. Market intelligence (time-travel enabled) ---
    market = get_market_data()
    competitors = market.get_competitor_signals(channel, reference_date=analysis_end)
    trends = market.get_market_interest(days=analysis_days, end_date=analysis_end)
    competitor_intel = _format_competitors(competitors)
    market_trends = _format_trends(trends)

    # --- 3. Strategy context (time-travel enabled) ---
    strategy = get_strategy_data()
    mmm = strategy.get_mmm_guardrails(channel, reference_date=analysis_end)
    mta = strategy.get_mta_comparison(channel, reference_date=analysis_end)
    strategy_text = _format_strategy(mmm, mta)

    # Combine strategy with offline-specific guidance
    offline_context_text = _get_channel_context(channel)
    channel_context = f"{strategy_text}\n\n{offline_context_text}"

    # Correlation context
    correlation_context = _format_correlation_context(correlated) if correlated else ""

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
        )

        messages = [
            {"role": "system", "content": OFFLINE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = llm.invoke(messages)
        investigation_summary = response.content
        print(f"  ✅ Offline investigation complete for {channel}")

    except Exception as e:
        print(f"  ⚠️ LLM investigation failed: {e}")
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


def _format_competitors(signals: list) -> str:
    if not signals:
        return "No significant competitor activity detected in this period."
    lines = [
        f"- {s.get('date')}: {s.get('competitor')} ({s.get('activity_type')}) - {s.get('details')}"
        for s in signals
    ]
    return "\n".join(lines)


def _format_trends(trends: list) -> str:
    if not trends:
        return "No market trend data available."
    recent = trends[-5:]
    lines = [f"- {t.get('date')}: Interest Score {t.get('interest_score')}" for t in recent]
    return "\n".join(lines)


def _format_strategy(mmm: dict, mta: dict) -> str:
    lines = []
    if mmm:
        lines.append("### MMM Saturation Analysis")
        lines.append(f"- Saturation Point: ${mmm.get('saturation_point_daily', 'N/A')}/day")
        lines.append(f"- Marginal ROAS: {mmm.get('current_marginal_roas', 'N/A')}")
        lines.append(f"- Recommendation: {mmm.get('recommendation', 'N/A').upper()}")
    else:
        lines.append("### MMM Analysis: Not available")
    if mta:
        lines.append("\n### MTA Attribution Comparison")
        lines.append(f"- Last Click ROAS: {mta.get('last_click_roas', 'N/A')}")
        lines.append(f"- MTA ROAS: {mta.get('data_driven_roas', 'N/A')}")
        diff = mta.get("data_driven_roas", 0) - mta.get("last_click_roas", 0)
        if diff > 0.5:
            lines.append("  *NOTE: Channel is undervalued by Last Click (common for offline).*")
        elif diff < -0.5:
            lines.append("  *NOTE: Channel is overvalued by Last Click.*")
    else:
        lines.append("\n### MTA Analysis: Not available")
    return "\n".join(lines)


def _format_correlation_context(correlated: list) -> str:
    """Format cross-channel correlations for the investigator."""
    lines = ["\n## Cross-Channel Correlations"]
    lines.append("The following anomalies were detected simultaneously and may share a root cause:\n")
    for c in correlated[:3]:
        reasons = ", ".join(c.get("correlation_reasons", []))
        lines.append(
            f"- **{c.get('channel', 'unknown')}** {c.get('metric', '')} "
            f"{c.get('direction', '')} {c.get('deviation_pct', 0):+.1f}% "
            f"(correlation: {reasons})"
        )
    lines.append("\nConsider whether a shared root cause (e.g., tracking failure, market event) explains multiple channels.")
    return "\n".join(lines)

