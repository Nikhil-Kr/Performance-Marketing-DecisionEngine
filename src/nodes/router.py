"""Router Node - Routes anomalies to appropriate specialist."""
from src.schemas.state import ExpeditionState
from src.data_layer import get_marketing_data
from src.intelligence.models import get_llm_safe
from src.intelligence.prompts.router import ROUTER_SYSTEM_PROMPT, format_router_prompt


# Channel category mapping
PAID_MEDIA_CHANNELS = {
    "google_search", "google_pmax", "google_display", "google_youtube",
    "meta_ads", "tiktok_ads", "linkedin_ads", "programmatic", "affiliate"
}
INFLUENCER_CHANNELS = {"influencer_campaigns", "influencer"}
OFFLINE_CHANNELS = {"direct_mail", "tv", "radio", "ooh", "events", "podcast"}


def route_to_investigator(state: ExpeditionState) -> dict:
    """
    Router Node.
    
    Analyzes the selected anomaly and routes to the appropriate
    specialist investigator:
    - paid_media: Google, Meta, TikTok, etc.
    - influencer: Creator/influencer campaigns
    - offline: Direct mail, TV, events
    """
    print("\n🔀 Running Router...")
    
    anomaly = state.get("selected_anomaly")
    
    if not anomaly:
        print("  ⚠️ No anomaly to route")
        return {
            "channel_category": None,
            "current_node": "router",
            "error": "No anomaly selected for routing",
        }
    
    channel = anomaly.get("channel", "").lower()
    
    # First, try rule-based routing (fast, no LLM needed)
    if channel in PAID_MEDIA_CHANNELS:
        category = "paid_media"
    elif channel in INFLUENCER_CHANNELS:
        category = "influencer"
    elif channel in OFFLINE_CHANNELS:
        category = "offline"
    else:
        # Fall back to LLM for unknown channels
        category = _llm_route(anomaly)
    
    print(f"  📍 Routed to: {category.upper()}")
    
    return {
        "channel_category": category,
        "current_node": "router",
    }


def _llm_route(anomaly: dict) -> str:
    """Use LLM to classify unknown channels (Tier 1 - fast)."""
    try:
        llm = get_llm_safe("tier1")
        prompt = format_router_prompt(anomaly)
        
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        result = response.content.strip().upper()
        
        if "INFLUENCER" in result:
            return "influencer"
        elif "OFFLINE" in result:
            return "offline"
        else:
            return "paid_media"  # Default
            
    except Exception as e:
        print(f"  ⚠️ LLM routing failed: {e}, defaulting to paid_media")
        return "paid_media"


def get_route_decision(state: ExpeditionState) -> str:
    """
    Conditional edge function for LangGraph.
    
    Returns the next node name based on channel_category.
    """
    category = state.get("channel_category")
    
    if category == "influencer":
        return "investigate_influencer"
    elif category == "offline":
        return "investigate_offline"
    else:
        return "investigate_paid_media"
