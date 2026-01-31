"""Proposer Node - Maps diagnosis to executable actions."""
import uuid
from src.schemas.state import ExpeditionState
from src.data_layer import get_strategy_data

# Action templates - now with BOTH increase and decrease variants
ACTION_TEMPLATES = {
    # --- Budget Actions ---
    "budget_increase": {
        "action_type": "budget_change", 
        "operation": "increase", 
        "parameters": {"adjustment_pct": 20}, 
        "estimated_impact": "Resume spend, capture demand", 
        "risk_level": "medium"
    },
    "budget_decrease": {
        "action_type": "budget_change", 
        "operation": "decrease", 
        "parameters": {"adjustment_pct": 20}, 
        "estimated_impact": "Reduce wasteful spend", 
        "risk_level": "low"
    },
    
    # --- Bid Actions ---
    "bid_increase": {
        "action_type": "bid_adjustment", 
        "operation": "increase", 
        "parameters": {"adjustment_pct": 15}, 
        "estimated_impact": "Regain impression share", 
        "risk_level": "medium"
    },
    "bid_decrease": {
        "action_type": "bid_adjustment", 
        "operation": "decrease", 
        "parameters": {"adjustment_pct": 15}, 
        "estimated_impact": "Reduce CPA, improve efficiency", 
        "risk_level": "low"
    },
    
    # --- Pause/Enable ---
    "pause_campaign": {
        "action_type": "pause", 
        "operation": "pause", 
        "parameters": {"duration_hours": 24}, 
        "estimated_impact": "Stop bleeding, reassess", 
        "risk_level": "medium"
    },
    "enable_campaign": {
        "action_type": "enable", 
        "operation": "enable", 
        "parameters": {}, 
        "estimated_impact": "Resume paused activity", 
        "risk_level": "low"
    },
    
    # --- Notifications ---
    "creative_fatigue": {
        "action_type": "notification", 
        "operation": "alert", 
        "parameters": {"team": "creative", "urgency": "high"}, 
        "estimated_impact": "New creative in 2-3 days", 
        "risk_level": "low"
    },
    "tracking_issue": {
        "action_type": "notification", 
        "operation": "alert", 
        "parameters": {"team": "engineering", "urgency": "critical"}, 
        "estimated_impact": "Fix tracking within hours", 
        "risk_level": "low"
    },
    "platform_issue": {
        "action_type": "notification", 
        "operation": "alert", 
        "parameters": {"team": "ops", "urgency": "medium"}, 
        "estimated_impact": "Monitor platform status", 
        "risk_level": "low"
    },
    "manual_review": {
        "action_type": "notification", 
        "operation": "alert", 
        "parameters": {"team": "decision_science", "urgency": "medium"}, 
        "estimated_impact": "Analyst review within 1 hour", 
        "risk_level": "low"
    },
    
    # --- Fraud/Bot ---
    "bot_traffic": {
        "action_type": "exclusion", 
        "operation": "block_ip", 
        "parameters": {"list": "global_blocklist"}, 
        "estimated_impact": "Stop invalid traffic spend", 
        "risk_level": "medium"
    },
    "influencer_fraud": {
        "action_type": "contract", 
        "operation": "terminate", 
        "parameters": {"reason": "fraud_clause"}, 
        "estimated_impact": "Recover budget, blacklist creator", 
        "risk_level": "high"
    },
    
    # --- Offline / TV / Podcast ---
    "make_good": {
        "action_type": "negotiation", 
        "operation": "request_make_good", 
        "parameters": {"inventory_type": "equivalent"}, 
        "estimated_impact": "Recover lost GRPs", 
        "risk_level": "low"
    },
    "partner_issue": {
        "action_type": "communication", 
        "operation": "contact_partner", 
        "parameters": {"priority": "high"}, 
        "estimated_impact": "Restore tracking or fix leakage", 
        "risk_level": "low"
    },
    "vendor_delivery": {
        "action_type": "notification", 
        "operation": "alert", 
        "parameters": {"team": "media_buying"}, 
        "estimated_impact": "Vendor follow-up", 
        "risk_level": "low"
    },
    "measurement_audit": {
        "action_type": "notification", 
        "operation": "alert", 
        "parameters": {"team": "analytics"}, 
        "estimated_impact": "Verify measurement accuracy", 
        "risk_level": "low"
    },
}

# Offline channel identifiers
OFFLINE_CHANNELS = {"tv", "podcast", "radio", "direct_mail", "ooh", "events"}

# Metrics where a SPIKE is bad (higher = worse)
BAD_SPIKE_METRICS = {"cpa", "cpc", "cpm", "cost", "frequency"}

# Metrics where a DROP is bad (lower = worse)
BAD_DROP_METRICS = {"roas", "conversions", "revenue", "clicks", "impressions", "ctr", "engagement_rate"}


def propose_actions(state: ExpeditionState) -> dict:
    """
    Propose actions that MATCH the diagnosis findings.
    
    Key logic:
    - If metric is CPA and direction is SPIKE (bad) → decrease budget/bids, pause
    - If metric is ROAS and direction is DROP (bad) → investigate, possibly pause
    - If budget exhausted (spend dropped) → increase budget
    - Use diagnosis.recommended_actions to guide action selection
    """
    print("\n🎯 Proposing Actions...")
    diagnosis = state.get("diagnosis")
    anomaly = state.get("selected_anomaly")
    
    if not diagnosis: 
        return {"proposed_actions": []}
    
    root_cause = diagnosis.get("root_cause", "").lower()
    recommended = diagnosis.get("recommended_actions", [])
    recommended_text = " ".join(recommended).lower() if recommended else ""
    
    channel = anomaly.get("channel", "unknown") if anomaly else "unknown"
    metric = anomaly.get("metric", "").lower() if anomaly else ""
    direction = anomaly.get("direction", "").lower() if anomaly else ""
    
    is_offline = any(off in channel.lower() for off in OFFLINE_CHANNELS)
    
    # Determine if this is a "bad" situation that needs remediation
    is_bad_spike = direction == "spike" and metric in BAD_SPIKE_METRICS
    is_bad_drop = direction == "drop" and metric in BAD_DROP_METRICS
    is_problematic = is_bad_spike or is_bad_drop
    
    actions = []
    
    print(f"  📊 Anomaly: {metric} {direction} | Problematic: {is_problematic}")
    
    # === SMART ACTION MAPPING ===
    
    # 1. Check diagnosis recommended_actions first (LLM guidance)
    if recommended_text:
        if any(word in recommended_text for word in ["decrease", "reduce", "lower", "cut"]):
            if "budget" in recommended_text:
                actions.append(_create(channel, anomaly, "budget_decrease"))
            if "bid" in recommended_text:
                actions.append(_create(channel, anomaly, "bid_decrease"))
        
        if any(word in recommended_text for word in ["increase", "raise", "boost"]):
            if "budget" in recommended_text and not is_bad_spike:
                actions.append(_create(channel, anomaly, "budget_increase"))
            if "bid" in recommended_text and not is_bad_spike:
                actions.append(_create(channel, anomaly, "bid_increase"))
        
        if any(word in recommended_text for word in ["pause", "stop", "halt"]):
            actions.append(_create(channel, anomaly, "pause_campaign"))
    
    # 2. Root cause based mapping
    if "competitor" in root_cause or "bidding" in root_cause or "auction" in root_cause:
        # Competitor pressure: if CPA spiked, we might need to bid more OR cut losses
        if is_bad_spike:
            # CPA spiked due to competition - consider pausing or reducing
            actions.append(_create(channel, anomaly, "bid_decrease"))
            actions.append(_create(channel, anomaly, "manual_review"))
        else:
            # Trying to regain share
            actions.append(_create(channel, anomaly, "bid_increase"))
    
    if "creative" in root_cause or "fatigue" in root_cause or "ad copy" in root_cause:
        actions.append(_create(channel, anomaly, "creative_fatigue"))
        if is_problematic:
            actions.append(_create(channel, anomaly, "budget_decrease"))  # Reduce waste while fixing
    
    if "tracking" in root_cause or "pixel" in root_cause or "attribution" in root_cause:
        actions.append(_create(channel, anomaly, "tracking_issue"))
    
    if "budget" in root_cause:
        if "exhaust" in root_cause or "cap" in root_cause or "limit" in root_cause:
            # Budget exhausted = spend dropped, need more budget
            actions.append(_create(channel, anomaly, "budget_increase"))
        elif "over" in root_cause or "wasteful" in root_cause:
            # Overspending
            actions.append(_create(channel, anomaly, "budget_decrease"))
    
    if "saturation" in root_cause or "frequency" in root_cause or "overexposure" in root_cause:
        actions.append(_create(channel, anomaly, "pause_campaign"))
        actions.append(_create(channel, anomaly, "budget_decrease"))
    
    if "bot" in root_cause or "fraud" in root_cause or "invalid" in root_cause:
        if "influencer" in channel:
            actions.append(_create(channel, anomaly, "influencer_fraud"))
        else:
            actions.append(_create(channel, anomaly, "bot_traffic"))
        actions.append(_create(channel, anomaly, "pause_campaign"))
    
    if "platform" in root_cause or "algorithm" in root_cause or "outage" in root_cause:
        actions.append(_create(channel, anomaly, "platform_issue"))
    
    # 3. Offline-specific patterns
    if is_offline:
        if "preempt" in root_cause or "make-good" in root_cause or "delivery" in root_cause:
            actions.append(_create(channel, anomaly, "make_good"))
        if "affiliate" in root_cause or "partner" in root_cause or "leakage" in root_cause:
            actions.append(_create(channel, anomaly, "partner_issue"))
        if "nielsen" in root_cause or "measurement" in root_cause or "model" in root_cause:
            actions.append(_create(channel, anomaly, "measurement_audit"))
        if "vendor" in root_cause or "inventory" in root_cause:
            actions.append(_create(channel, anomaly, "vendor_delivery"))
    
    # 4. If problematic and no specific action yet, add safe defaults
    if is_problematic and not actions:
        if is_bad_spike:
            # High CPA/CPC - reduce spend
            actions.append(_create(channel, anomaly, "budget_decrease"))
            actions.append(_create(channel, anomaly, "manual_review"))
        else:
            # Low ROAS/conversions - investigate
            actions.append(_create(channel, anomaly, "manual_review"))
    
    # 5. Fallback
    if not actions:
        if is_offline:
            actions.append(_create(channel, anomaly, "vendor_delivery"))
        else:
            actions.append(_create(channel, anomaly, "manual_review"))
    
    # Remove duplicates (by action_type + operation)
    seen = set()
    unique_actions = []
    for action in actions:
        key = f"{action['action_type']}_{action['operation']}"
        if key not in seen:
            seen.add(key)
            unique_actions.append(action)
    
    # Apply MMM Guardrails (with state for date context)
    final_actions = _apply_guardrails(unique_actions, channel, state)
    
    print(f"  ✅ Generated {len(final_actions)} actions")
    for action in final_actions:
        print(f"    - {action['action_type']}: {action['operation']} ({action['risk_level']} risk)")
    
    return {"proposed_actions": final_actions}


def _apply_guardrails(actions: list, channel: str, state: dict) -> list:
    """
    Apply MMM guardrails to proposed actions.
    
    If channel is saturated, block budget increases.
    Uses reference_date from state for time-travel compliance.
    """
    try:
        strategy = get_strategy_data()
        
        # Get reference date from state
        reference_date = None
        if state.get("analysis_end_date"):
            from datetime import datetime
            reference_date = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
        
        mmm = strategy.get_mmm_guardrails(channel, reference_date=reference_date)
        
        if not mmm:
            return actions
        
        marginal_roas = mmm.get("current_marginal_roas", 1.0)
        recommendation = mmm.get("recommendation", "maintain")
        
        filtered = []
        for action in actions:
            # Block budget INCREASES if channel is saturated
            if action.get("action_type") == "budget_change" and action.get("operation") == "increase":
                if recommendation == "maintain" or marginal_roas < 1.0:
                    print(f"    ⚠️ Blocked budget increase: channel saturated (ROAS: {marginal_roas:.2f})")
                    # Replace with review action
                    action = _create(channel, {}, "manual_review")
                    action["estimated_impact"] = f"Review recommended: channel near saturation (marginal ROAS: {marginal_roas:.2f})"
            
            filtered.append(action)
        
        return filtered
        
    except Exception as e:
        print(f"    ⚠️ Guardrail check failed: {e}")
        return actions


def _create(channel: str, anomaly: dict, template_key: str) -> dict:
    """Create an action from a template with proper platform routing."""
    t = ACTION_TEMPLATES.get(template_key, ACTION_TEMPLATES["manual_review"])
    
    # Build description based on anomaly context
    metric = anomaly.get("metric", "metric") if anomaly else "metric"
    direction = anomaly.get("direction", "") if anomaly else ""
    
    return {
        "action_id": f"act_{uuid.uuid4().hex[:8]}",
        "action_type": t.get("action_type", "notification"),
        "platform": _get_platform(channel),
        "resource_type": "campaign",
        "resource_id": f"{channel}_campaign_001",
        "operation": t.get("operation", "alert"),
        "parameters": t.get("parameters", {}),
        "risk_level": t.get("risk_level", "medium"),
        "estimated_impact": t.get("estimated_impact", "Unknown"),
        "requires_approval": t.get("risk_level", "medium") != "low",
        "context": f"Response to {metric} {direction}" if metric and direction else "",
    }


def _get_platform(channel: str) -> str:
    """Map channel to platform/executor name."""
    c = channel.lower()
    
    # Digital platforms
    if "google" in c:
        return "google_ads"
    elif "meta" in c:
        return "meta_ads"
    elif "tiktok" in c:
        return "tiktok_ads"
    elif "linkedin" in c:
        return "linkedin_ads"
    elif "influencer" in c:
        return "creatoriq"
    
    # Offline platforms
    elif "tv" in c:
        return "tv_buying"
    elif "podcast" in c:
        return "podcast_network"
    elif "radio" in c:
        return "radio_buying"
    elif "direct_mail" in c or "mail" in c:
        return "direct_mail"
    elif "ooh" in c or "outdoor" in c:
        return "ooh_vendor"
    elif "event" in c:
        return "events_team"
    elif "affiliate" in c:
        return "affiliate_network"
    elif "programmatic" in c:
        return "dsp"
    
    return channel
