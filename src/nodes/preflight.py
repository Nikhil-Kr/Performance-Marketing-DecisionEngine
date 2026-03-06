"""Pre-Flight & Anomaly Detection Nodes."""
from datetime import datetime, timedelta
from collections import defaultdict
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data, get_influencer_data
from src.utils.logging import get_logger

logger = get_logger("preflight")


def preflight_check(state: ExpeditionState) -> dict:
    """
    Pre-Flight Check Node.
    
    Validates that all data sources are healthy and fresh before proceeding.
    """
    logger.info("Running Pre-Flight Check...")
    
    marketing = get_marketing_data()
    influencer = get_influencer_data()
    
    # Check data health
    marketing_healthy = marketing.is_healthy()
    influencer_healthy = influencer.is_healthy()
    
    if not marketing_healthy and not influencer_healthy:
        logger.error("All data sources unhealthy")
        return {
            "preflight_passed": False,
            "preflight_error": "No data sources available. Run 'make mock-data'.",
            "data_freshness": {},
            "current_node": "preflight",
        }
    
    # Check freshness
    freshness = {}
    if marketing_healthy:
        freshness.update(marketing.check_data_freshness())
    if influencer_healthy:
        freshness.update(influencer.check_data_freshness())
    
    # Convert to strings for state serialization
    freshness_str = {k: v.isoformat() if isinstance(v, datetime) else str(v) for k, v in freshness.items()}
    
    logger.info("Pre-flight passed (%d sources healthy)", len(freshness))
    
    return {
        "preflight_passed": True,
        "preflight_error": None,
        "data_freshness": freshness_str,
        "current_node": "preflight",
    }


def detect_anomalies(state: ExpeditionState) -> dict:
    """
    Anomaly Detection Node.
    
    Called after pre-flight passes to identify issues to investigate.
    Now includes cross-channel correlation (Improvement #2).
    """
    logger.info("Detecting anomalies...")
    
    # 1. PRIORITY CHECK: Did the user manually select an anomaly?
    # If app.py passed a 'selected_anomaly', we trust it and skip auto-detection.
    if state.get("selected_anomaly"):
        selected = state["selected_anomaly"]
        logger.info("User selected target: %s (%s)", selected.get('channel', 'unknown'), selected.get('metric', 'unknown'))
        
        # Even with user selection, run correlation to enrich context
        all_anomalies = state.get("anomalies", [selected])
        correlated = _find_correlations(all_anomalies, selected)
        
        return {
            "selected_anomaly": selected,
            "current_node": "detect_anomalies",
            "anomalies": all_anomalies,
            "correlated_anomalies": correlated,
        }

    # 2. AUTO-PILOT: No user selection, so we scan everything and pick the worst one.
    marketing = get_marketing_data()
    influencer = get_influencer_data()

    # Extract date range from state (set by UI date picker)
    analysis_start = state.get("analysis_start_date")
    analysis_end = state.get("analysis_end_date")
    if analysis_start and not isinstance(analysis_start, datetime):
        analysis_start = datetime.fromisoformat(str(analysis_start))
    if analysis_end and not isinstance(analysis_end, datetime):
        analysis_end = datetime.fromisoformat(str(analysis_end))

    all_anomalies = []

    # Check marketing channels
    marketing_anomalies = marketing.get_anomalies(start_date=analysis_start, end_date=analysis_end)
    all_anomalies.extend(marketing_anomalies)

    # Check influencer campaigns
    influencer_anomalies = influencer.get_anomalies(start_date=analysis_start, end_date=analysis_end)
    all_anomalies.extend(influencer_anomalies)
    
    # Select highest priority anomaly
    selected = all_anomalies[0] if all_anomalies else None
    
    # Cross-channel correlation (Improvement #2)
    correlated = _find_correlations(all_anomalies, selected) if selected else []
    
    if selected:
        logger.info("Found %d anomalies", len(all_anomalies))
        logger.info("Auto-Selected: %s %s in %s", selected.get('severity', 'unknown').upper(), selected.get('direction', ''), selected.get('channel', 'unknown'))
        if correlated:
            logger.info("Cross-channel correlations: %d related anomalies", len(correlated))
    else:
        logger.info("No anomalies detected")
    
    return {
        "anomalies": all_anomalies,
        "selected_anomaly": selected,
        "correlated_anomalies": correlated,
        "current_node": "detect_anomalies",
    }


def _find_correlations(all_anomalies: list[dict], selected: dict | None) -> list[dict]:
    """
    Find anomalies co-occurring across channels that may share a root cause.
    
    Improvement #2: Cross-Channel Correlation.
    
    Patterns detected:
    - Multiple channels with same metric anomaly on same day → likely platform/tracking issue
    - Spend up + conversions down across channels → likely pixel/attribution problem
    - Same direction across all paid channels → likely external event or tracking
    """
    if not selected or len(all_anomalies) < 2:
        return []
    
    correlated = []
    selected_channel = selected.get("channel", "")
    selected_metric = selected.get("metric", "")
    selected_direction = selected.get("direction", "")
    
    for anomaly in all_anomalies:
        # Skip the selected anomaly itself
        if (anomaly.get("channel") == selected_channel and 
            anomaly.get("metric") == selected_metric):
            continue
        
        # Correlation signals:
        correlation_score = 0.0
        reasons = []
        
        # 1. Same metric anomaly in different channel
        if anomaly.get("metric") == selected_metric:
            correlation_score += 0.4
            reasons.append(f"Same metric ({selected_metric}) anomaly")
        
        # 2. Same direction
        if anomaly.get("direction") == selected_direction:
            correlation_score += 0.2
            reasons.append(f"Same direction ({selected_direction})")
        
        # 3. Similar severity
        sev_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        sev_diff = abs(
            sev_map.get(anomaly.get("severity", "low"), 1) - 
            sev_map.get(selected.get("severity", "low"), 1)
        )
        if sev_diff <= 1:
            correlation_score += 0.2
            reasons.append("Similar severity")
        
        # 4. Efficiency divergence across channels (spend ↑ conv ↓)
        if anomaly.get("detection_method") == "multi_metric_divergence":
            correlation_score += 0.3
            reasons.append("Efficiency divergence detected")
        
        # Threshold for reporting as correlated
        if correlation_score >= 0.4:
            correlated.append({
                **anomaly,
                "correlation_score": round(correlation_score, 2),
                "correlation_reasons": reasons,
            })
    
    # Sort by correlation score
    correlated.sort(key=lambda x: x.get("correlation_score", 0), reverse=True)
    
    return correlated[:5]  # Top 5 most correlated

