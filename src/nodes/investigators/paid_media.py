# """Paid Media Investigator Node - Analyzes Google, Meta, TikTok anomalies."""
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_marketing_data
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.investigator import (
#     PAID_MEDIA_SYSTEM_PROMPT,
#     format_paid_media_prompt,
# )


# def investigate_paid_media(state: ExpeditionState) -> dict:
#     """
#     Paid Media Investigator Node.
    
#     Gathers evidence from paid media channels and generates
#     initial root cause hypotheses.
    
#     Uses Tier 1 (Flash) model for speed.
#     """
#     print("\n🔬 Investigating Paid Media...")
    
#     anomaly = state.get("selected_anomaly")
#     if not anomaly:
#         return {
#             "investigation_evidence": None,
#             "investigation_summary": "No anomaly to investigate",
#             "current_node": "investigate_paid_media",
#         }
    
#     channel = anomaly.get("channel", "unknown")
    
#     # Gather evidence from data layer
#     marketing = get_marketing_data()
    
#     # Get recent performance
#     performance_df = marketing.get_channel_performance(channel, days=14)
#     if performance_df.empty:
#         performance_summary = "No performance data available"
#     else:
#         performance_summary = _summarize_performance(performance_df)
    
#     # Get campaign breakdown
#     campaign_df = marketing.get_campaign_breakdown(channel, days=14)
#     if campaign_df.empty:
#         campaign_breakdown = "No campaign breakdown available"
#     else:
#         campaign_breakdown = _summarize_campaigns(campaign_df)
    
#     # Package raw evidence (for Critic node later)
#     raw_evidence = {
#         "channel": channel,
#         "anomaly": anomaly,
#         "performance_summary": performance_summary,
#         "campaign_breakdown": campaign_breakdown,
#         "recent_metrics": performance_df.tail(7).to_dict() if not performance_df.empty else {},
#     }
    
#     # Generate investigation using LLM
#     try:
#         llm = get_llm_safe("tier1")
        
#         prompt = format_paid_media_prompt(
#             anomaly=anomaly,
#             performance_summary=performance_summary,
#             campaign_breakdown=campaign_breakdown,
#         )
        
#         messages = [
#             {"role": "system", "content": PAID_MEDIA_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ]
        
#         response = llm.invoke(messages)
#         investigation_summary = response.content
        
#         print(f"  ✅ Investigation complete for {channel}")
        
#     except Exception as e:
#         print(f"  ⚠️ LLM investigation failed: {e}")
#         investigation_summary = f"Investigation error: {str(e)}"
    
#     return {
#         "investigation_evidence": raw_evidence,
#         "investigation_summary": investigation_summary,
#         "current_node": "investigate_paid_media",
#     }


# def _summarize_performance(df) -> str:
#     """Create a text summary of performance data."""
#     lines = []
    
#     # Calculate trends
#     for metric in ["spend", "cpa", "roas", "conversions"]:
#         if metric in df.columns:
#             recent_avg = df[metric].tail(3).mean()
#             prior_avg = df[metric].head(len(df) - 3).mean()
            
#             if prior_avg > 0:
#                 change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
#                 trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
#                 lines.append(f"- {metric.upper()}: {recent_avg:.2f} ({trend} {change_pct:+.1f}% vs prior)")
    
#     return "\n".join(lines) if lines else "No metrics available"


# def _summarize_campaigns(df) -> str:
#     """Create a text summary of campaign breakdown."""
#     if df.empty:
#         return "No campaign data"
    
#     # Group by campaign
#     summary = df.groupby("campaign_name").agg({
#         "spend": "sum",
#         "conversions": "sum",
#     }).reset_index()
    
#     lines = []
#     for _, row in summary.iterrows():
#         cpa = row["spend"] / max(row["conversions"], 1)
#         lines.append(f"- {row['campaign_name']}: ${row['spend']:.0f} spend, {int(row['conversions'])} conv, ${cpa:.2f} CPA")
    
#     return "\n".join(lines)

# # <----- TIER 3 & TIER 4 ---------->

# """Paid Media Investigator Node."""
# from datetime import datetime, timedelta
# import pandas as pd
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_marketing_data, get_market_data, get_strategy_data
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.investigator import PAID_MEDIA_SYSTEM_PROMPT, format_paid_media_prompt

# def investigate_paid_media(state: ExpeditionState) -> dict:
#     """
#     Investigates anomalies in paid media channels.
    
#     Uses the analysis date range from state (user-selected) to ensure
#     all data fetching and context is bounded appropriately.
#     """
#     print("\n🔬 Investigating Paid Media...")
    
#     anomaly = state.get("selected_anomaly")
#     if not anomaly:
#         return {"investigation_summary": "No anomaly selected."}

#     channel = anomaly.get("channel")
    
#     # EXTRACT ANALYSIS DATE RANGE FROM STATE (prioritize state over anomaly)
#     # This ensures we respect what the user selected in the UI
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
    
#     # 4. Format Prompt (includes analysis period context)
#     prompt = format_paid_media_prompt(
#         anomaly=anomaly,
#         performance_summary=performance.to_markdown(index=False) if not performance.empty else "No data available",
#         campaign_breakdown=breakdown.to_markdown(index=False) if not breakdown.empty else "No data available",
#         competitor_intel=competitor_text,
#         market_trends=trend_text,
#         strategy_context=strategy_text,
#         analysis_start=analysis_start.strftime('%Y-%m-%d'),
#         analysis_end=analysis_end.strftime('%Y-%m-%d'),
#     )
    
#     # 5. Call LLM
#     try:
#         llm = get_llm_safe("tier1")
#         messages = [
#             {"role": "system", "content": PAID_MEDIA_SYSTEM_PROMPT},
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
#         "current_node": "investigate_paid_media"
#     }


# def _format_competitors(signals: list) -> str:
#     if not signals: return "No significant competitor activity detected in this period."
#     lines = [f"- {s.get('date')}: {s.get('competitor')} ({s.get('activity_type')}) - {s.get('details')}" for s in signals]
#     return "\n".join(lines)

# def _format_trends(trends: list) -> str:
#     if not trends: return "No market trend data available."
#     recent = trends[-5:] # Show last 5 points leading up to the anomaly
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
#         if diff > 0.5: lines.append("  *NOTE: Channel is undervalued by Last Click.*")
#         elif diff < -0.5: lines.append("  *NOTE: Channel is overvalued by Last Click.*")
#     else:
#         lines.append("\n### MTA Analysis: Not available")
        
#     return "\n".join(lines)

## <--------- Updated - 3/3 --------->

# """Paid Media Investigator Node - Analyzes Google, Meta, TikTok anomalies."""
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_marketing_data
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.investigator import (
#     PAID_MEDIA_SYSTEM_PROMPT,
#     format_paid_media_prompt,
# )


# def investigate_paid_media(state: ExpeditionState) -> dict:
#     """
#     Paid Media Investigator Node.
    
#     Gathers evidence from paid media channels and generates
#     initial root cause hypotheses.
    
#     Now includes cross-channel correlation context (Improvement #2).
    
#     Uses Tier 1 (Flash) model for speed.
#     """
#     print("\n🔬 Investigating Paid Media...")
    
#     anomaly = state.get("selected_anomaly")
#     correlated = state.get("correlated_anomalies", [])
    
#     if not anomaly:
#         return {
#             "investigation_evidence": None,
#             "investigation_summary": "No anomaly to investigate",
#             "current_node": "investigate_paid_media",
#         }
    
#     channel = anomaly.get("channel", "unknown")
    
#     # Gather evidence from data layer
#     marketing = get_marketing_data()
    
#     # Get recent performance
#     performance_df = marketing.get_channel_performance(channel, days=14)
#     if performance_df.empty:
#         performance_summary = "No performance data available"
#     else:
#         performance_summary = _summarize_performance(performance_df)
    
#     # Get campaign breakdown
#     campaign_df = marketing.get_campaign_breakdown(channel, days=14)
#     if campaign_df.empty:
#         campaign_breakdown = "No campaign breakdown available"
#     else:
#         campaign_breakdown = _summarize_campaigns(campaign_df)
    
#     # Cross-channel correlation context (Improvement #2)
#     correlation_context = ""
#     if correlated:
#         correlation_context = _format_correlation_context(correlated)
    
#     # Package raw evidence (for Critic node later)
#     raw_evidence = {
#         "channel": channel,
#         "anomaly": anomaly,
#         "performance_summary": performance_summary,
#         "campaign_breakdown": campaign_breakdown,
#         "correlation_context": correlation_context,
#         "recent_metrics": performance_df.tail(7).to_dict() if not performance_df.empty else {},
#     }
    
#     # Generate investigation using LLM
#     try:
#         llm = get_llm_safe("tier1")
        
#         prompt = format_paid_media_prompt(
#             anomaly=anomaly,
#             performance_summary=performance_summary,
#             campaign_breakdown=campaign_breakdown,
#             correlation_context=correlation_context,
#         )
        
#         messages = [
#             {"role": "system", "content": PAID_MEDIA_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ]
        
#         response = llm.invoke(messages)
#         investigation_summary = response.content
        
#         print(f"  ✅ Investigation complete for {channel}")
        
#     except Exception as e:
#         print(f"  ⚠️ LLM investigation failed: {e}")
#         investigation_summary = f"Investigation error: {str(e)}"
    
#     return {
#         "investigation_evidence": raw_evidence,
#         "investigation_summary": investigation_summary,
#         "current_node": "investigate_paid_media",
#     }


# def _summarize_performance(df) -> str:
#     """Create a text summary of performance data."""
#     lines = []
    
#     # Calculate trends
#     for metric in ["spend", "cpa", "roas", "conversions"]:
#         if metric in df.columns:
#             recent_avg = df[metric].tail(3).mean()
#             prior_avg = df[metric].head(len(df) - 3).mean()
            
#             if prior_avg > 0:
#                 change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
#                 trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
#                 lines.append(f"- {metric.upper()}: {recent_avg:.2f} ({trend} {change_pct:+.1f}% vs prior)")
    
#     return "\n".join(lines) if lines else "No metrics available"


# def _summarize_campaigns(df) -> str:
#     """Create a text summary of campaign breakdown."""
#     if df.empty:
#         return "No campaign data"
    
#     # Group by campaign
#     summary = df.groupby("campaign_name").agg({
#         "spend": "sum",
#         "conversions": "sum",
#     }).reset_index()
    
#     lines = []
#     for _, row in summary.iterrows():
#         cpa = row["spend"] / max(row["conversions"], 1)
#         lines.append(f"- {row['campaign_name']}: ${row['spend']:.0f} spend, {int(row['conversions'])} conv, ${cpa:.2f} CPA")
    
#     return "\n".join(lines)


# def _format_correlation_context(correlated: list[dict]) -> str:
#     """Format cross-channel correlations for the investigator prompt."""
#     lines = ["\n## Cross-Channel Correlations"]
#     lines.append("The following anomalies were detected simultaneously and may share a root cause:\n")
    
#     for c in correlated[:3]:
#         reasons = ", ".join(c.get("correlation_reasons", []))
#         lines.append(
#             f"- **{c.get('channel', 'unknown')}** {c.get('metric', '')} "
#             f"{c.get('direction', '')} {c.get('deviation_pct', 0):+.1f}% "
#             f"(correlation: {reasons})"
#         )
    
#     lines.append("\nConsider whether a shared root cause (e.g., tracking failure, market event) explains multiple channels.")
#     return "\n".join(lines)

## <--------- V3 - Quality Signals Only (Previous Active) --------->

# # <------- Updated - 3/5 ------------->
#
# """Paid Media Investigator Node - Analyzes Google, Meta, TikTok anomalies."""
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_marketing_data
# from src.intelligence.models import get_llm_safe
# from src.intelligence.prompts.investigator import (
#     PAID_MEDIA_SYSTEM_PROMPT,
#     format_paid_media_prompt,
# )
#
#
# def investigate_paid_media(state: ExpeditionState) -> dict:
#     print("\n🔬 Investigating Paid Media...")
#     anomaly = state.get("selected_anomaly")
#     if not anomaly:
#         return {
#             "investigation_evidence": None,
#             "investigation_summary": "No anomaly to investigate",
#             "current_node": "investigate_paid_media",
#         }
#     channel = anomaly.get("channel", "unknown")
#     marketing = get_marketing_data()
#     performance_df = marketing.get_channel_performance(channel, days=14)
#     if performance_df.empty:
#         performance_summary = "No performance data available"
#     else:
#         performance_summary = _summarize_performance(performance_df)
#     campaign_df = marketing.get_campaign_breakdown(channel, days=14)
#     if campaign_df.empty:
#         campaign_breakdown = "No campaign breakdown available"
#     else:
#         campaign_breakdown = _summarize_campaigns(campaign_df)
#     quality_signals = _get_quality_signals(performance_df, channel)
#     raw_evidence = {
#         "channel": channel,
#         "anomaly": anomaly,
#         "performance_summary": performance_summary,
#         "campaign_breakdown": campaign_breakdown,
#         "recent_metrics": performance_df.tail(7).to_dict() if not performance_df.empty else {},
#     }
#     if quality_signals:
#         raw_evidence["quality_signals"] = quality_signals
#     full_performance_summary = performance_summary
#     if quality_signals:
#         full_performance_summary += f"\n\n## Traffic Quality Signals\n{quality_signals}"
#     try:
#         llm = get_llm_safe("tier1")
#         prompt = format_paid_media_prompt(
#             anomaly=anomaly,
#             performance_summary=full_performance_summary,
#             campaign_breakdown=campaign_breakdown,
#         )
#         messages = [
#             {"role": "system", "content": PAID_MEDIA_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt},
#         ]
#         response = llm.invoke(messages)
#         investigation_summary = response.content
#         print(f"  ✅ Investigation complete for {channel}")
#     except Exception as e:
#         print(f"  ⚠️ LLM investigation failed: {e}")
#         investigation_summary = f"Investigation error: {str(e)}"
#     return {
#         "investigation_evidence": raw_evidence,
#         "investigation_summary": investigation_summary,
#         "current_node": "investigate_paid_media",
#     }
#
#
# def _summarize_performance(df) -> str:
#     lines = []
#     for metric in ["spend", "cpa", "roas", "conversions"]:
#         if metric in df.columns:
#             recent_avg = df[metric].tail(3).mean()
#             prior_avg = df[metric].head(len(df) - 3).mean()
#             if prior_avg > 0:
#                 change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
#                 trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
#                 lines.append(f"- {metric.upper()}: {recent_avg:.2f} ({trend} {change_pct:+.1f}% vs prior)")
#     return "\n".join(lines) if lines else "No metrics available"
#
#
# def _get_quality_signals(df, channel: str) -> str:
#     if df.empty:
#         return ""
#     signals = []
#     if channel == "programmatic":
#         fraud_cols = ["ivt_rate", "suspicious_click_pct", "geo_anomaly_score", "new_domain_pct"]
#         available = [c for c in fraud_cols if c in df.columns]
#         if available:
#             signals.append("### Fraud / Invalid Traffic (IVT) Indicators")
#             for col in available:
#                 recent = df[col].tail(3).mean()
#                 baseline = df[col].head(len(df) - 3).mean()
#                 if baseline > 0:
#                     change = ((recent - baseline) / baseline) * 100
#                     trend = "🚨" if change > 100 else "⚠️" if change > 50 else "→"
#                     label = col.replace("_", " ").title()
#                     signals.append(f"- {label}: {recent:.1%} recent vs {baseline:.1%} baseline ({trend} {change:+.0f}% change)")
#             ivt_recent = df["ivt_rate"].tail(3).mean() if "ivt_rate" in df.columns else 0
#             susp_recent = df["suspicious_click_pct"].tail(3).mean() if "suspicious_click_pct" in df.columns else 0
#             if ivt_recent > 0.20 or susp_recent > 0.20:
#                 signals.append("\n⚠️ CRITICAL: IVT rate and suspicious click percentage are significantly above industry norms (typically <5%). This strongly suggests bot traffic or click fraud on low-quality inventory.")
#     elif channel == "affiliate":
#         partner_cols = ["avg_order_value", "coupon_usage_rate", "unique_referral_domains", "new_customer_pct"]
#         available = [c for c in partner_cols if c in df.columns]
#         if available:
#             signals.append("### Partner & Coupon Quality Indicators")
#             for col in available:
#                 recent = df[col].tail(4).mean()
#                 baseline = df[col].head(len(df) - 4).mean()
#                 if baseline > 0:
#                     change = ((recent - baseline) / baseline) * 100
#                     trend = "🚨" if abs(change) > 100 else "⚠️" if abs(change) > 50 else "→"
#                     label = col.replace("_", " ").title()
#                     if col in ["avg_order_value"]:
#                         signals.append(f"- {label}: ${recent:.2f} recent vs ${baseline:.2f} baseline ({trend} {change:+.0f}% change)")
#                     elif col in ["unique_referral_domains"]:
#                         signals.append(f"- {label}: {recent:.0f} recent vs {baseline:.0f} baseline ({trend} {change:+.0f}% change)")
#                     else:
#                         signals.append(f"- {label}: {recent:.1%} recent vs {baseline:.1%} baseline ({trend} {change:+.0f}% change)")
#             aov_recent = df["avg_order_value"].tail(4).mean() if "avg_order_value" in df.columns else 50
#             coupon_recent = df["coupon_usage_rate"].tail(4).mean() if "coupon_usage_rate" in df.columns else 0.1
#             if aov_recent < 25 and coupon_recent > 0.70:
#                 signals.append("\n⚠️ CRITICAL: Average order value has collapsed while coupon usage rate spiked to near-100%. This pattern strongly indicates coupon code leakage to discount aggregator sites.")
#     return "\n".join(signals) if signals else ""
#
#
# def _summarize_campaigns(df) -> str:
#     if df.empty:
#         return "No campaign data"
#     summary = df.groupby("campaign_name").agg({"spend": "sum", "conversions": "sum"}).reset_index()
#     lines = []
#     for _, row in summary.iterrows():
#         cpa = row["spend"] / max(row["conversions"], 1)
#         lines.append(f"- {row['campaign_name']}: ${row['spend']:.0f} spend, {int(row['conversions'])} conv, ${cpa:.2f} CPA")
#     return "\n".join(lines)

## <--------- V4 - Market + Strategy Intelligence + Date Range Restored --------->

"""Paid Media Investigator Node - Analyzes Google, Meta, TikTok anomalies."""
from datetime import datetime, timedelta
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data, get_market_data, get_strategy_data
from src.intelligence.models import get_llm_safe, extract_content
from src.intelligence.prompts.investigator import (
    PAID_MEDIA_SYSTEM_PROMPT,
    format_paid_media_prompt,
)


def investigate_paid_media(state: ExpeditionState) -> dict:
    """
    Paid Media Investigator Node.

    Gathers evidence from paid media channels (performance, campaign breakdown,
    quality signals) plus market intelligence (competitors, trends) and strategy
    context (MMM saturation, MTA comparison). Respects the analysis date range
    selected in the UI for time-travel analysis.

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
    strategy_context = _format_strategy(mmm, mta)

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
            lines.append("  *NOTE: Channel is undervalued by Last Click.*")
        elif diff < -0.5:
            lines.append("  *NOTE: Channel is overvalued by Last Click.*")
    else:
        lines.append("\n### MTA Analysis: Not available")

    return "\n".join(lines)