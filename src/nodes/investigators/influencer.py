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

## <--------- V3 - Cross-Channel Correlation, No Date Range (Previous Active) --------->

# ## <--------- Updated - 3/3 --------->
# """Influencer Causal Analyst Node - V3 had no date range awareness, no analysis_start/end in prompt."""
# def investigate_influencer(state) -> dict: ...  (fetches all data, not date-bounded)
# def _summarize_campaigns(df): ...
# def _summarize_creators(df): ...
# def _format_attribution(attribution): ...
# def _format_correlation_context(correlated): ...

## <--------- V4 - Date Range Restored (P4) --------->

"""Influencer Causal Analyst Node - Analyzes creator/influencer anomalies."""
import pandas as pd
from datetime import datetime, timedelta
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

    Specialized investigator for creator/influencer campaigns. Now respects the
    analysis date range selected in the UI (P4: time-travel), filtering creator
    posts to the analysis window and passing analysis_start/analysis_end to the prompt.

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

    print(f"  📅 Analysis Period: {analysis_start.strftime('%Y-%m-%d')} to {analysis_end.strftime('%Y-%m-%d')}")

    # --- Gather influencer data (date-bounded) ---
    influencer = get_influencer_data()
    creator_name = anomaly.get("entity")

    all_campaigns = influencer.get_campaign_performance()

    # Filter to this creator if we know their name
    if creator_name and not all_campaigns.empty and "creator_name" in all_campaigns.columns:
        creator_data = all_campaigns[all_campaigns["creator_name"] == creator_name].copy()
    else:
        creator_data = all_campaigns.copy()

    # Posts within the analysis window (current anomaly context)
    if not creator_data.empty and "post_date" in creator_data.columns:
        current_posts = creator_data[
            (creator_data["post_date"] <= pd.Timestamp(analysis_end)) &
            (creator_data["post_date"] >= pd.Timestamp(analysis_start))
        ].sort_values("post_date", ascending=False).head(5)

        # History strictly before the analysis window (for baseline)
        history_posts = creator_data[
            creator_data["post_date"] < pd.Timestamp(analysis_start)
        ].sort_values("post_date", ascending=False).head(5)
    else:
        current_posts = creator_data.head(5)
        history_posts = creator_data.tail(5)

    campaign_data = (
        current_posts.to_markdown(index=False) if not current_posts.empty
        else "No campaign data found for this analysis period."
    )
    creator_history = (
        history_posts.to_markdown(index=False) if not history_posts.empty
        else "No prior history found before analysis window."
    )

    # Attribution analysis
    creator_df = influencer.get_creator_performance()
    if not all_campaigns.empty and "campaign_id" in all_campaigns.columns:
        campaign_id = all_campaigns["campaign_id"].iloc[0]
        attribution = influencer.get_attribution_analysis(campaign_id)
        attribution_data = _format_attribution(attribution)
    else:
        attribution_data = "No attribution data available"

    # Correlation context
    correlation_context = _format_correlation_context(correlated) if correlated else ""

    # --- Package raw evidence ---
    raw_evidence = {
        "channel": "influencer",
        "anomaly": anomaly,
        "campaign_data": campaign_data,
        "creator_history": creator_history,
        "attribution_data": attribution_data,
        "correlation_context": correlation_context,
        "analysis_start": analysis_start.strftime("%Y-%m-%d"),
        "analysis_end": analysis_end.strftime("%Y-%m-%d"),
    }

    # --- Build prompt and call LLM ---
    try:
        llm = get_llm_safe("tier1")

        prompt = format_influencer_prompt(
            anomaly=anomaly,
            campaign_data=campaign_data,
            creator_history=creator_history,
            attribution_data=attribution_data,
            analysis_start=analysis_start.strftime("%Y-%m-%d"),
            analysis_end=analysis_end.strftime("%Y-%m-%d"),
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


def _format_attribution(attribution: dict) -> str:
    """Format attribution analysis data."""
    if not attribution:
        return "No attribution data"
    return (
        f"Attribution Analysis:\n"
        f"- Total Spend: ${attribution.get('total_spend', 0):,.2f}\n"
        f"- Total Conversions: {attribution.get('total_conversions', 0)}\n"
        f"- Observed Conv Rate: {attribution.get('observed_conversion_rate', 0):.4f}\n"
        f"- Baseline Conv Rate: {attribution.get('baseline_conversion_rate', 0):.4f}\n"
        f"- Incremental Lift: {attribution.get('incremental_lift_pct', 0):.1f}%\n"
        f"- Statistical Significance: {attribution.get('statistical_significance', 0):.2f}"
    )


def _format_correlation_context(correlated: list) -> str:
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
