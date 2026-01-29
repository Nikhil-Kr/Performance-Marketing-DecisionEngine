"""Proposer Node - Maps diagnosis to executable actions."""
import uuid
from src.schemas.state import ExpeditionState


# Action templates based on root cause patterns
ACTION_TEMPLATES = {
    # --- Digital Performance ---
    "competitor_bidding": {
        "action_type": "bid_adjustment",
        "operation": "increase",
        "parameters": {"adjustment_pct": 20},
        "estimated_impact": "Regain impression share within 24-48 hours",
        "risk_level": "medium",
    },
    "creative_fatigue": {
        "action_type": "notification",
        "operation": "alert",
        "parameters": {"team": "creative", "urgency": "high"},
        "estimated_impact": "New creative deployment within 2-3 days",
        "risk_level": "low",
    },
    "tracking_issue": {
        "action_type": "notification",
        "operation": "alert",
        "parameters": {"team": "engineering", "urgency": "critical"},
        "estimated_impact": "Tracking restoration within 2-4 hours",
        "risk_level": "low",
    },
    "budget_exhaustion": {
        "action_type": "budget_change",
        "operation": "increase",
        "parameters": {"adjustment_pct": 25},
        "estimated_impact": "Resume spend immediately",
        "risk_level": "medium",
    },
    "platform_issue": {
        "action_type": "notification",
        "operation": "alert",
        "parameters": {"team": "platform_ops", "urgency": "medium"},
        "estimated_impact": "Monitor for platform recovery",
        "risk_level": "low",
    },
    "audience_saturation": {
        "action_type": "pause",
        "operation": "pause_campaign",
        "parameters": {"duration_hours": 24},
        "estimated_impact": "Reduce wasted spend, allow audience refresh",
        "risk_level": "medium",
    },
    
    # --- Fraud & Compliance ---
    "bot_traffic": {
        "action_type": "exclusion",
        "operation": "block_ip_range",
        "parameters": {"list_id": "global_blocklist", "update": "append"},
        "estimated_impact": "Stop invalid traffic spend immediately",
        "risk_level": "medium",
    },
    "influencer_fraud": {
        "action_type": "contract",
        "operation": "terminate_agreement",
        "parameters": {"reason": "fraud_clause", "notify_legal": True},
        "estimated_impact": "Recover remaining budget, blacklist creator",
        "risk_level": "high",
    },
    
    # --- Offline & Partners ---
    "make_good": {
        "action_type": "negotiation",
        "operation": "request_make_good",
        "parameters": {"inventory_type": "equivalent_spot"},
        "estimated_impact": "Recover lost GRPs in next flight",
        "risk_level": "low",
    },
    "partner_issue": {
        "action_type": "communication",
        "operation": "contact_partner",
        "parameters": {"priority": "high", "template": "compliance_violation"},
        "estimated_impact": "Restore tracking or stop leakage",
        "risk_level": "low",
    }
}


def propose_actions(state: ExpeditionState) -> dict:
    """
    Proposer Node.
    
    Maps the diagnosis root cause to specific executable actions.
    
    Per architecture:
    - Generates JSON payloads compatible with platform APIs
    - Includes risk assessment for each action
    - Flags actions requiring human approval
    """
    print("\n🎯 Proposing Actions...")
    
    diagnosis = state.get("diagnosis")
    anomaly = state.get("selected_anomaly")
    
    if not diagnosis:
        return {
            "proposed_actions": [],
            "current_node": "proposer",
            "error": "No diagnosis to propose actions for",
        }
    
    root_cause = diagnosis.get("root_cause", "").lower()
    channel = anomaly.get("channel", "unknown") if anomaly else "unknown"
    
    # Match root cause to action templates
    actions = []
    
    # --- Keyword Matching Logic ---
    
    # 1. Competitor / Bidding
    if any(kw in root_cause for kw in ["competitor", "bidding", "auction", "cpc"]):
        actions.append(_create_action("competitor_bidding", channel, anomaly))
    
    # 2. Creative / Content
    if any(kw in root_cause for kw in ["creative", "fatigue", "ad copy", "script", "video"]):
        actions.append(_create_action("creative_fatigue", channel, anomaly))
    
    # 3. Technical / Tracking
    if any(kw in root_cause for kw in ["tracking", "pixel", "attribution", "measurement", "tag", "ios"]):
        actions.append(_create_action("tracking_issue", channel, anomaly))
    
    # 4. Budget / Spend
    if any(kw in root_cause for kw in ["budget", "spend", "cap", "limit"]):
        actions.append(_create_action("budget_exhaustion", channel, anomaly))
    
    # 5. Platform Errors
    if any(kw in root_cause for kw in ["platform", "algorithm", "outage", "bug"]):
        actions.append(_create_action("platform_issue", channel, anomaly))
    
    # 6. Saturation / Frequency
    if any(kw in root_cause for kw in ["saturation", "frequency", "overexposure"]):
        actions.append(_create_action("audience_saturation", channel, anomaly))

    # 7. Fraud / Bots (NEW)
    if any(kw in root_cause for kw in ["bot", "fraud", "fake", "invalid", "click farm"]):
        if "influencer" in channel:
            actions.append(_create_action("influencer_fraud", channel, anomaly))
        else:
            actions.append(_create_action("bot_traffic", channel, anomaly))

    # 8. TV / Offline Issues (NEW)
    if any(kw in root_cause for kw in ["preempt", "make-good", "nielsen", "tv spot"]):
        actions.append(_create_action("make_good", channel, anomaly))

    # 9. Partner / Affiliate (NEW)
    if any(kw in root_cause for kw in ["affiliate", "partner", "coupon", "leakage"]):
        actions.append(_create_action("partner_issue", channel, anomaly))
    
    # Always add a notification action as fallback if nothing matched
    if not actions:
        actions.append({
            "action_id": f"action_{uuid.uuid4().hex[:8]}",
            "action_type": "notification",
            "platform": channel,
            "resource_type": "alert",
            "resource_id": "manual_review",
            "operation": "alert",
            "parameters": {
                "team": "decision_science",
                "urgency": "medium",
                "message": f"Manual review required for {channel} anomaly",
            },
            "estimated_impact": "Analyst assigned within 1 hour",
            "risk_level": "low",
            "requires_approval": False,
        })
    
    print(f"  ✅ Generated {len(actions)} proposed actions")
    for action in actions:
        print(f"    - {action['action_type']}: {action['operation']} ({action['risk_level']} risk)")
    
    return {
        "proposed_actions": actions,
        "current_node": "proposer",
    }


def _create_action(template_key: str, channel: str, anomaly: dict | None) -> dict:
    """Create an action from a template."""
    template = ACTION_TEMPLATES.get(template_key, {})
    
    # Determine resource ID (would be real campaign/ad group ID in production)
    resource_id = f"{channel}_campaign_001"  # Mock
    
    return {
        "action_id": f"action_{uuid.uuid4().hex[:8]}",
        "action_type": template.get("action_type", "notification"),
        "platform": _get_platform(channel),
        "resource_type": "campaign",
        "resource_id": resource_id,
        "operation": template.get("operation", "alert"),
        "parameters": template.get("parameters", {}),
        "estimated_impact": template.get("estimated_impact", "Unknown"),
        "risk_level": template.get("risk_level", "medium"),
        "requires_approval": template.get("risk_level", "medium") != "low",
    }


def _get_platform(channel: str) -> str:
    """Map channel to platform name."""
    if channel.startswith("google"):
        return "google_ads"
    elif channel.startswith("meta"):
        return "meta_ads"
    elif channel.startswith("tiktok"):
        return "tiktok_ads"
    elif channel == "influencer_campaigns":
        return "creatoriq"
    else:
        return channel