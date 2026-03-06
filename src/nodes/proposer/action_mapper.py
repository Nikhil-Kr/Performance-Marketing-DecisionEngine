"""Proposer Node - Maps diagnosis to executable actions using LLM + keyword fallback + MMM guardrail."""
import uuid
import json
import re
from datetime import datetime
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_llm_safe, extract_content
from src.data_layer import get_strategy_data
from src.utils.logging import get_logger

logger = get_logger("proposer")


# Action templates based on root cause patterns
ACTION_TEMPLATES = {
    # --- Digital Performance ---
    "competitor_bidding": {
        "action_type": "bid_adjustment",
        "operation": "increase",
        "parameters": {"adjustment_pct": 20},
        "estimated_impact": "Regain impression share within 24-48 hours",
        "risk_level": "medium",
        "description": "Increase bids to counter competitor activity in auctions",
    },
    "creative_fatigue": {
        "action_type": "notification",
        "operation": "alert",
        "parameters": {"team": "creative", "urgency": "high"},
        "estimated_impact": "New creative deployment within 2-3 days",
        "risk_level": "low",
        "description": "Alert creative team about ad fatigue and need for fresh assets",
    },
    "tracking_issue": {
        "action_type": "notification",
        "operation": "alert",
        "parameters": {"team": "engineering", "urgency": "critical"},
        "estimated_impact": "Tracking restoration within 2-4 hours",
        "risk_level": "low",
        "description": "Alert engineering to fix tracking pixel, tag, or attribution issues",
    },
    "budget_exhaustion": {
        "action_type": "budget_change",
        "operation": "increase",
        "parameters": {"adjustment_pct": 25},
        "estimated_impact": "Resume spend immediately",
        "risk_level": "medium",
        "description": "Increase daily budget to prevent spend caps from limiting delivery",
    },
    "platform_issue": {
        "action_type": "notification",
        "operation": "alert",
        "parameters": {"team": "platform_ops", "urgency": "medium"},
        "estimated_impact": "Monitor for platform recovery",
        "risk_level": "low",
        "description": "Alert ops team about suspected platform algorithm or outage issue",
    },
    "audience_saturation": {
        "action_type": "pause",
        "operation": "pause_campaign",
        "parameters": {"duration_hours": 24},
        "estimated_impact": "Reduce wasted spend, allow audience refresh",
        "risk_level": "medium",
        "description": "Pause high-frequency campaigns to allow audience refresh",
    },

    # --- Fraud & Compliance ---
    "bot_traffic": {
        "action_type": "exclusion",
        "operation": "block_ip_range",
        "parameters": {"list_id": "global_blocklist", "update": "append"},
        "estimated_impact": "Stop invalid traffic spend immediately",
        "risk_level": "medium",
        "description": "Block suspected bot traffic IP ranges to stop wasted spend",
    },
    "influencer_fraud": {
        "action_type": "contract",
        "operation": "terminate_agreement",
        "parameters": {"reason": "fraud_clause", "notify_legal": True},
        "estimated_impact": "Recover remaining budget, blacklist creator",
        "risk_level": "high",
        "description": "Terminate influencer contract for fraudulent activity (fake followers/engagement)",
    },

    # --- Offline & Partners ---
    "make_good": {
        "action_type": "negotiation",
        "operation": "request_make_good",
        "parameters": {"inventory_type": "equivalent_spot"},
        "estimated_impact": "Recover lost GRPs in next flight",
        "risk_level": "low",
        "description": "Request make-good spots for preempted or under-delivered media",
    },
    "partner_issue": {
        "action_type": "communication",
        "operation": "contact_partner",
        "parameters": {"priority": "high", "template": "compliance_violation"},
        "estimated_impact": "Restore tracking or stop leakage",
        "risk_level": "low",
        "description": "Contact media partner about compliance or tracking issues",
    },
    "schedule_adjustment": {
        "action_type": "schedule_change",
        "operation": "reschedule",
        "parameters": {"shift_strategy": "optimize_daypart"},
        "estimated_impact": "Improve reach by shifting to higher-performing time slots",
        "risk_level": "low",
        "description": "Adjust media schedule timing (daypart, day-of-week) for offline channels",
    },
}


def propose_actions(state: ExpeditionState) -> dict:
    """
    Proposer Node — V4.

    Maps diagnosis to executable actions via LLM (primary) + keyword fallback,
    then applies MMM guardrail to block budget increases on saturated channels.
    """
    logger.info("Proposing Actions...")

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

    # Primary: LLM-based action mapping
    actions = _llm_action_mapping(diagnosis, anomaly)

    # Fallback: keyword matching if LLM fails or returns nothing
    if not actions:
        logger.warning("LLM mapping failed, using keyword fallback")
        allowed_keys = diagnosis.get("allowed_action_keys")
        actions = _keyword_action_mapping(root_cause, channel, anomaly, allowed_keys)

    # Last resort: manual review notification
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

    # MMM Guardrail: block budget increases on saturated channels
    actions = _apply_guardrails(actions, channel, state)

    logger.info("Generated %d proposed actions", len(actions))
    for action in actions:
        logger.info("  - %s: %s (%s risk)", action['action_type'], action['operation'], action['risk_level'])

    return {
        "proposed_actions": actions,
        "current_node": "proposer",
    }


def _apply_guardrails(actions: list, channel: str, state: dict) -> list:
    """
    Apply MMM guardrail to proposed actions.

    If a channel is saturated (marginal ROAS < 1.0 or recommendation == 'maintain'),
    block any budget_increase actions and replace them with a manual_review notification.
    Uses analysis_end_date from state for time-travel compliance.
    """
    try:
        strategy = get_strategy_data()

        reference_date = None
        if state.get("analysis_end_date"):
            try:
                reference_date = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        mmm = strategy.get_mmm_guardrails(channel, reference_date=reference_date)

        if not mmm:
            return actions

        marginal_roas = mmm.get("current_marginal_roas", 1.0)
        recommendation = mmm.get("recommendation", "scale")

        filtered = []
        for action in actions:
            if (
                action.get("action_type") == "budget_change"
                and action.get("operation") == "increase"
                and (recommendation == "maintain" or marginal_roas < 1.0)
            ):
                logger.warning("MMM Guardrail: blocked budget increase - channel saturated (marginal ROAS: %.2f)", marginal_roas)
                review_action = {
                    "action_id": f"action_{uuid.uuid4().hex[:8]}",
                    "action_type": "notification",
                    "platform": _get_platform(channel),
                    "resource_type": "alert",
                    "resource_id": "manual_review",
                    "operation": "alert",
                    "parameters": {"team": "decision_science", "urgency": "medium"},
                    "estimated_impact": f"Review recommended: channel near saturation (marginal ROAS: {marginal_roas:.2f})",
                    "risk_level": "low",
                    "requires_approval": False,
                }
                filtered.append(review_action)
            else:
                filtered.append(action)

        return filtered

    except Exception as e:
        logger.error("MMM guardrail check failed: %s", e, exc_info=True)
        # Fail-safe: block budget increases rather than allowing them through unguarded
        return [a for a in actions if not (a.get("action_type") == "budget_change" and a.get("operation") == "increase")]


def _llm_action_mapping(diagnosis: dict, anomaly: dict | None) -> list[dict]:
    """Use LLM (Tier 1) to intelligently map diagnosis to action templates.

    Respects allowed_action_keys from the explainer's ROOT_CAUSE_ACTION_MAP
    guardrail — only shows the LLM templates that are valid for this root cause.
    """
    try:
        llm = get_llm_safe("tier1")

        # Filter templates to allowed keys if the explainer set them
        allowed_keys = diagnosis.get("allowed_action_keys")
        if allowed_keys:
            templates_to_show = {k: v for k, v in ACTION_TEMPLATES.items() if k in allowed_keys}
            if not templates_to_show:
                templates_to_show = ACTION_TEMPLATES  # fallback to all if no overlap
        else:
            templates_to_show = ACTION_TEMPLATES

        template_menu = "\n".join([
            f"- {key}: {tmpl.get('description', tmpl.get('operation', key))}"
            for key, tmpl in templates_to_show.items()
        ])

        channel = anomaly.get("channel", "unknown") if anomaly else "unknown"

        prompt = f"""Given this diagnosis, select the most appropriate action templates.

DIAGNOSIS:
Root Cause: {diagnosis.get('root_cause', 'Unknown')}
Confidence: {diagnosis.get('confidence', 'N/A')}
Recommended Actions: {diagnosis.get('recommended_actions', [])}

CHANNEL: {channel}

AVAILABLE ACTION TEMPLATES:
{template_menu}

Select 1-3 templates that best address this root cause.
Respond ONLY with a JSON array of template keys, e.g.: ["tracking_issue", "creative_fatigue"]
Do not include any explanation, just the JSON array."""

        messages = [{"role": "user", "content": prompt}]
        response = llm.invoke(messages)

        content = extract_content(response).strip()
        json_match = re.search(r'\[[\s\S]*?\]', content)
        if json_match:
            selected_keys = json.loads(json_match.group())
            actions = []
            for key in selected_keys:
                key = key.strip().lower()
                if key in ACTION_TEMPLATES:
                    actions.append(_create_action(key, channel, anomaly))
            if actions:
                return actions

    except Exception as e:
        logger.error("LLM action mapping failed: %s", e, exc_info=True)

    return []


def _keyword_action_mapping(root_cause: str, channel: str, anomaly: dict | None, allowed_keys: list | None = None) -> list[dict]:
    """Fallback keyword-based action mapping. Respects allowed_keys guardrail if provided."""
    actions = []

    def _add(key):
        if allowed_keys is None or key in allowed_keys:
            actions.append(_create_action(key, channel, anomaly))

    if any(kw in root_cause for kw in ["competitor", "bidding", "auction", "cpc", "impression share"]):
        _add("competitor_bidding")
    if any(kw in root_cause for kw in ["creative", "fatigue", "ad copy", "script", "video", "frequency"]):
        _add("creative_fatigue")
    if any(kw in root_cause for kw in ["tracking", "pixel", "attribution", "measurement", "tag", "ios", "capi", "gtm"]):
        _add("tracking_issue")
    if any(kw in root_cause for kw in ["budget", "spend", "cap", "limit", "exhausted"]):
        _add("budget_exhaustion")
    if any(kw in root_cause for kw in ["platform", "algorithm", "outage", "bug", "update"]):
        _add("platform_issue")
    if any(kw in root_cause for kw in ["saturation", "frequency", "overexposure", "lookalike"]):
        _add("audience_saturation")
    if any(kw in root_cause for kw in ["bot", "fraud", "fake", "invalid", "click farm"]):
        if "influencer" in channel:
            _add("influencer_fraud")
        else:
            _add("bot_traffic")
    if any(kw in root_cause for kw in ["preempt", "make-good", "nielsen", "tv spot", "grp", "delivery"]):
        _add("make_good")
    if any(kw in root_cause for kw in ["affiliate", "partner", "coupon", "leakage", "promo code"]):
        _add("partner_issue")
    if any(kw in root_cause for kw in ["daypart", "schedule", "timing", "weekend", "holiday", "download"]):
        _add("schedule_adjustment")

    return actions


def _create_action(template_key: str, channel: str, anomaly: dict | None) -> dict:
    """Create an action from a template."""
    template = ACTION_TEMPLATES.get(template_key, {})
    return {
        "action_id": f"action_{uuid.uuid4().hex[:8]}",
        "action_type": template.get("action_type", "notification"),
        "platform": _get_platform(channel),
        "resource_type": "campaign",
        "resource_id": f"{channel}_campaign_001",
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
    elif channel in ("tv", "radio", "ooh", "events", "podcast", "direct_mail"):
        return f"{channel}_platform"
    else:
        return channel

