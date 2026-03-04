# """Proposer Node - Maps diagnosis to executable actions."""
# import uuid
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_strategy_data

# # Action templates - now with BOTH increase and decrease variants
# ACTION_TEMPLATES = {
#     # --- Budget Actions ---
#     "budget_increase": {
#         "action_type": "budget_change", 
#         "operation": "increase", 
#         "parameters": {"adjustment_pct": 20}, 
#         "estimated_impact": "Resume spend, capture demand", 
#         "risk_level": "medium"
#     },
#     "budget_decrease": {
#         "action_type": "budget_change", 
#         "operation": "decrease", 
#         "parameters": {"adjustment_pct": 20}, 
#         "estimated_impact": "Reduce wasteful spend", 
#         "risk_level": "low"
#     },
    
#     # --- Bid Actions ---
#     "bid_increase": {
#         "action_type": "bid_adjustment", 
#         "operation": "increase", 
#         "parameters": {"adjustment_pct": 15}, 
#         "estimated_impact": "Regain impression share", 
#         "risk_level": "medium"
#     },
#     "bid_decrease": {
#         "action_type": "bid_adjustment", 
#         "operation": "decrease", 
#         "parameters": {"adjustment_pct": 15}, 
#         "estimated_impact": "Reduce CPA, improve efficiency", 
#         "risk_level": "low"
#     },
    
#     # --- Pause/Enable ---
#     "pause_campaign": {
#         "action_type": "pause", 
#         "operation": "pause", 
#         "parameters": {"duration_hours": 24}, 
#         "estimated_impact": "Stop bleeding, reassess", 
#         "risk_level": "medium"
#     },
#     "enable_campaign": {
#         "action_type": "enable", 
#         "operation": "enable", 
#         "parameters": {}, 
#         "estimated_impact": "Resume paused activity", 
#         "risk_level": "low"
#     },
    
#     # --- Notifications ---
#     "creative_fatigue": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "parameters": {"team": "creative", "urgency": "high"}, 
#         "estimated_impact": "New creative in 2-3 days", 
#         "risk_level": "low"
#     },
#     "tracking_issue": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "parameters": {"team": "engineering", "urgency": "critical"}, 
#         "estimated_impact": "Fix tracking within hours", 
#         "risk_level": "low"
#     },
#     "platform_issue": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "parameters": {"team": "ops", "urgency": "medium"}, 
#         "estimated_impact": "Monitor platform status", 
#         "risk_level": "low"
#     },
#     "manual_review": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "parameters": {"team": "decision_science", "urgency": "medium"}, 
#         "estimated_impact": "Analyst review within 1 hour", 
#         "risk_level": "low"
#     },
    
#     # --- Fraud/Bot ---
#     "bot_traffic": {
#         "action_type": "exclusion", 
#         "operation": "block_ip", 
#         "parameters": {"list": "global_blocklist"}, 
#         "estimated_impact": "Stop invalid traffic spend", 
#         "risk_level": "medium"
#     },
#     "influencer_fraud": {
#         "action_type": "contract", 
#         "operation": "terminate", 
#         "parameters": {"reason": "fraud_clause"}, 
#         "estimated_impact": "Recover budget, blacklist creator", 
#         "risk_level": "high"
#     },
    
#     # --- Offline / TV / Podcast ---
#     "make_good": {
#         "action_type": "negotiation", 
#         "operation": "request_make_good", 
#         "parameters": {"inventory_type": "equivalent"}, 
#         "estimated_impact": "Recover lost GRPs", 
#         "risk_level": "low"
#     },
#     "partner_issue": {
#         "action_type": "communication", 
#         "operation": "contact_partner", 
#         "parameters": {"priority": "high"}, 
#         "estimated_impact": "Restore tracking or fix leakage", 
#         "risk_level": "low"
#     },
#     "vendor_delivery": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "parameters": {"team": "media_buying"}, 
#         "estimated_impact": "Vendor follow-up", 
#         "risk_level": "low"
#     },
#     "measurement_audit": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "parameters": {"team": "analytics"}, 
#         "estimated_impact": "Verify measurement accuracy", 
#         "risk_level": "low"
#     },
# }

# # Offline channel identifiers
# OFFLINE_CHANNELS = {"tv", "podcast", "radio", "direct_mail", "ooh", "events"}

# # Metrics where a SPIKE is bad (higher = worse)
# BAD_SPIKE_METRICS = {"cpa", "cpc", "cpm", "cost", "frequency"}

# # Metrics where a DROP is bad (lower = worse)
# BAD_DROP_METRICS = {"roas", "conversions", "revenue", "clicks", "impressions", "ctr", "engagement_rate"}


# def propose_actions(state: ExpeditionState) -> dict:
#     """
#     Propose actions that MATCH the diagnosis findings.
    
#     Key logic:
#     - If metric is CPA and direction is SPIKE (bad) → decrease budget/bids, pause
#     - If metric is ROAS and direction is DROP (bad) → investigate, possibly pause
#     - If budget exhausted (spend dropped) → increase budget
#     - Use diagnosis.recommended_actions to guide action selection
#     """
#     print("\n🎯 Proposing Actions...")
#     diagnosis = state.get("diagnosis")
#     anomaly = state.get("selected_anomaly")
    
#     if not diagnosis: 
#         return {"proposed_actions": []}
    
#     root_cause = diagnosis.get("root_cause", "").lower()
#     recommended = diagnosis.get("recommended_actions", [])
#     recommended_text = " ".join(recommended).lower() if recommended else ""
    
#     channel = anomaly.get("channel", "unknown") if anomaly else "unknown"
#     metric = anomaly.get("metric", "").lower() if anomaly else ""
#     direction = anomaly.get("direction", "").lower() if anomaly else ""
    
#     is_offline = any(off in channel.lower() for off in OFFLINE_CHANNELS)
    
#     # Determine if this is a "bad" situation that needs remediation
#     is_bad_spike = direction == "spike" and metric in BAD_SPIKE_METRICS
#     is_bad_drop = direction == "drop" and metric in BAD_DROP_METRICS
#     is_problematic = is_bad_spike or is_bad_drop
    
#     actions = []
    
#     print(f"  📊 Anomaly: {metric} {direction} | Problematic: {is_problematic}")
    
#     # === SMART ACTION MAPPING ===
    
#     # 1. Check diagnosis recommended_actions first (LLM guidance)
#     if recommended_text:
#         if any(word in recommended_text for word in ["decrease", "reduce", "lower", "cut"]):
#             if "budget" in recommended_text:
#                 actions.append(_create(channel, anomaly, "budget_decrease"))
#             if "bid" in recommended_text:
#                 actions.append(_create(channel, anomaly, "bid_decrease"))
        
#         if any(word in recommended_text for word in ["increase", "raise", "boost"]):
#             if "budget" in recommended_text and not is_bad_spike:
#                 actions.append(_create(channel, anomaly, "budget_increase"))
#             if "bid" in recommended_text and not is_bad_spike:
#                 actions.append(_create(channel, anomaly, "bid_increase"))
        
#         if any(word in recommended_text for word in ["pause", "stop", "halt"]):
#             actions.append(_create(channel, anomaly, "pause_campaign"))
    
#     # 2. Root cause based mapping
#     if "competitor" in root_cause or "bidding" in root_cause or "auction" in root_cause:
#         # Competitor pressure: if CPA spiked, we might need to bid more OR cut losses
#         if is_bad_spike:
#             # CPA spiked due to competition - consider pausing or reducing
#             actions.append(_create(channel, anomaly, "bid_decrease"))
#             actions.append(_create(channel, anomaly, "manual_review"))
#         else:
#             # Trying to regain share
#             actions.append(_create(channel, anomaly, "bid_increase"))
    
#     if "creative" in root_cause or "fatigue" in root_cause or "ad copy" in root_cause:
#         actions.append(_create(channel, anomaly, "creative_fatigue"))
#         if is_problematic:
#             actions.append(_create(channel, anomaly, "budget_decrease"))  # Reduce waste while fixing
    
#     if "tracking" in root_cause or "pixel" in root_cause or "attribution" in root_cause:
#         actions.append(_create(channel, anomaly, "tracking_issue"))
    
#     if "budget" in root_cause:
#         if "exhaust" in root_cause or "cap" in root_cause or "limit" in root_cause:
#             # Budget exhausted = spend dropped, need more budget
#             actions.append(_create(channel, anomaly, "budget_increase"))
#         elif "over" in root_cause or "wasteful" in root_cause:
#             # Overspending
#             actions.append(_create(channel, anomaly, "budget_decrease"))
    
#     if "saturation" in root_cause or "frequency" in root_cause or "overexposure" in root_cause:
#         actions.append(_create(channel, anomaly, "pause_campaign"))
#         actions.append(_create(channel, anomaly, "budget_decrease"))
    
#     if "bot" in root_cause or "fraud" in root_cause or "invalid" in root_cause:
#         if "influencer" in channel:
#             actions.append(_create(channel, anomaly, "influencer_fraud"))
#         else:
#             actions.append(_create(channel, anomaly, "bot_traffic"))
#         actions.append(_create(channel, anomaly, "pause_campaign"))
    
#     if "platform" in root_cause or "algorithm" in root_cause or "outage" in root_cause:
#         actions.append(_create(channel, anomaly, "platform_issue"))
    
#     # 3. Offline-specific patterns
#     if is_offline:
#         if "preempt" in root_cause or "make-good" in root_cause or "delivery" in root_cause:
#             actions.append(_create(channel, anomaly, "make_good"))
#         if "affiliate" in root_cause or "partner" in root_cause or "leakage" in root_cause:
#             actions.append(_create(channel, anomaly, "partner_issue"))
#         if "nielsen" in root_cause or "measurement" in root_cause or "model" in root_cause:
#             actions.append(_create(channel, anomaly, "measurement_audit"))
#         if "vendor" in root_cause or "inventory" in root_cause:
#             actions.append(_create(channel, anomaly, "vendor_delivery"))
    
#     # 4. If problematic and no specific action yet, add safe defaults
#     if is_problematic and not actions:
#         if is_bad_spike:
#             # High CPA/CPC - reduce spend
#             actions.append(_create(channel, anomaly, "budget_decrease"))
#             actions.append(_create(channel, anomaly, "manual_review"))
#         else:
#             # Low ROAS/conversions - investigate
#             actions.append(_create(channel, anomaly, "manual_review"))
    
#     # 5. Fallback
#     if not actions:
#         if is_offline:
#             actions.append(_create(channel, anomaly, "vendor_delivery"))
#         else:
#             actions.append(_create(channel, anomaly, "manual_review"))
    
#     # Remove duplicates (by action_type + operation)
#     seen = set()
#     unique_actions = []
#     for action in actions:
#         key = f"{action['action_type']}_{action['operation']}"
#         if key not in seen:
#             seen.add(key)
#             unique_actions.append(action)
    
#     # Apply MMM Guardrails (with state for date context)
#     final_actions = _apply_guardrails(unique_actions, channel, state)
    
#     print(f"  ✅ Generated {len(final_actions)} actions")
#     for action in final_actions:
#         print(f"    - {action['action_type']}: {action['operation']} ({action['risk_level']} risk)")
    
#     return {"proposed_actions": final_actions}


# def _apply_guardrails(actions: list, channel: str, state: dict) -> list:
#     """
#     Apply MMM guardrails to proposed actions.
    
#     If channel is saturated, block budget increases.
#     Uses reference_date from state for time-travel compliance.
#     """
#     try:
#         strategy = get_strategy_data()
        
#         # Get reference date from state
#         reference_date = None
#         if state.get("analysis_end_date"):
#             from datetime import datetime
#             reference_date = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
        
#         mmm = strategy.get_mmm_guardrails(channel, reference_date=reference_date)
        
#         if not mmm:
#             return actions
        
#         marginal_roas = mmm.get("current_marginal_roas", 1.0)
#         recommendation = mmm.get("recommendation", "maintain")
        
#         filtered = []
#         for action in actions:
#             # Block budget INCREASES if channel is saturated
#             if action.get("action_type") == "budget_change" and action.get("operation") == "increase":
#                 if recommendation == "maintain" or marginal_roas < 1.0:
#                     print(f"    ⚠️ Blocked budget increase: channel saturated (ROAS: {marginal_roas:.2f})")
#                     # Replace with review action
#                     action = _create(channel, {}, "manual_review")
#                     action["estimated_impact"] = f"Review recommended: channel near saturation (marginal ROAS: {marginal_roas:.2f})"
            
#             filtered.append(action)
        
#         return filtered
        
#     except Exception as e:
#         print(f"    ⚠️ Guardrail check failed: {e}")
#         return actions


# def _create(channel: str, anomaly: dict, template_key: str) -> dict:
#     """Create an action from a template with proper platform routing."""
#     t = ACTION_TEMPLATES.get(template_key, ACTION_TEMPLATES["manual_review"])
    
#     # Build description based on anomaly context
#     metric = anomaly.get("metric", "metric") if anomaly else "metric"
#     direction = anomaly.get("direction", "") if anomaly else ""
    
#     return {
#         "action_id": f"act_{uuid.uuid4().hex[:8]}",
#         "action_type": t.get("action_type", "notification"),
#         "platform": _get_platform(channel),
#         "resource_type": "campaign",
#         "resource_id": f"{channel}_campaign_001",
#         "operation": t.get("operation", "alert"),
#         "parameters": t.get("parameters", {}),
#         "risk_level": t.get("risk_level", "medium"),
#         "estimated_impact": t.get("estimated_impact", "Unknown"),
#         "requires_approval": t.get("risk_level", "medium") != "low",
#         "context": f"Response to {metric} {direction}" if metric and direction else "",
#     }


# def _get_platform(channel: str) -> str:
#     """Map channel to platform/executor name."""
#     c = channel.lower()
    
#     # Digital platforms
#     if "google" in c:
#         return "google_ads"
#     elif "meta" in c:
#         return "meta_ads"
#     elif "tiktok" in c:
#         return "tiktok_ads"
#     elif "linkedin" in c:
#         return "linkedin_ads"
#     elif "influencer" in c:
#         return "creatoriq"
    
#     # Offline platforms
#     elif "tv" in c:
#         return "tv_buying"
#     elif "podcast" in c:
#         return "podcast_network"
#     elif "radio" in c:
#         return "radio_buying"
#     elif "direct_mail" in c or "mail" in c:
#         return "direct_mail"
#     elif "ooh" in c or "outdoor" in c:
#         return "ooh_vendor"
#     elif "event" in c:
#         return "events_team"
#     elif "affiliate" in c:
#         return "affiliate_network"
#     elif "programmatic" in c:
#         return "dsp"
    
#     return channel

# """Proposer Node - Formats LLM-selected actions for execution."""
# import uuid
# from src.schemas.state import ExpeditionState
# from src.data_layer import get_strategy_data

# # Action templates - definitions only (LLM selects which to use)
# ACTION_TEMPLATES = {
#     # --- Budget Actions ---
#     "budget_increase": {
#         "action_type": "budget_change", 
#         "operation": "increase", 
#         "default_parameters": {"adjustment_pct": 20}, 
#         "estimated_impact": "Resume spend, capture demand", 
#         "risk_level": "medium"
#     },
#     "budget_decrease": {
#         "action_type": "budget_change", 
#         "operation": "decrease", 
#         "default_parameters": {"adjustment_pct": 20}, 
#         "estimated_impact": "Reduce wasteful spend", 
#         "risk_level": "low"
#     },
    
#     # --- Bid Actions ---
#     "bid_increase": {
#         "action_type": "bid_adjustment", 
#         "operation": "increase", 
#         "default_parameters": {"adjustment_pct": 15}, 
#         "estimated_impact": "Regain impression share", 
#         "risk_level": "medium"
#     },
#     "bid_decrease": {
#         "action_type": "bid_adjustment", 
#         "operation": "decrease", 
#         "default_parameters": {"adjustment_pct": 15}, 
#         "estimated_impact": "Reduce CPA, improve efficiency", 
#         "risk_level": "low"
#     },
    
#     # --- Pause/Enable ---
#     "pause_campaign": {
#         "action_type": "pause", 
#         "operation": "pause", 
#         "default_parameters": {"duration_hours": 24}, 
#         "estimated_impact": "Stop bleeding, reassess", 
#         "risk_level": "medium"
#     },
#     "enable_campaign": {
#         "action_type": "enable", 
#         "operation": "enable", 
#         "default_parameters": {}, 
#         "estimated_impact": "Resume paused activity", 
#         "risk_level": "low"
#     },
    
#     # --- Notifications ---
#     "creative_fatigue": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "default_parameters": {"team": "creative", "urgency": "high"}, 
#         "estimated_impact": "New creative in 2-3 days", 
#         "risk_level": "low"
#     },
#     "tracking_issue": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "default_parameters": {"team": "engineering", "urgency": "critical"}, 
#         "estimated_impact": "Fix tracking within hours", 
#         "risk_level": "low"
#     },
#     "platform_issue": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "default_parameters": {"team": "ops", "urgency": "medium"}, 
#         "estimated_impact": "Monitor platform status", 
#         "risk_level": "low"
#     },
#     "manual_review": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "default_parameters": {"team": "decision_science", "urgency": "medium"}, 
#         "estimated_impact": "Analyst review within 1 hour", 
#         "risk_level": "low"
#     },
    
#     # --- Fraud/Bot ---
#     "bot_traffic": {
#         "action_type": "exclusion", 
#         "operation": "block_ip", 
#         "default_parameters": {"list": "global_blocklist"}, 
#         "estimated_impact": "Stop invalid traffic spend", 
#         "risk_level": "medium"
#     },
#     "influencer_fraud": {
#         "action_type": "contract", 
#         "operation": "terminate", 
#         "default_parameters": {"reason": "fraud_clause"}, 
#         "estimated_impact": "Recover budget, blacklist creator", 
#         "risk_level": "high"
#     },
    
#     # --- Offline / TV / Podcast ---
#     "make_good": {
#         "action_type": "negotiation", 
#         "operation": "request_make_good", 
#         "default_parameters": {"inventory_type": "equivalent"}, 
#         "estimated_impact": "Recover lost GRPs", 
#         "risk_level": "low"
#     },
#     "partner_issue": {
#         "action_type": "communication", 
#         "operation": "contact_partner", 
#         "default_parameters": {"priority": "high"}, 
#         "estimated_impact": "Restore tracking or fix leakage", 
#         "risk_level": "low"
#     },
#     "vendor_delivery": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "default_parameters": {"team": "media_buying"}, 
#         "estimated_impact": "Vendor follow-up", 
#         "risk_level": "low"
#     },
#     "measurement_audit": {
#         "action_type": "notification", 
#         "operation": "alert", 
#         "default_parameters": {"team": "analytics"}, 
#         "estimated_impact": "Verify measurement accuracy", 
#         "risk_level": "low"
#     },
# }

# # Offline channel identifiers (for guardrails)
# OFFLINE_CHANNELS = {"tv", "podcast", "radio", "direct_mail", "ooh", "events"}


# def propose_actions(state: ExpeditionState) -> dict:
#     """
#     Convert LLM-selected actions into executable format.
    
#     The LLM (Explainer) has already selected appropriate actions based on its diagnosis.
#     This function simply:
#     1. Reads actions from diagnosis["actions"]
#     2. Validates they exist in our template catalog
#     3. Applies MMM guardrails
#     4. Formats for execution layer
#     """
#     print("\n🎯 Proposing Actions...")
#     diagnosis = state.get("diagnosis")
#     anomaly = state.get("selected_anomaly")
    
#     if not diagnosis: 
#         print("  ⚠️ No diagnosis available")
#         return {"proposed_actions": []}
    
#     channel = anomaly.get("channel", "unknown") if anomaly else "unknown"
    
#     # Get LLM-selected actions from diagnosis
#     llm_actions = diagnosis.get("actions", [])
    
#     if not llm_actions:
#         print("  ⚠️ No actions in diagnosis, using fallback")
#         llm_actions = [{"template_id": "manual_review", "reason": "No specific action recommended"}]
    
#     print(f"  📋 LLM selected {len(llm_actions)} actions")
    
#     # Convert LLM actions to executable format
#     actions = []
#     for llm_action in llm_actions:
#         template_id = llm_action.get("template_id", "manual_review")
        
#         # Validate template exists
#         if template_id not in ACTION_TEMPLATES:
#             print(f"    ⚠️ Unknown template '{template_id}', skipping")
#             continue
        
#         # Build action from template + LLM customization
#         action = _build_action(
#             channel=channel,
#             anomaly=anomaly,
#             template_id=template_id,
#             llm_reason=llm_action.get("reason", ""),
#             llm_parameters=llm_action.get("parameters", {}),
#             priority=llm_action.get("priority", "medium"),
#         )
#         actions.append(action)
#         print(f"    ✓ {template_id}: {llm_action.get('reason', '')[:50]}...")
    
#     # Fallback if no valid actions
#     if not actions:
#         actions.append(_build_action(channel, anomaly, "manual_review", "Fallback action", {}, "medium"))
    
#     # Apply MMM Guardrails
#     final_actions = _apply_guardrails(actions, channel, state)
    
#     print(f"  ✅ Final: {len(final_actions)} actions after guardrails")
    
#     return {"proposed_actions": final_actions}


# def _build_action(
#     channel: str, 
#     anomaly: dict, 
#     template_id: str, 
#     llm_reason: str,
#     llm_parameters: dict,
#     priority: str
# ) -> dict:
#     """Build an executable action from template + LLM customization."""
    
#     template = ACTION_TEMPLATES.get(template_id, ACTION_TEMPLATES["manual_review"])
    
#     # Merge LLM parameters with defaults (LLM params take precedence)
#     parameters = {**template.get("default_parameters", {}), **llm_parameters}
    
#     # Build estimated impact with LLM's reason
#     impact = template.get("estimated_impact", "Unknown")
#     if llm_reason:
#         impact = f"{impact}. Reason: {llm_reason}"
    
#     return {
#         "action_id": f"act_{uuid.uuid4().hex[:8]}",
#         "action_type": template.get("action_type", "notification"),
#         "platform": _get_platform(channel),
#         "resource_type": "campaign",
#         "resource_id": f"{channel}_campaign_001",
#         "operation": template.get("operation", "alert"),
#         "parameters": parameters,
#         "risk_level": template.get("risk_level", "medium"),
#         "estimated_impact": impact,
#         "requires_approval": template.get("risk_level", "medium") != "low",
#         "priority": priority,
#         "template_id": template_id,  # Keep for reference
#     }


# def _apply_guardrails(actions: list, channel: str, state: dict) -> list:
#     """
#     Apply MMM guardrails to proposed actions.
    
#     If channel is saturated, block budget increases.
#     """
#     try:
#         strategy = get_strategy_data()
        
#         # Get reference date from state
#         reference_date = None
#         if state.get("analysis_end_date"):
#             from datetime import datetime
#             reference_date = datetime.strptime(state["analysis_end_date"], "%Y-%m-%d")
        
#         mmm = strategy.get_mmm_guardrails(channel, reference_date=reference_date)
        
#         if not mmm:
#             return actions
        
#         marginal_roas = mmm.get("current_marginal_roas", 1.0)
#         recommendation = mmm.get("recommendation", "maintain")
        
#         filtered = []
#         for action in actions:
#             # Block budget INCREASES if channel is saturated
#             if action.get("action_type") == "budget_change" and action.get("operation") == "increase":
#                 if recommendation == "maintain" or marginal_roas < 1.0:
#                     print(f"    ⚠️ Guardrail: Blocked budget increase (saturated, ROAS: {marginal_roas:.2f})")
#                     # Convert to manual review instead
#                     action = _build_action(
#                         channel, {}, "manual_review",
#                         f"Budget increase blocked by guardrail - channel saturated (marginal ROAS: {marginal_roas:.2f})",
#                         {}, "high"
#                     )
            
#             filtered.append(action)
        
#         return filtered
        
#     except Exception as e:
#         print(f"    ⚠️ Guardrail check failed: {e}")
#         return actions


# def _get_platform(channel: str) -> str:
#     """Map channel to platform/executor name."""
#     c = channel.lower()
    
#     # Digital platforms
#     if "google" in c:
#         return "google_ads"
#     elif "meta" in c:
#         return "meta_ads"
#     elif "tiktok" in c:
#         return "tiktok_ads"
#     elif "linkedin" in c:
#         return "linkedin_ads"
#     elif "influencer" in c:
#         return "creatoriq"
    
#     # Offline platforms
#     elif "tv" in c:
#         return "tv_buying"
#     elif "podcast" in c:
#         return "podcast_network"
#     elif "radio" in c:
#         return "radio_buying"
#     elif "direct_mail" in c or "mail" in c:
#         return "direct_mail"
#     elif "ooh" in c or "outdoor" in c:
#         return "ooh_vendor"
#     elif "event" in c:
#         return "events_team"
#     elif "affiliate" in c:
#         return "affiliate_network"
#     elif "programmatic" in c:
#         return "dsp"
    
#     return channel

## <--------- Updated - 3/3 --------->
"""Proposer Node - Maps diagnosis to executable actions using LLM + keyword fallback."""
import uuid
import json
import re
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_llm_safe


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
    Proposer Node.
    
    Maps the diagnosis root cause to specific executable actions.
    
    Improvement #8: Now uses LLM as primary method for action mapping,
    with keyword matching as fallback. LLM receives the full template menu
    and selects appropriate actions based on diagnosis context.
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
    
    # Primary: LLM-based action mapping (Improvement #8)
    actions = _llm_action_mapping(diagnosis, anomaly)
    
    # Fallback: Keyword matching if LLM fails or returns nothing
    if not actions:
        print("  ⚠️ LLM mapping failed, using keyword fallback")
        actions = _keyword_action_mapping(root_cause, channel, anomaly)
    
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


def _llm_action_mapping(diagnosis: dict, anomaly: dict | None) -> list[dict]:
    """
    Use LLM (Tier 1) to intelligently map diagnosis to action templates.
    
    Improvement #8: Presents the full template menu to the LLM and asks
    it to select the most appropriate actions based on the diagnosis.
    """
    try:
        llm = get_llm_safe("tier1")
        
        # Build template menu for LLM
        template_menu = "\n".join([
            f"- {key}: {tmpl.get('description', tmpl.get('operation', key))}"
            for key, tmpl in ACTION_TEMPLATES.items()
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
        
        # Parse response
        content = response.content.strip()
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
        print(f"  ⚠️ LLM action mapping failed: {e}")
    
    return []


def _keyword_action_mapping(root_cause: str, channel: str, anomaly: dict | None) -> list[dict]:
    """Fallback keyword-based action mapping."""
    actions = []
    
    # 1. Competitor / Bidding
    if any(kw in root_cause for kw in ["competitor", "bidding", "auction", "cpc", "impression share"]):
        actions.append(_create_action("competitor_bidding", channel, anomaly))
    
    # 2. Creative / Content
    if any(kw in root_cause for kw in ["creative", "fatigue", "ad copy", "script", "video", "frequency"]):
        actions.append(_create_action("creative_fatigue", channel, anomaly))
    
    # 3. Technical / Tracking
    if any(kw in root_cause for kw in ["tracking", "pixel", "attribution", "measurement", "tag", "ios", "capi", "gtm"]):
        actions.append(_create_action("tracking_issue", channel, anomaly))
    
    # 4. Budget / Spend
    if any(kw in root_cause for kw in ["budget", "spend", "cap", "limit", "exhausted"]):
        actions.append(_create_action("budget_exhaustion", channel, anomaly))
    
    # 5. Platform Errors
    if any(kw in root_cause for kw in ["platform", "algorithm", "outage", "bug", "update"]):
        actions.append(_create_action("platform_issue", channel, anomaly))
    
    # 6. Saturation / Frequency
    if any(kw in root_cause for kw in ["saturation", "frequency", "overexposure", "lookalike"]):
        actions.append(_create_action("audience_saturation", channel, anomaly))

    # 7. Fraud / Bots
    if any(kw in root_cause for kw in ["bot", "fraud", "fake", "invalid", "click farm"]):
        if "influencer" in channel:
            actions.append(_create_action("influencer_fraud", channel, anomaly))
        else:
            actions.append(_create_action("bot_traffic", channel, anomaly))

    # 8. TV / Offline Issues
    if any(kw in root_cause for kw in ["preempt", "make-good", "nielsen", "tv spot", "grp", "delivery"]):
        actions.append(_create_action("make_good", channel, anomaly))

    # 9. Partner / Affiliate
    if any(kw in root_cause for kw in ["affiliate", "partner", "coupon", "leakage", "promo code"]):
        actions.append(_create_action("partner_issue", channel, anomaly))
    
    # 10. Schedule / Timing
    if any(kw in root_cause for kw in ["daypart", "schedule", "timing", "weekend", "holiday", "download"]):
        actions.append(_create_action("schedule_adjustment", channel, anomaly))
    
    return actions


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
    elif channel in ("tv", "radio", "ooh", "events", "podcast", "direct_mail"):
        return f"{channel}_platform"
    else:
        return channel

