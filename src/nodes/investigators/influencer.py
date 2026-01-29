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
    
    Uses Tier 1 (Flash) model for initial analysis.
    """
    print("\n🎯 Investigating Influencer Campaign...")
    
    anomaly = state.get("selected_anomaly")
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
    
    # Package raw evidence
    raw_evidence = {
        "channel": "influencer",
        "anomaly": anomaly,
        "campaign_data": campaign_data,
        "creator_history": creator_history,
        "attribution_data": attribution_data,
    }
    
    # Generate investigation using LLM
    try:
        llm = get_llm_safe("tier1")
        
        prompt = format_influencer_prompt(
            anomaly=anomaly,
            campaign_data=campaign_data,
            creator_history=creator_history,
            attribution_data=attribution_data,
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
    
    # Group by campaign
    campaigns = df.groupby("campaign_id").agg({
        "contract_value": "sum",
        "impressions": "sum",
        "engagements": "sum",
        "conversions": "sum",
    }).reset_index()
    
    for _, row in campaigns.iterrows():
        eng_rate = row["engagements"] / max(row["impressions"], 1) * 100
        cpe = row["contract_value"] / max(row["engagements"], 1)
        lines.append(
            f"- {row['campaign_id']}: ${row['contract_value']:.0f} spend, "
            f"{eng_rate:.2f}% eng rate, ${cpe:.2f} CPE"
        )
    
    return "\n".join(lines)


def _summarize_creators(df) -> str:
    """Summarize creator performance."""
    if df.empty:
        return "No creator data available"
    
    lines = []
    for _, row in df.iterrows():
        eng_rate = row.get("engagements", 0) / max(row.get("impressions", 1), 1) * 100
        lines.append(
            f"- {row.get('creator_name', 'Unknown')} ({row.get('platform', 'unknown')}): "
            f"{eng_rate:.2f}% avg engagement, {int(row.get('conversions', 0))} conversions"
        )
    
    return "\n".join(lines[:10])  # Limit to top 10


def _format_attribution(attribution: dict) -> str:
    """Format attribution analysis results."""
    if not attribution:
        return "No attribution data"
    
    return f"""
Attribution Analysis for {attribution.get('campaign_id', 'Unknown')}:
- Total Spend: ${attribution.get('total_spend', 0):.2f}
- Total Conversions: {attribution.get('total_conversions', 0)}
- Observed Conversion Rate: {attribution.get('observed_conversion_rate', 0):.4f}
- Baseline Rate: {attribution.get('baseline_conversion_rate', 0):.4f}
- Incremental Lift: {attribution.get('incremental_lift_pct', 0):.1f}%
- Statistical Significance: {attribution.get('statistical_significance', 0):.2%}
"""
