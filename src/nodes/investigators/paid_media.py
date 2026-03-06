"""Paid Media Investigator Node - Analyzes Google, Meta, TikTok anomalies."""
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data
from src.intelligence.models import get_llm_safe, extract_content
from src.intelligence.prompts.investigator import (
    PAID_MEDIA_SYSTEM_PROMPT,
    format_paid_media_prompt,
)
from src.nodes.investigators.utils import extract_analysis_dates, fetch_market_context
from src.utils.logging import get_logger

logger = get_logger("investigator.paid_media")


def investigate_paid_media(state: ExpeditionState) -> dict:
    """
    Paid Media Investigator Node.

    Gathers evidence from paid media channels (performance, campaign breakdown,
    quality signals) plus market intelligence (competitors, trends) and strategy
    context (MMM saturation, MTA comparison). Respects the analysis date range
    selected in the UI for time-travel analysis.

    Uses Tier 1 (Flash) model for speed.
    """
    logger.info("Investigating Paid Media...")

    anomaly = state.get("selected_anomaly")
    if not anomaly:
        return {
            "investigation_evidence": None,
            "investigation_summary": "No anomaly to investigate",
            "current_node": "investigate_paid_media",
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
    campaign_df = marketing.get_campaign_breakdown(channel, days=lookback_days, end_date=analysis_end)

    performance_summary = (
        _summarize_performance(performance_df) if not performance_df.empty
        else "No performance data available"
    )
    campaign_breakdown = (
        _summarize_campaigns(campaign_df) if not campaign_df.empty
        else "No campaign breakdown available"
    )

    # Append quality/fraud signals inline with performance
    quality_signals = _get_quality_signals(performance_df, channel)
    if quality_signals:
        performance_summary += f"\n\n## Traffic Quality Signals\n{quality_signals}"

    # --- 2. Market intelligence + strategy context (time-travel enabled) ---
    market_ctx = fetch_market_context(channel, analysis_end, analysis_days)
    competitor_intel = market_ctx["competitor_intel"]
    market_trends = market_ctx["market_trends"]
    strategy_context = market_ctx["strategy_context"]

    # --- Package raw evidence ---
    raw_evidence = {
        "channel": channel,
        "anomaly": anomaly,
        "performance_summary": performance_summary,
        "campaign_breakdown": campaign_breakdown,
        "competitor_intel": competitor_intel,
        "market_trends": market_trends,
        "strategy_context": strategy_context,
        "recent_metrics": performance_df.tail(7).to_dict() if not performance_df.empty else {},
        "analysis_start": analysis_start.strftime("%Y-%m-%d"),
        "analysis_end": analysis_end.strftime("%Y-%m-%d"),
    }

    # --- 4. Build prompt and call LLM ---
    try:
        llm = get_llm_safe("tier1")

        prompt = format_paid_media_prompt(
            anomaly=anomaly,
            performance_summary=performance_summary,
            campaign_breakdown=campaign_breakdown,
            competitor_intel=competitor_intel,
            market_trends=market_trends,
            strategy_context=strategy_context,
            analysis_start=analysis_start.strftime("%Y-%m-%d"),
            analysis_end=analysis_end.strftime("%Y-%m-%d"),
        )

        messages = [
            {"role": "system", "content": PAID_MEDIA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = llm.invoke(messages)
        investigation_summary = extract_content(response)
        logger.info("Investigation complete for %s", channel)

    except Exception as e:
        logger.error("LLM investigation failed: %s", e, exc_info=True)
        investigation_summary = f"Investigation error: {str(e)}"

    return {
        "investigation_evidence": raw_evidence,
        "investigation_summary": investigation_summary,
        "current_node": "investigate_paid_media",
    }


def _summarize_performance(df) -> str:
    """Create a text summary of performance data."""
    lines = []
    for metric in ["spend", "cpa", "roas", "conversions"]:
        if metric in df.columns:
            recent_avg = df[metric].tail(3).mean()
            prior_avg = df[metric].head(len(df) - 3).mean()
            if prior_avg > 0:
                change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
                trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
                lines.append(f"- {metric.upper()}: {recent_avg:.2f} ({trend} {change_pct:+.1f}% vs prior)")
    return "\n".join(lines) if lines else "No metrics available"


def _get_quality_signals(df, channel: str) -> str:
    """Extract channel-specific quality/fraud signals when available."""
    if df.empty:
        return ""

    signals = []

    if channel == "programmatic":
        fraud_cols = ["ivt_rate", "suspicious_click_pct", "geo_anomaly_score", "new_domain_pct"]
        available = [c for c in fraud_cols if c in df.columns]
        if available:
            signals.append("### Fraud / Invalid Traffic (IVT) Indicators")
            for col in available:
                recent = df[col].tail(3).mean()
                baseline = df[col].head(len(df) - 3).mean()
                if baseline > 0:
                    change = ((recent - baseline) / baseline) * 100
                    trend = "🚨" if change > 100 else "⚠️" if change > 50 else "→"
                    label = col.replace("_", " ").title()
                    signals.append(
                        f"- {label}: {recent:.1%} recent vs {baseline:.1%} baseline "
                        f"({trend} {change:+.0f}% change)"
                    )
            ivt_recent = df["ivt_rate"].tail(3).mean() if "ivt_rate" in df.columns else 0
            susp_recent = df["suspicious_click_pct"].tail(3).mean() if "suspicious_click_pct" in df.columns else 0
            if ivt_recent > 0.20 or susp_recent > 0.20:
                signals.append(
                    "\n⚠️ CRITICAL: IVT rate and suspicious click percentage are "
                    "significantly above industry norms (typically <5%). This strongly "
                    "suggests bot traffic or click fraud on low-quality inventory."
                )

    elif channel == "affiliate":
        partner_cols = ["avg_order_value", "coupon_usage_rate", "unique_referral_domains", "new_customer_pct"]
        available = [c for c in partner_cols if c in df.columns]
        if available:
            signals.append("### Partner & Coupon Quality Indicators")
            for col in available:
                recent = df[col].tail(4).mean()
                baseline = df[col].head(len(df) - 4).mean()
                if baseline > 0:
                    change = ((recent - baseline) / baseline) * 100
                    trend = "🚨" if abs(change) > 100 else "⚠️" if abs(change) > 50 else "→"
                    label = col.replace("_", " ").title()
                    if col == "avg_order_value":
                        signals.append(
                            f"- {label}: ${recent:.2f} recent vs ${baseline:.2f} baseline "
                            f"({trend} {change:+.0f}% change)"
                        )
                    elif col == "unique_referral_domains":
                        signals.append(
                            f"- {label}: {recent:.0f} recent vs {baseline:.0f} baseline "
                            f"({trend} {change:+.0f}% change)"
                        )
                    else:
                        signals.append(
                            f"- {label}: {recent:.1%} recent vs {baseline:.1%} baseline "
                            f"({trend} {change:+.0f}% change)"
                        )
            aov_recent = df["avg_order_value"].tail(4).mean() if "avg_order_value" in df.columns else 50
            coupon_recent = df["coupon_usage_rate"].tail(4).mean() if "coupon_usage_rate" in df.columns else 0.1
            if aov_recent < 25 and coupon_recent > 0.70:
                signals.append(
                    "\n⚠️ CRITICAL: Average order value has collapsed while coupon "
                    "usage rate spiked to near-100%. This pattern strongly indicates "
                    "coupon code leakage to discount aggregator sites."
                )

    return "\n".join(signals) if signals else ""


def _summarize_campaigns(df) -> str:
    """Create a text summary of campaign breakdown."""
    if df.empty:
        return "No campaign data"
    summary = df.groupby("campaign_name").agg({"spend": "sum", "conversions": "sum"}).reset_index()
    lines = []
    for _, row in summary.iterrows():
        cpa = row["spend"] / max(row["conversions"], 1)
        lines.append(f"- {row['campaign_name']}: ${row['spend']:.0f} spend, {int(row['conversions'])} conv, ${cpa:.2f} CPA")
    return "\n".join(lines)
