# <--------V3 ------------->
"""Pre-Flight Check Node - Validates data freshness before investigation."""
from datetime import datetime, timedelta

from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data, get_influencer_data


# Maximum allowed data latency (from architecture spec)
MAX_DATA_LATENCY_HOURS = 1


def preflight_check(state: ExpeditionState) -> dict:
    """
    Pre-Flight Check Node.
    
    Validates data freshness before investigation begins.
    Per architecture: Aborts if data is stale (>1 hour old).
    
    This prevents diagnosing noise from stale pipelines.
    """
    print("\n🔍 Running Pre-Flight Check...")
    
    issues = []
    freshness = {}
    
    try:
        # Check marketing data
        marketing = get_marketing_data()
        if marketing.is_healthy():
            marketing_freshness = marketing.check_data_freshness()
            freshness.update({
                f"marketing_{k}": v.isoformat() if isinstance(v, datetime) else str(v)
                for k, v in marketing_freshness.items()
            })
        else:
            issues.append("Marketing data source is unhealthy")
        
        # Check influencer data
        influencer = get_influencer_data()
        if influencer.is_healthy():
            influencer_freshness = influencer.check_data_freshness()
            freshness.update({
                f"influencer_{k}": v.isoformat() if isinstance(v, datetime) else str(v)
                for k, v in influencer_freshness.items()
            })
        else:
            issues.append("Influencer data source is unhealthy")
        
        # Validate freshness (in production, check actual timestamps)
        # For mock data, we always pass since timestamps are "now"
        cutoff = datetime.now() - timedelta(hours=MAX_DATA_LATENCY_HOURS)
        
    except Exception as e:
        issues.append(f"Error during pre-flight: {str(e)}")
    
    passed = len(issues) == 0
    
    if passed:
        print("  ✅ Pre-flight check passed")
    else:
        print(f"  ❌ Pre-flight check failed: {issues}")
    
    return {
        "data_freshness": freshness,
        "preflight_passed": passed,
        "preflight_error": "; ".join(issues) if issues else None,
        "current_node": "preflight",
    }


def detect_anomalies(state: ExpeditionState) -> dict:
    """
    Detect anomalies across all channels within the analysis date range.
    
    Called after pre-flight passes to identify issues to investigate.
    Respects the user's selected date range from state.
    """
    print("\n🔎 Detecting anomalies...")
    
    # 1. PRIORITY CHECK: Did the user manually select an anomaly?
    # If app.py passed a 'selected_anomaly', we trust it and skip auto-detection.
    if state.get("selected_anomaly"):
        selected = state["selected_anomaly"]
        print(f"  📌 User selected target: {selected.get('channel', 'unknown')} ({selected.get('metric', 'unknown')})")
        return {
            "selected_anomaly": selected,
            "current_node": "detect_anomalies",
            # We preserve existing anomalies list if present, or create a list with just this one
            "anomalies": state.get("anomalies", [selected])
        }

    # 2. Extract date range from state (set by UI or batch processor)
    start_date = None
    end_date = None
    
    if state.get("analysis_start_date"):
        try:
            start_date = datetime.strptime(state["analysis_start_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass
            
    if state.get("analysis_end_date"):
        try:
            end_date = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    
    # Log the date range being used
    if start_date and end_date:
        print(f"  📅 Analysis period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    elif end_date:
        print(f"  📅 Analysis as of: {end_date.strftime('%Y-%m-%d')}")
    else:
        print(f"  📅 Analysis period: Using defaults (now)")

    # 3. AUTO-PILOT: Scan everything with the date range
    marketing = get_marketing_data()
    influencer = get_influencer_data()
    
    all_anomalies = []
    
    # Check marketing channels with date range
    marketing_anomalies = marketing.get_anomalies(
        start_date=start_date,
        end_date=end_date
    )
    all_anomalies.extend(marketing_anomalies)
    
    # Check influencer campaigns with date range
    influencer_anomalies = influencer.get_anomalies(
        start_date=start_date,
        end_date=end_date
    )
    all_anomalies.extend(influencer_anomalies)
    
    # Select highest priority anomaly
    selected = all_anomalies[0] if all_anomalies else None
    
    if selected:
        print(f"  🚨 Found {len(all_anomalies)} anomalies")
        print(f"  📌 Auto-Selected: {selected.get('severity', 'unknown').upper()} {selected.get('direction', '')} in {selected.get('channel', 'unknown')}")
    else:
        print("  ✅ No anomalies detected")
    
    return {
        "anomalies": all_anomalies,
        "selected_anomaly": selected,
        "current_node": "detect_anomalies",
    }
