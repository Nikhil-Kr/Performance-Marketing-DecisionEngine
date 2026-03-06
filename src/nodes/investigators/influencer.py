"""Influencer Causal Analyst Node - Analyzes creator/influencer anomalies."""
import pandas as pd
from src.schemas.state import ExpeditionState
from src.data_layer import get_influencer_data
from src.intelligence.models import get_llm_safe, extract_content
from src.intelligence.prompts.investigator import (
    INFLUENCER_SYSTEM_PROMPT,
    format_influencer_prompt,
)
from src.nodes.investigators.utils import extract_analysis_dates, format_correlation_context
from src.utils.logging import get_logger

logger = get_logger("investigator.influencer")


def investigate_influencer(state: ExpeditionState) -> dict:
    """
    Influencer Causal Analyst Node.

    Specialized investigator for creator/influencer campaigns. Now respects the
    analysis date range selected in the UI (P4: time-travel), filtering creator
    posts to the analysis window and passing analysis_start/analysis_end to the prompt.

    Uses Tier 1 (Flash) model for initial analysis.
    """
    logger.info("Investigating Influencer Campaign...")

    anomaly = state.get("selected_anomaly")
    correlated = state.get("correlated_anomalies", [])

    if not anomaly:
        return {
            "investigation_evidence": None,
            "investigation_summary": "No anomaly to investigate",
            "current_node": "investigate_influencer",
        }

    # --- Resolve analysis date range (P4: time-travel) ---
    analysis_start, analysis_end = extract_analysis_dates(state, anomaly)

    logger.info("Analysis Period: %s to %s", analysis_start.strftime('%Y-%m-%d'), analysis_end.strftime('%Y-%m-%d'))

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
    correlation_context = format_correlation_context(correlated) if correlated else ""

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
        investigation_summary = extract_content(response)
        logger.info("Influencer investigation complete")

    except Exception as e:
        logger.error("LLM investigation failed: %s", e, exc_info=True)
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
