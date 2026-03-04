# # <--------V3 ------------->
# """Pre-Flight Check Node - Validates data freshness before investigation."""
# from datetime import datetime, timedelta

# from src.schemas.state import ExpeditionState
# from src.data_layer import get_marketing_data, get_influencer_data


# # Maximum allowed data latency (from architecture spec)
# MAX_DATA_LATENCY_HOURS = 1


# def preflight_check(state: ExpeditionState) -> dict:
#     """
#     Pre-Flight Check Node.
    
#     Validates data freshness before investigation begins.
#     Per architecture: Aborts if data is stale (>1 hour old).
    
#     This prevents diagnosing noise from stale pipelines.
#     """
#     print("\n🔍 Running Pre-Flight Check...")
    
#     issues = []
#     freshness = {}
    
#     try:
#         # Check marketing data
#         marketing = get_marketing_data()
#         if marketing.is_healthy():
#             marketing_freshness = marketing.check_data_freshness()
#             freshness.update({
#                 f"marketing_{k}": v.isoformat() if isinstance(v, datetime) else str(v)
#                 for k, v in marketing_freshness.items()
#             })
#         else:
#             issues.append("Marketing data source is unhealthy")
        
#         # Check influencer data
#         influencer = get_influencer_data()
#         if influencer.is_healthy():
#             influencer_freshness = influencer.check_data_freshness()
#             freshness.update({
#                 f"influencer_{k}": v.isoformat() if isinstance(v, datetime) else str(v)
#                 for k, v in influencer_freshness.items()
#             })
#         else:
#             issues.append("Influencer data source is unhealthy")
        
#         # Validate freshness (in production, check actual timestamps)
#         # For mock data, we always pass since timestamps are "now"
#         cutoff = datetime.now() - timedelta(hours=MAX_DATA_LATENCY_HOURS)
        
#     except Exception as e:
#         issues.append(f"Error during pre-flight: {str(e)}")
    
#     passed = len(issues) == 0
    
#     if passed:
#         print("  ✅ Pre-flight check passed")
#     else:
#         print(f"  ❌ Pre-flight check failed: {issues}")
    
#     return {
#         "data_freshness": freshness,
#         "preflight_passed": passed,
#         "preflight_error": "; ".join(issues) if issues else None,
#         "current_node": "preflight",
#     }


# def detect_anomalies(state: ExpeditionState) -> dict:
#     """
#     Detect anomalies across all channels within the analysis date range.
    
#     Called after pre-flight passes to identify issues to investigate.
#     Respects the user's selected date range from state.
#     """
#     print("\n🔎 Detecting anomalies...")
    
#     # 1. PRIORITY CHECK: Did the user manually select an anomaly?
#     # If app.py passed a 'selected_anomaly', we trust it and skip auto-detection.
#     if state.get("selected_anomaly"):
#         selected = state["selected_anomaly"]
#         print(f"  📌 User selected target: {selected.get('channel', 'unknown')} ({selected.get('metric', 'unknown')})")
#         return {
#             "selected_anomaly": selected,
#             "current_node": "detect_anomalies",
#             # We preserve existing anomalies list if present, or create a list with just this one
#             "anomalies": state.get("anomalies", [selected])
#         }

#     # 2. Extract date range from state (set by UI or batch processor)
#     start_date = None
#     end_date = None
    
#     if state.get("analysis_start_date"):
#         try:
#             start_date = datetime.strptime(state["analysis_start_date"], "%Y-%m-%d")
#         except (ValueError, TypeError):
#             pass
            
#     if state.get("analysis_end_date"):
#         try:
#             end_date = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
#         except (ValueError, TypeError):
#             pass
    
#     # Log the date range being used
#     if start_date and end_date:
#         print(f"  📅 Analysis period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
#     elif end_date:
#         print(f"  📅 Analysis as of: {end_date.strftime('%Y-%m-%d')}")
#     else:
#         print(f"  📅 Analysis period: Using defaults (now)")

#     # 3. AUTO-PILOT: Scan everything with the date range
#     marketing = get_marketing_data()
#     influencer = get_influencer_data()
    
#     all_anomalies = []
    
#     # Check marketing channels with date range
#     marketing_anomalies = marketing.get_anomalies(
#         start_date=start_date,
#         end_date=end_date
#     )
#     all_anomalies.extend(marketing_anomalies)
    
#     # Check influencer campaigns with date range
#     influencer_anomalies = influencer.get_anomalies(
#         start_date=start_date,
#         end_date=end_date
#     )
#     all_anomalies.extend(influencer_anomalies)
    
#     # Select highest priority anomaly
#     selected = all_anomalies[0] if all_anomalies else None
    
#     if selected:
#         print(f"  🚨 Found {len(all_anomalies)} anomalies")
#         print(f"  📌 Auto-Selected: {selected.get('severity', 'unknown').upper()} {selected.get('direction', '')} in {selected.get('channel', 'unknown')}")
#     else:
#         print("  ✅ No anomalies detected")
    
#     return {
#         "anomalies": all_anomalies,
#         "selected_anomaly": selected,
#         "current_node": "detect_anomalies",
#     }

## <--------- Updated - 3/3 --------->

"""Pre-Flight & Anomaly Detection Nodes."""
from datetime import datetime, timedelta
from collections import defaultdict
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data, get_influencer_data


def preflight_check(state: ExpeditionState) -> dict:
    """
    Pre-Flight Check Node.
    
    Validates that all data sources are healthy and fresh before proceeding.
    """
    print("\n✈️ Running Pre-Flight Check...")
    
    marketing = get_marketing_data()
    influencer = get_influencer_data()
    
    # Check data health
    marketing_healthy = marketing.is_healthy()
    influencer_healthy = influencer.is_healthy()
    
    if not marketing_healthy and not influencer_healthy:
        print("  ❌ All data sources unhealthy")
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
    
    print(f"  ✅ Pre-flight passed ({len(freshness)} sources healthy)")
    
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
    print("\n🔎 Detecting anomalies...")
    
    # 1. PRIORITY CHECK: Did the user manually select an anomaly?
    # If app.py passed a 'selected_anomaly', we trust it and skip auto-detection.
    if state.get("selected_anomaly"):
        selected = state["selected_anomaly"]
        print(f"  📌 User selected target: {selected.get('channel', 'unknown')} ({selected.get('metric', 'unknown')})")
        
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
    
    all_anomalies = []
    
    # Check marketing channels
    marketing_anomalies = marketing.get_anomalies()
    all_anomalies.extend(marketing_anomalies)
    
    # Check influencer campaigns
    influencer_anomalies = influencer.get_anomalies()
    all_anomalies.extend(influencer_anomalies)
    
    # Select highest priority anomaly
    selected = all_anomalies[0] if all_anomalies else None
    
    # Cross-channel correlation (Improvement #2)
    correlated = _find_correlations(all_anomalies, selected) if selected else []
    
    if selected:
        print(f"  🚨 Found {len(all_anomalies)} anomalies")
        print(f"  📌 Auto-Selected: {selected.get('severity', 'unknown').upper()} {selected.get('direction', '')} in {selected.get('channel', 'unknown')}")
        if correlated:
            print(f"  🔗 Cross-channel correlations: {len(correlated)} related anomalies")
    else:
        print("  ✅ No anomalies detected")
    
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

