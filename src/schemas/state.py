"""LangGraph state and data model definitions."""
from typing import TypedDict, Annotated, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


# ============================================================================
# Pydantic Models (for validation)
# ============================================================================

class AnomalyInfo(BaseModel):
    """Information about a detected anomaly."""
    channel: str
    metric: str
    current_value: float
    expected_value: float
    deviation_pct: float
    severity: Literal["low", "medium", "high", "critical"]
    direction: Literal["spike", "drop"]
    detected_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def summary(self) -> str:
        """Human-readable summary."""
        return f"{self.severity.upper()} {self.direction} in {self.channel} {self.metric}: {self.deviation_pct:+.1f}%"


class HistoricalIncident(BaseModel):
    """Past incident retrieved from RAG."""
    incident_id: str
    similarity_score: float
    date: str
    channel: str
    anomaly_type: str
    root_cause: str
    resolution: str
    

class DiagnosisResult(BaseModel):
    """Root cause diagnosis from the Explainer node."""
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[str]
    recommended_actions: list[str]
    
    # Multi-persona explanations
    executive_summary: str = ""
    technical_details: str = ""


class ActionPayload(BaseModel):
    """Executable action for remediation."""
    action_id: str
    action_type: Literal[
        # Digital actions
        "budget_change", "bid_adjustment", "pause", "enable", "notification",
        # Offline actions
        "exclusion", "contract", "negotiation", "communication",
    ]
    platform: str
    resource_type: str
    resource_id: str
    operation: str
    parameters: dict[str, Any]
    estimated_impact: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool = True


class CriticValidation(BaseModel):
    """Critic node validation result."""
    is_valid: bool
    hallucination_risk: float = Field(ge=0.0, le=1.0)
    data_grounded: bool
    evidence_verified: bool
    issues: list[str] = []
    

# ============================================================================
# LangGraph State (TypedDict for graph)
# ============================================================================

class ExpeditionState(TypedDict):
    """
    Main state passed between LangGraph nodes.
    
    This is the shared "memory" that flows through the graph.
    Each node reads from and writes to this state.
    """
    # Conversation messages (for multi-turn interactions)
    messages: Annotated[list, add_messages]
    
    # Pre-Flight Check
    data_freshness: dict[str, str] | None
    preflight_passed: bool
    preflight_error: str | None
    
    # Analysis Time Window (User-selected date range)
    analysis_start_date: str | None  # ISO format: "2025-01-01"
    analysis_end_date: str | None    # ISO format: "2025-01-15"
    
    # Anomaly Detection
    anomalies: list[dict]  # List of AnomalyInfo as dicts
    selected_anomaly: dict | None
    
    # Router
    channel_category: str | None  # "paid_media", "influencer", "offline"
    
    # Investigation
    investigation_evidence: dict | None
    investigation_summary: str | None
    
    # Memory (RAG)
    historical_incidents: list[dict]  # List of HistoricalIncident as dicts
    rag_context: str | None
    
    # Explainer
    diagnosis: dict | None  # DiagnosisResult as dict
    
    # Proposer
    proposed_actions: list[dict]  # List of ActionPayload as dicts
    
    # Critic
    critic_validation: dict | None  # CriticValidation as dict
    validation_passed: bool
    
    # Action Layer
    selected_action: dict | None
    human_approved: bool
    execution_result: dict | None
    
    # Meta
    current_node: str
    error: str | None
    run_id: str | None
