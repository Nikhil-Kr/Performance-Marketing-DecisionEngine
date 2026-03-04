# """Influencer Investigator Node."""
# from datetime import datetime, timedelta
# import pandas as pd
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_influencer_data
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.investigator import (
#     INFLUENCER_SYSTEM_PROMPT,
#     format_influencer_prompt
# )


# def investigate_influencer(state: ExpeditionState) -> dict:
#     """
#     Investigates anomalies in influencer/creator campaigns.
    
#     Uses the analysis date range from state (user-selected) to ensure
#     all data fetching and context is bounded appropriately.
#     """
#     print("\n🔬 Investigating Influencer...")
    
#     anomaly = state.get("selected_anomaly")
#     if not anomaly:
#         return {
#             "investigation_summary": "No anomaly selected.",
#             "current_node": "investigate_influencer"
#         }

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

#     print(f"  📅 Analysis Period: {analysis_start.strftime('%Y-%m-%d')} to {analysis_end.strftime('%Y-%m-%d')}")

#     # 1. Get Influencer Data
#     influencer = get_influencer_data()
    
#     creator_name = anomaly.get("entity")  # Creator Name
    
#     # Get all posts for this creator
#     all_campaigns = influencer.get_campaign_performance()
    
#     # Filter for this creator
#     creator_data = all_campaigns[all_campaigns["creator_name"] == creator_name].copy()
    
#     # The specific post that flagged the anomaly (within analysis window)
#     current_post = creator_data[
#         (creator_data["post_date"] <= pd.Timestamp(analysis_end)) &
#         (creator_data["post_date"] >= pd.Timestamp(analysis_start))
#     ].sort_values("post_date", ascending=False).head(1)
    
#     # History strictly BEFORE the analysis end date (for baseline context)
#     history = creator_data[
#         creator_data["post_date"] < pd.Timestamp(analysis_end)
#     ].sort_values("post_date", ascending=False).head(5)
    
#     # 2. Format Data for LLM
#     campaign_str = current_post.to_markdown(index=False) if not current_post.empty else "No campaign data found for this period."
#     history_str = history.to_markdown(index=False) if not history.empty else "No prior history found."
    
#     # Mock Attribution (Tier 4)
#     attribution_str = f"MTA Analysis: {creator_name} has a historical 1.5x lift multiplier on organic search traffic."

#     # 3. Format Prompt (includes analysis period context)
#     prompt = format_influencer_prompt(
#         anomaly=anomaly,
#         campaign_data=campaign_str,
#         creator_history=history_str,
#         attribution_data=attribution_str,
#         analysis_start=analysis_start.strftime('%Y-%m-%d'),
#         analysis_end=analysis_end.strftime('%Y-%m-%d'),
#     )
    
#     # 4. Call LLM
#     try:
#         llm = get_llm_safe("tier1")
#         messages = [
#             {"role": "system", "content": INFLUENCER_SYSTEM_PROMPT},
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
#         "current_node": "investigate_influencer"
#     }

## <--------- Updated - 3/3 --------->
"""Influencer Causal Analyst Node - Analyzes creator/influencer anomalies."""
from src.schemas.state import ExpeditionState
from src.data_layer import get_influencer_data
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.investigator import (
    INFLUENCER_SYSTEM_PROMPT,
    format_influencer_prompt,
)


def investigate_influencer(state: ExpeditionState) -> dict:
    """
    Influencer Causal Analyst Node.
    
    Specialized investigator for creator/influencer campaigns.
    Focuses on:
    - Creator performance analysis
    - Platform-specific metrics
    - Causal/incremental impact assessment
    - Attribution quality
    
    Now includes cross-channel correlation context (Improvement #2).
    Uses Tier 1 (Flash) model for initial analysis.
    """
    print("\n🎯 Investigating Influencer Campaign...")
    
    anomaly = state.get("selected_anomaly")
    correlated = state.get("correlated_anomalies", [])
    
    if not anomaly:
        return {
            "investigation_evidence": None,
            "investigation_summary": "No anomaly to investigate",
            "current_node": "investigate_influencer",
        }
    
    # Gather evidence from influencer data
    influencer = get_influencer_data()
    
    # Get campaign performance
    campaign_df = influencer.get_campaign_performance()
    campaign_data = _summarize_campaigns(campaign_df)
    
    # Get creator performance
    creator_df = influencer.get_creator_performance()
    creator_history = _summarize_creators(creator_df)
    
    # Get attribution analysis (mock causal data)
    if not campaign_df.empty:
        campaign_id = campaign_df["campaign_id"].iloc[0]
        attribution = influencer.get_attribution_analysis(campaign_id)
        attribution_data = _format_attribution(attribution)
    else:
        attribution_data = "No attribution data available"
    
    # Cross-channel correlation context (Improvement #2)
    correlation_context = ""
    if correlated:
        correlation_context = _format_correlation_context(correlated)
    
    # Package raw evidence
    raw_evidence = {
        "channel": "influencer",
        "anomaly": anomaly,
        "campaign_data": campaign_data,
        "creator_history": creator_history,
        "attribution_data": attribution_data,
        "correlation_context": correlation_context,
    }
    
    # Generate investigation using LLM
    try:
        llm = get_llm_safe("tier1")
        
        prompt = format_influencer_prompt(
            anomaly=anomaly,
            campaign_data=campaign_data,
            creator_history=creator_history,
            attribution_data=attribution_data,
            correlation_context=correlation_context,
        )
        
        messages = [
            {"role": "system", "content": INFLUENCER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        investigation_summary = response.content
        
        print("  ✅ Influencer investigation complete")
        
    except Exception as e:
        print(f"  ⚠️ LLM investigation failed: {e}")
        investigation_summary = f"Investigation error: {str(e)}"
    
    return {
        "investigation_evidence": raw_evidence,
        "investigation_summary": investigation_summary,
        "current_node": "investigate_influencer",
    }


def _summarize_campaigns(df) -> str:
    """Summarize influencer campaign data."""
    if df.empty:
        return "No campaign data available"
    
    lines = []
    for _, row in df.head(10).iterrows():
        lines.append(
            f"- {row.get('creator_name', 'Unknown')} ({row.get('platform', 'unknown')}): "
            f"${row.get('contract_value', 0):,.0f} spend, "
            f"{int(row.get('impressions', 0)):,} impressions, "
            f"{int(row.get('engagements', 0)):,} engagements"
        )
    
    return "\n".join(lines)


def _summarize_creators(df) -> str:
    """Summarize creator-level performance."""
    if df.empty:
        return "No creator data available"
    
    lines = []
    for _, row in df.iterrows():
        eng_rate = row.get("engagements", 0) / max(row.get("impressions", 1), 1) * 100
        lines.append(
            f"- {row.get('creator_name', 'Unknown')} ({row.get('platform', 'unknown')}): "
            f"Engagement Rate: {eng_rate:.2f}%, "
            f"{int(row.get('conversions', 0))} conversions"
        )
    
    return "\n".join(lines)


def _format_attribution(attribution: dict) -> str:
    """Format attribution analysis data."""
    if not attribution:
        return "No attribution data"
    
    return f"""Attribution Analysis:
- Total Spend: ${attribution.get('total_spend', 0):,.2f}
- Total Conversions: {attribution.get('total_conversions', 0)}
- Observed Conv Rate: {attribution.get('observed_conversion_rate', 0):.4f}
- Baseline Conv Rate: {attribution.get('baseline_conversion_rate', 0):.4f}
- Incremental Lift: {attribution.get('incremental_lift_pct', 0):.1f}%
- Statistical Significance: {attribution.get('statistical_significance', 0):.2f}"""


def _format_correlation_context(correlated: list[dict]) -> str:
    """Format cross-channel correlations."""
    lines = ["\n## Cross-Channel Correlations"]
    lines.append("The following anomalies were detected simultaneously:\n")
    
    for c in correlated[:3]:
        reasons = ", ".join(c.get("correlation_reasons", []))
        lines.append(
            f"- **{c.get('channel', 'unknown')}** {c.get('metric', '')} "
            f"{c.get('direction', '')} {c.get('deviation_pct', 0):+.1f}% "
            f"(correlation: {reasons})"
        )
    
    return "\n".join(lines)
