"""
LangGraph Definition for Project Expedition.

This is the main orchestration layer that connects all nodes
into a coherent agent workflow.

Architecture Flow:
Pre-Flight → Detect → Router → Investigator → Memory → Explainer → Critic ⟲ → Proposer
                         ↓
                    ┌────┴──────────┐
                    │       │       │
               Paid Media  Influencer  Offline
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.utils.logging import get_logger

logger = get_logger("graph")

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
# Constants
# ============================================================================

MAX_CRITIC_RETRIES = 2  # Maximum times explainer can retry after critic rejection


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
    """Route to appropriate specialist including offline channels."""
    category = state.get("channel_category", "paid_media")
    if category == "influencer":
        return "influencer"
    elif category == "offline":
        return "offline"
    return "paid_media"


def should_proceed_after_critic(state: ExpeditionState) -> Literal["proposer", "retry_explainer", "end"]:
    """
    Check if validation passed. If not, retry the explainer with critic feedback
    up to MAX_CRITIC_RETRIES times.
    
    Improvement #1: Critic now actually blocks and can trigger retry.
    """
    if state.get("validation_passed", False):
        return "proposer"
    
    # Check if we can retry
    retry_count = state.get("critic_retry_count", 0)
    if retry_count < MAX_CRITIC_RETRIES:
        # Get hallucination risk - only retry if risk is concerning but not hopeless
        validation = state.get("critic_validation", {})
        risk = validation.get("hallucination_risk", 1.0)
        
        if risk > 0.8:
            # Too risky, don't even bother retrying - escalate to human
            logger.warning("Risk too high (%.0f%%), escalating to human review", risk * 100)
            return "end"
        
        logger.info("Retrying explainer (attempt %d/%d)", retry_count + 1, MAX_CRITIC_RETRIES)
        return "retry_explainer"
    
    # Exhausted retries - proceed with low confidence flag
    logger.warning("Exhausted %d retries, proceeding with caution", MAX_CRITIC_RETRIES)
    return "proposer"


# ============================================================================
# Retry Node (bridges critic back to explainer)
# ============================================================================

def prepare_critic_retry(state: ExpeditionState) -> dict:
    """
    Prepare state for explainer retry by packaging critic feedback.
    Increments retry counter and formats feedback for the explainer.
    """
    validation = state.get("critic_validation", {})
    issues = validation.get("issues", [])
    recommendations = validation.get("recommendations", "")
    
    feedback = "CRITIC FEEDBACK (please address these issues):\n"
    for issue in issues:
        feedback += f"- {issue}\n"
    if recommendations:
        feedback += f"\nRecommendations: {recommendations}\n"
    
    return {
        "critic_retry_count": state.get("critic_retry_count", 0) + 1,
        "critic_feedback": feedback,
        "current_node": "retry_explainer",
    }


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
    
    # Investigators (now includes offline)
    workflow.add_node("paid_media", investigate_paid_media)
    workflow.add_node("influencer", investigate_influencer)
    workflow.add_node("offline", investigate_offline)
    
    # Memory (RAG)
    workflow.add_node("memory", retrieve_historical_context)
    
    # Explainer
    workflow.add_node("explainer", generate_explanation)
    
    # Critic
    workflow.add_node("critic", validate_diagnosis)
    
    # Critic retry bridge (Improvement #1)
    workflow.add_node("retry_explainer", prepare_critic_retry)
    
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
    
    # Router conditional (now includes offline)
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
    
    # Critic conditional (now with retry loop)
    workflow.add_conditional_edges(
        "critic",
        should_proceed_after_critic,
        {
            "proposer": "proposer",
            "retry_explainer": "retry_explainer",
            "end": END,
        }
    )
    
    # Retry loops back to explainer
    workflow.add_edge("retry_explainer", "explainer")
    
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
        "anomalies": [],
        "selected_anomaly": None,
        "correlated_anomalies": [],
        "channel_category": None,
        "investigation_evidence": None,
        "investigation_summary": None,
        "historical_incidents": [],
        "rag_context": None,
        "diagnosis": None,
        "proposed_actions": [],
        "critic_validation": None,
        "validation_passed": False,
        "critic_retry_count": 0,
        "critic_feedback": None,
        "selected_action": None,
        "human_approved": False,
        "execution_result": None,
        "analysis_start_date": None,
        "analysis_end_date": None,
        "current_node": "start",
        "error": None,
        "run_id": str(uuid.uuid4()),
    }
    
    # Apply any overrides
    if initial_state:
        state.update(initial_state)
    
    # Run the graph
    logger.info("=" * 60)
    logger.info("EXPEDITION AGENT STARTING")
    logger.info("=" * 60)

    final_state = expedition_graph.invoke(state)

    logger.info("=" * 60)
    logger.info("EXPEDITION COMPLETE")
    logger.info("=" * 60)
    
    return final_state


def stream_expedition(initial_state: dict | None = None):
    """
    Stream the Expedition agent node-by-node.

    Yields (node_name, state_update) tuples as each node completes,
    enabling real-time progress feedback in the UI.
    """
    import uuid

    state: ExpeditionState = {
        "messages": [],
        "data_freshness": None,
        "preflight_passed": False,
        "preflight_error": None,
        "anomalies": [],
        "selected_anomaly": None,
        "correlated_anomalies": [],
        "channel_category": None,
        "investigation_evidence": None,
        "investigation_summary": None,
        "historical_incidents": [],
        "rag_context": None,
        "diagnosis": None,
        "proposed_actions": [],
        "critic_validation": None,
        "validation_passed": False,
        "critic_retry_count": 0,
        "critic_feedback": None,
        "selected_action": None,
        "human_approved": False,
        "execution_result": None,
        "analysis_start_date": None,
        "analysis_end_date": None,
        "current_node": "start",
        "error": None,
        "run_id": str(uuid.uuid4()),
    }

    if initial_state:
        state.update(initial_state)

    logger.info("EXPEDITION AGENT STREAMING")

    for event in expedition_graph.stream(state):
        for node_name, update in event.items():
            logger.info("Completed node: %s", node_name)
            yield node_name, update


if __name__ == "__main__":
    # Quick test
    result = run_expedition()
    print("\nFinal State:")
    print(f"  Current Node: {result.get('current_node')}")
    print(f"  Error: {result.get('error')}")
    print(f"  Anomalies Found: {len(result.get('anomalies', []))}")
    print(f"  Critic Retries: {result.get('critic_retry_count', 0)}")
    if result.get('diagnosis'):
        print(f"  Diagnosis: {result['diagnosis'].get('root_cause', 'N/A')[:100]}...")

