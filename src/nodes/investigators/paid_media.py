"""Paid Media Investigator Node - Analyzes Google, Meta, TikTok anomalies."""
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.investigator import (
    PAID_MEDIA_SYSTEM_PROMPT,
    format_paid_media_prompt,
)


def investigate_paid_media(state: ExpeditionState) -> dict:
    """
    Paid Media Investigator Node.
    
    Gathers evidence from paid media channels and generates
    initial root cause hypotheses.
    
    Uses Tier 1 (Flash) model for speed.
    """
    print("\n🔬 Investigating Paid Media...")
    
    anomaly = state.get("selected_anomaly")
    if not anomaly:
        return {
            "investigation_evidence": None,
            "investigation_summary": "No anomaly to investigate",
            "current_node": "investigate_paid_media",
        }
    
    channel = anomaly.get("channel", "unknown")
    
    # Gather evidence from data layer
    marketing = get_marketing_data()
    
    # Get recent performance
    performance_df = marketing.get_channel_performance(channel, days=14)
    if performance_df.empty:
        performance_summary = "No performance data available"
    else:
        performance_summary = _summarize_performance(performance_df)
    
    # Get campaign breakdown
    campaign_df = marketing.get_campaign_breakdown(channel, days=14)
    if campaign_df.empty:
        campaign_breakdown = "No campaign breakdown available"
    else:
        campaign_breakdown = _summarize_campaigns(campaign_df)
    
    # Package raw evidence (for Critic node later)
    raw_evidence = {
        "channel": channel,
        "anomaly": anomaly,
        "performance_summary": performance_summary,
        "campaign_breakdown": campaign_breakdown,
        "recent_metrics": performance_df.tail(7).to_dict() if not performance_df.empty else {},
    }
    
    # Generate investigation using LLM
    try:
        llm = get_llm_safe("tier1")
        
        prompt = format_paid_media_prompt(
            anomaly=anomaly,
            performance_summary=performance_summary,
            campaign_breakdown=campaign_breakdown,
        )
        
        messages = [
            {"role": "system", "content": PAID_MEDIA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        investigation_summary = response.content
        
        print(f"  ✅ Investigation complete for {channel}")
        
    except Exception as e:
        print(f"  ⚠️ LLM investigation failed: {e}")
        investigation_summary = f"Investigation error: {str(e)}"
    
    return {
        "investigation_evidence": raw_evidence,
        "investigation_summary": investigation_summary,
        "current_node": "investigate_paid_media",
    }


def _summarize_performance(df) -> str:
    """Create a text summary of performance data."""
    lines = []
    
    # Calculate trends
    for metric in ["spend", "cpa", "roas", "conversions"]:
        if metric in df.columns:
            recent_avg = df[metric].tail(3).mean()
            prior_avg = df[metric].head(len(df) - 3).mean()
            
            if prior_avg > 0:
                change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
                trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
                lines.append(f"- {metric.upper()}: {recent_avg:.2f} ({trend} {change_pct:+.1f}% vs prior)")
    
    return "\n".join(lines) if lines else "No metrics available"


def _summarize_campaigns(df) -> str:
    """Create a text summary of campaign breakdown."""
    if df.empty:
        return "No campaign data"
    
    # Group by campaign
    summary = df.groupby("campaign_name").agg({
        "spend": "sum",
        "conversions": "sum",
    }).reset_index()
    
    lines = []
    for _, row in summary.iterrows():
        cpa = row["spend"] / max(row["conversions"], 1)
        lines.append(f"- {row['campaign_name']}: ${row['spend']:.0f} spend, {int(row['conversions'])} conv, ${cpa:.2f} CPA")
    
    return "\n".join(lines)
