"""Shared utilities for investigator nodes."""
from datetime import datetime, timedelta
from src.data_layer import get_market_data, get_strategy_data


def extract_analysis_dates(state: dict, anomaly: dict) -> tuple[datetime, datetime]:
    """
    Extract analysis start/end dates from state with fallbacks.
    Priority: state dates > anomaly detected_at > now.
    Returns (analysis_start, analysis_end).
    """
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

    return analysis_start, analysis_end


def fetch_market_context(channel: str, analysis_end: datetime, analysis_days: int) -> dict:
    """
    Fetch market intelligence and strategy context for a channel.
    Returns dict with formatted strings and raw MMM/MTA dicts.
    """
    market = get_market_data()
    competitors = market.get_competitor_signals(channel, reference_date=analysis_end)
    trends = market.get_market_interest(days=analysis_days, end_date=analysis_end)

    strategy = get_strategy_data()
    mmm = strategy.get_mmm_guardrails(channel, reference_date=analysis_end)
    mta = strategy.get_mta_comparison(channel, reference_date=analysis_end)

    return {
        "competitor_intel": format_competitors(competitors),
        "market_trends": format_trends(trends),
        "strategy_context": format_strategy(mmm, mta),
        "mmm": mmm,
        "mta": mta,
    }


def format_competitors(signals: list) -> str:
    """Format competitor signals for prompt inclusion."""
    if not signals:
        return "No significant competitor activity detected in this period."
    lines = [
        f"- {s.get('date')}: {s.get('competitor')} ({s.get('activity_type')}) - {s.get('details')}"
        for s in signals
    ]
    return "\n".join(lines)


def format_trends(trends: list) -> str:
    """Format market trends for prompt inclusion."""
    if not trends:
        return "No market trend data available."
    recent = trends[-5:]
    lines = [f"- {t.get('date')}: Interest Score {t.get('interest_score')}" for t in recent]
    return "\n".join(lines)


def format_strategy(mmm: dict, mta: dict) -> str:
    """Format MMM/MTA strategy context for prompt inclusion."""
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


def format_correlation_context(correlated: list) -> str:
    """Format cross-channel correlations for investigator prompts."""
    if not correlated:
        return ""
    lines = ["\n## Cross-Channel Correlations"]
    lines.append("The following anomalies were detected simultaneously and may share a root cause:\n")
    for c in correlated[:3]:
        reasons = ", ".join(c.get("correlation_reasons", []))
        lines.append(
            f"- **{c.get('channel', 'unknown')}** {c.get('metric', '')} "
            f"{c.get('direction', '')} {c.get('deviation_pct', 0):+.1f}% "
            f"(correlation: {reasons})"
        )
    lines.append("\nConsider whether a shared root cause explains multiple channels.")
    return "\n".join(lines)
