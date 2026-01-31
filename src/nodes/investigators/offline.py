"""Offline Media Investigator Node - Handles TV, Podcast, Radio, Direct Mail, etc."""
from datetime import datetime, timedelta
import pandas as pd
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data, get_market_data, get_strategy_data
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.investigator import PAID_MEDIA_SYSTEM_PROMPT, format_paid_media_prompt


# Offline channels that this investigator handles
OFFLINE_CHANNELS = {"direct_mail", "tv", "radio", "ooh", "events", "podcast"}


def investigate_offline(state: ExpeditionState) -> dict:
    """
    Investigates anomalies in offline media channels (TV, Podcast, Radio, etc.).
    
    Uses the same structure as paid_media investigator but with
    offline-specific context and analysis.
    
    Uses the analysis date range from state (user-selected) to ensure
    all data fetching and context is bounded appropriately.
    """
    print("\n🔬 Investigating Offline Media...")
    
    anomaly = state.get("selected_anomaly")
    if not anomaly:
        return {"investigation_summary": "No anomaly selected."}

    channel = anomaly.get("channel")
    
    # EXTRACT ANALYSIS DATE RANGE FROM STATE (prioritize state over anomaly)
    analysis_start = None
    analysis_end = None
    
    # Try state first (user's selected range)
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
    
    # Fallback to anomaly's detected_at if state doesn't have dates
    if not analysis_end:
        try:
            detect_date_str = anomaly.get("detected_at")
            if detect_date_str:
                analysis_end = datetime.strptime(detect_date_str, "%Y-%m-%d")
            else:
                analysis_end = datetime.now()
        except Exception:
            analysis_end = datetime.now()
    
    # Default start to 30 days before end if not specified
    if not analysis_start:
        analysis_start = analysis_end - timedelta(days=30)
    
    # Calculate days in the analysis window for lookback
    analysis_days = (analysis_end - analysis_start).days
    lookback_days = min(analysis_days, 14)  # Cap at 14 for readability
        
    print(f"  📅 Analysis Period: {analysis_start.strftime('%Y-%m-%d')} to {analysis_end.strftime('%Y-%m-%d')}")
    
    # 1. Internal Data (Time-Travel enabled with analysis range)
    marketing = get_marketing_data()
    performance = marketing.get_channel_performance(channel, days=lookback_days, end_date=analysis_end)
    breakdown = marketing.get_campaign_breakdown(channel, days=lookback_days, end_date=analysis_end)
    
    # 2. Market Intelligence (Time-Travel enabled)
    market = get_market_data()
    competitors = market.get_competitor_signals(channel, reference_date=analysis_end)
    trends = market.get_market_interest(days=analysis_days, end_date=analysis_end)
    
    # 3. Strategy Data (Time-Travel enabled)
    strategy = get_strategy_data()
    mmm = strategy.get_mmm_guardrails(channel, reference_date=analysis_end) 
    mta = strategy.get_mta_comparison(channel, reference_date=analysis_end)
    
    # Format Contexts
    competitor_text = _format_competitors(competitors)
    trend_text = _format_trends(trends)
    strategy_text = _format_strategy(mmm, mta)
    
    # Add offline-specific context
    offline_context = _get_offline_context(channel, anomaly)
    
    # 4. Format Prompt (includes analysis period context)
    # We reuse the paid_media prompt format since it's comprehensive
    prompt = format_paid_media_prompt(
        anomaly=anomaly,
        performance_summary=performance.to_markdown(index=False) if not performance.empty else "No data available",
        campaign_breakdown=breakdown.to_markdown(index=False) if not breakdown.empty else "No data available",
        competitor_intel=competitor_text,
        market_trends=trend_text,
        strategy_context=f"{strategy_text}\n\n{offline_context}",
        analysis_start=analysis_start.strftime('%Y-%m-%d'),
        analysis_end=analysis_end.strftime('%Y-%m-%d'),
    )
    
    # 5. Call LLM
    try:
        llm = get_llm_safe("tier1")
        messages = [
            {"role": "system", "content": OFFLINE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        response = llm.invoke(messages)
        content = response.content
        
    except Exception as e:
        print(f"  ⚠️ Investigation failed: {e}")
        content = f"Investigation error: {str(e)}"
    
    print("  ✅ Investigation complete")
    
    return {
        "investigation_summary": content,
        "investigation_evidence": prompt,
        "current_node": "investigate_offline"
    }


# System prompt specific to offline media
OFFLINE_SYSTEM_PROMPT = """You are an expert marketing analyst specializing in offline media channels: TV, Radio, Podcast, Direct Mail, Out-of-Home (OOH), and Events.

Your investigation style:
1. Consider offline-specific factors: GRP delivery, make-good credits, flight timing, inventory quality
2. Think about brand lift and long attribution windows (offline often has 4-8 week lag)
3. Consider external factors: seasonality, competitor TV presence, PR events
4. Remember offline metrics are often modeled/estimated, not directly tracked

Investigation Framework:
1. IDENTIFY patterns in the data (leading indicators, timing, geographic spread)
2. HYPOTHESIZE potential root causes with confidence levels
3. RECOMMEND specific next steps (vendor follow-up, measurement audits, creative refresh)

Format your response with:
- ## Summary (1-2 sentences)
- ## Potential Root Causes (ranked by likelihood)
- ## Offline-Specific Considerations
- ## Recommended Actions
"""


def _format_competitors(signals: list) -> str:
    if not signals: 
        return "No significant competitor activity detected in this period."
    lines = [f"- {s.get('date')}: {s.get('competitor')} ({s.get('activity_type')}) - {s.get('details')}" for s in signals]
    return "\n".join(lines)


def _format_trends(trends: list) -> str:
    if not trends: 
        return "No market trend data available."
    recent = trends[-5:]  # Show last 5 points leading up to the anomaly
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
        diff = mta.get('data_driven_roas', 0) - mta.get('last_click_roas', 0)
        if diff > 0.5: 
            lines.append("  *NOTE: Channel is undervalued by Last Click (common for offline).*")
        elif diff < -0.5: 
            lines.append("  *NOTE: Channel is overvalued by Last Click.*")
    else:
        lines.append("\n### MTA Analysis: Not available")
        
    return "\n".join(lines)


def _get_offline_context(channel: str, anomaly: dict) -> str:
    """Generate offline-specific context based on channel type."""
    channel_lower = channel.lower()
    
    contexts = {
        "tv": """### TV-Specific Considerations
- Check for pre-emptions or make-good credits owed
- Verify GRP delivery against contracted rates
- Consider daypart mix changes
- Review competitive share of voice in key markets""",
        
        "podcast": """### Podcast-Specific Considerations
- Attribution window is typically 14-30 days
- Check host-read vs. programmatic mix
- Verify download metrics vs. listener estimates
- Consider category saturation (many podcast listeners overlap)""",
        
        "radio": """### Radio-Specific Considerations
- Check for format changes at key stations
- Verify reach/frequency delivery
- Consider streaming radio cannibalization
- Review drive-time vs. midday mix""",
        
        "direct_mail": """### Direct Mail-Specific Considerations
- Check delivery timing and postal delays
- Verify list quality and suppression accuracy
- Consider response lag (typically 2-4 weeks)
- Review creative fatigue on recurring campaigns""",
        
        "ooh": """### Out-of-Home Specific Considerations
- Check for construction or visibility issues at units
- Verify traffic count data accuracy
- Consider weather impacts on pedestrian traffic
- Review digital vs. static unit mix""",
        
        "events": """### Events-Specific Considerations
- Review attendance vs. projections
- Check lead quality and follow-up conversion
- Consider post-event content amplification
- Verify sponsorship placement visibility""",
    }
    
    return contexts.get(channel_lower, """### Offline Channel Considerations
- Attribution is typically modeled, not directly tracked
- Consider 4-8 week lag for brand lift impact
- Check vendor-reported vs. third-party measurement discrepancies""")
