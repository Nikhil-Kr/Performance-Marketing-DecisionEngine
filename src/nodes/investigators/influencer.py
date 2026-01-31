"""Influencer Investigator Node."""
from datetime import datetime, timedelta
import pandas as pd
from src.schemas.state import ExpeditionState
from src.data_layer import get_influencer_data
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.investigator import (
    INFLUENCER_SYSTEM_PROMPT,
    format_influencer_prompt
)


def investigate_influencer(state: ExpeditionState) -> dict:
    """
    Investigates anomalies in influencer/creator campaigns.
    
    Uses the analysis date range from state (user-selected) to ensure
    all data fetching and context is bounded appropriately.
    """
    print("\n🔬 Investigating Influencer...")
    
    anomaly = state.get("selected_anomaly")
    if not anomaly:
        return {
            "investigation_summary": "No anomaly selected.",
            "current_node": "investigate_influencer"
        }

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

    print(f"  📅 Analysis Period: {analysis_start.strftime('%Y-%m-%d')} to {analysis_end.strftime('%Y-%m-%d')}")

    # 1. Get Influencer Data
    influencer = get_influencer_data()
    
    creator_name = anomaly.get("entity")  # Creator Name
    
    # Get all posts for this creator
    all_campaigns = influencer.get_campaign_performance()
    
    # Filter for this creator
    creator_data = all_campaigns[all_campaigns["creator_name"] == creator_name].copy()
    
    # The specific post that flagged the anomaly (within analysis window)
    current_post = creator_data[
        (creator_data["post_date"] <= pd.Timestamp(analysis_end)) &
        (creator_data["post_date"] >= pd.Timestamp(analysis_start))
    ].sort_values("post_date", ascending=False).head(1)
    
    # History strictly BEFORE the analysis end date (for baseline context)
    history = creator_data[
        creator_data["post_date"] < pd.Timestamp(analysis_end)
    ].sort_values("post_date", ascending=False).head(5)
    
    # 2. Format Data for LLM
    campaign_str = current_post.to_markdown(index=False) if not current_post.empty else "No campaign data found for this period."
    history_str = history.to_markdown(index=False) if not history.empty else "No prior history found."
    
    # Mock Attribution (Tier 4)
    attribution_str = f"MTA Analysis: {creator_name} has a historical 1.5x lift multiplier on organic search traffic."

    # 3. Format Prompt (includes analysis period context)
    prompt = format_influencer_prompt(
        anomaly=anomaly,
        campaign_data=campaign_str,
        creator_history=history_str,
        attribution_data=attribution_str,
        analysis_start=analysis_start.strftime('%Y-%m-%d'),
        analysis_end=analysis_end.strftime('%Y-%m-%d'),
    )
    
    # 4. Call LLM
    try:
        llm = get_llm_safe("tier1")
        messages = [
            {"role": "system", "content": INFLUENCER_SYSTEM_PROMPT},
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
        "current_node": "investigate_influencer"
    }