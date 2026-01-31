"""
LangGraph Definition for Project Expedition.

This is the main orchestration layer that connects all nodes
into a coherent agent workflow.

Architecture Flow:
Pre-Flight → Detect → Router → Investigator → Memory → Explainer → Critic → Proposer
"""
from typing import Literal
from langgraph.graph import StateGraph, END

from src.schemas.state import ExpeditionState
from src.nodes.preflight import preflight_check, detect_anomalies
from src.nodes.router import route_to_investigator, get_route_decision
from src.nodes.investigators.paid_media import investigate_paid_media
from src.nodes.investigators.influencer import investigate_influencer
from src.nodes.investigators.offline import investigate_offline
from src.nodes.memory.retriever import retrieve_historical_context
from src.nodes.explainer.synthesizer import generate_explanation
from src.nodes.proposer.action_mapper import propose_actions
from src.nodes.critic.validator import validate_diagnosis


# ============================================================================
# Conditional Edge Functions
# ============================================================================

def should_continue_after_preflight(state: ExpeditionState) -> Literal["detect", "abort"]:
    """Check if pre-flight passed."""
    if state.get("preflight_passed", False):
        return "detect"
    return "abort"


def should_continue_after_detect(state: ExpeditionState) -> Literal["router", "no_anomalies"]:
    """Check if any anomalies were detected."""
    anomalies = state.get("anomalies", [])
    if anomalies:
        return "router"
    return "no_anomalies"


def route_investigator(state: ExpeditionState) -> Literal["paid_media", "influencer", "offline"]:
    """Route to appropriate specialist."""
    category = state.get("channel_category", "paid_media")
    if category == "influencer":
        return "influencer"
    elif category == "offline":
        return "offline"
    return "paid_media"


def should_proceed_after_critic(state: ExpeditionState) -> Literal["proposer", "end"]:
    """Check if validation passed."""
    if state.get("validation_passed", False):
        return "proposer"
    # For now, proceed anyway but log warning
    # In production, could retry or escalate
    return "proposer"


# ============================================================================
# Graph Construction
# ============================================================================

def build_expedition_graph() -> StateGraph:
    """
    Build the complete Expedition agent graph.
    
    Returns:
        Compiled StateGraph ready to run
    """
    # Initialize graph with state schema
    workflow = StateGraph(ExpeditionState)
    
    # ---- Add Nodes ----
    
    # Pre-Flight & Detection
    workflow.add_node("preflight", preflight_check)
    workflow.add_node("detect", detect_anomalies)
    workflow.add_node("abort", lambda s: {**s, "error": "Pre-flight check failed", "current_node": "abort"})
    workflow.add_node("no_anomalies", lambda s: {**s, "current_node": "complete", "error": None})
    
    # Router
    workflow.add_node("router", route_to_investigator)
    
    # Investigators
    workflow.add_node("paid_media", investigate_paid_media)
    workflow.add_node("influencer", investigate_influencer)
    workflow.add_node("offline", investigate_offline)
    
    # Memory (RAG)
    workflow.add_node("memory", retrieve_historical_context)
    
    # Explainer
    workflow.add_node("explainer", generate_explanation)
    
    # Critic
    workflow.add_node("critic", validate_diagnosis)
    
    # Proposer
    workflow.add_node("proposer", propose_actions)
    
    # ---- Set Entry Point ----
    workflow.set_entry_point("preflight")
    
    # ---- Add Edges ----
    
    # Pre-flight conditional
    workflow.add_conditional_edges(
        "preflight",
        should_continue_after_preflight,
        {
            "detect": "detect",
            "abort": "abort",
        }
    )
    
    # Detect conditional
    workflow.add_conditional_edges(
        "detect",
        should_continue_after_detect,
        {
            "router": "router",
            "no_anomalies": "no_anomalies",
        }
    )
    
    # Router conditional
    workflow.add_conditional_edges(
        "router",
        route_investigator,
        {
            "paid_media": "paid_media",
            "influencer": "influencer",
            "offline": "offline",
        }
    )
    
    # Linear flow through investigation
    workflow.add_edge("paid_media", "memory")
    workflow.add_edge("influencer", "memory")
    workflow.add_edge("offline", "memory")
    workflow.add_edge("memory", "explainer")
    workflow.add_edge("explainer", "critic")
    
    # Critic conditional
    workflow.add_conditional_edges(
        "critic",
        should_proceed_after_critic,
        {
            "proposer": "proposer",
            "end": END,
        }
    )
    
    # Terminal edges
    workflow.add_edge("proposer", END)
    workflow.add_edge("abort", END)
    workflow.add_edge("no_anomalies", END)
    
    # Compile and return
    return workflow.compile()


# ============================================================================
# Export
# ============================================================================

# Compiled graph - ready to use
expedition_graph = build_expedition_graph()


def run_expedition(initial_state: dict | None = None) -> dict:
    """
    Run the Expedition agent.
    
    Args:
        initial_state: Optional initial state overrides
        
    Returns:
        Final state after graph execution
    """
    import uuid
    
    # Default initial state
    state: ExpeditionState = {
        "messages": [],
        "data_freshness": None,
        "preflight_passed": False,
        "preflight_error": None,
        # Analysis Time Window
        "analysis_start_date": None,
        "analysis_end_date": None,
        # Anomaly Detection
        "anomalies": [],
        "selected_anomaly": None,
        "channel_category": None,
        "investigation_evidence": None,
        "investigation_summary": None,
        "historical_incidents": [],
        "rag_context": None,
        "diagnosis": None,
        "proposed_actions": [],
        "critic_validation": None,
        "validation_passed": False,
        "selected_action": None,
        "human_approved": False,
        "execution_result": None,
        "current_node": "start",
        "error": None,
        "run_id": str(uuid.uuid4()),
    }
    
    # Apply any overrides
    if initial_state:
        state.update(initial_state)
    
    # Run the graph
    print("\n" + "="*60)
    print("🧭 EXPEDITION AGENT STARTING")
    print("="*60)
    
    final_state = expedition_graph.invoke(state)
    
    print("\n" + "="*60)
    print("🏁 EXPEDITION COMPLETE")
    print("="*60)
    
    return final_state


if __name__ == "__main__":
    # Quick test
    result = run_expedition()
    print("\nFinal State:")
    print(f"  Current Node: {result.get('current_node')}")
    print(f"  Error: {result.get('error')}")
    print(f"  Anomalies Found: {len(result.get('anomalies', []))}")
    if result.get('diagnosis'):
        print(f"  Diagnosis: {result['diagnosis'].get('root_cause', 'N/A')[:100]}...")
