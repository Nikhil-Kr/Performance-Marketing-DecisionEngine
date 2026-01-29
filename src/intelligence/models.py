"""
Intelligence Layer - Gemini model management.
"""
from functools import lru_cache
from typing import Literal
import os
from pathlib import Path

from src.utils.config import settings

TierType = Literal["tier1", "tier2"]

# Check if Vertex AI package is available
try:
    from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False
    ChatVertexAI = None
    VertexAIEmbeddings = None


def _has_gcp_credentials() -> bool:
    """Check if GCP credentials are available."""
    # Check explicit credentials file
    if settings.google_application_credentials:
        creds_path = Path(settings.google_application_credentials)
        if creds_path.exists():
            return True
    
    # Check application default credentials
    default_creds = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    if default_creds.exists():
        return True
    
    # Check environment variable
    env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if env_creds and Path(env_creds).exists():
        return True
    
    return False


@lru_cache()
def get_llm(tier: TierType = "tier1"):
    """Get Gemini LLM for specified tier."""
    
    # Check if we can use real Vertex AI
    can_use_vertex = (
        VERTEX_AVAILABLE and 
        _has_gcp_credentials() and 
        settings.google_cloud_project
    )
    
    if not can_use_vertex:
        print(f"  ℹ️ Using MockLLM (tier: {tier})")
        return MockLLM(tier)
    
    try:
        model_name = (
            settings.gemini_tier1_model if tier == "tier1" 
            else settings.gemini_tier2_model
        )
        
        print(f"  🤖 Using Vertex AI: {model_name}")
        
        return ChatVertexAI(
            model=model_name,
            project=settings.google_cloud_project,
            location=settings.vertex_ai_location,
            temperature=0.1 if tier == "tier1" else 0.3,
            max_tokens=1024 if tier == "tier1" else 4096,
        )
    except Exception as e:
        print(f"  ⚠️ Vertex AI failed: {e}")
        print(f"  ℹ️ Falling back to MockLLM")
        return MockLLM(tier)


@lru_cache()
def get_embeddings():
    """Get embedding model for RAG."""
    if not VERTEX_AVAILABLE or not _has_gcp_credentials():
        return None
    
    try:
        return VertexAIEmbeddings(
            model_name=settings.embedding_model,
            project=settings.google_cloud_project,
            location=settings.vertex_ai_location,
        )
    except Exception:
        return None


def get_llm_safe(tier: TierType = "tier1"):
    """Get LLM with guaranteed fallback to MockLLM."""
    try:
        llm = get_llm(tier)
        if llm is None:
            return MockLLM(tier)
        return llm
    except Exception as e:
        print(f"  ⚠️ LLM error: {e}")
        return MockLLM(tier)


# ============================================================================
# Mock LLM for testing
# ============================================================================

class MockLLM:
    """Mock LLM for testing without GCP."""
    
    def __init__(self, tier: str = "tier1"):
        self.tier = tier
    
    def invoke(self, messages) -> "MockResponse":
        """Generate mock response based on context."""
        if isinstance(messages, str):
            prompt = messages
        elif isinstance(messages, list):
            prompt = str(messages[-1]) if messages else ""
        else:
            prompt = str(messages)
        
        prompt_lower = prompt.lower()
        
        if "classify" in prompt_lower or "route" in prompt_lower:
            return MockResponse("PAID_MEDIA")
        elif "investigate" in prompt_lower:
            return MockResponse(self._mock_investigation())
        elif "synthesize" in prompt_lower or "diagnosis" in prompt_lower:
            return MockResponse(self._mock_diagnosis())
        elif "validate" in prompt_lower or "triple-lock" in prompt_lower:
            return MockResponse(self._mock_validation())
        else:
            return MockResponse(f"[Mock {self.tier} response]")
    
    def _mock_investigation(self) -> str:
        return """
### Potential Root Causes
1. **Competitor Bidding Activity** - Confidence: High
   - Evidence: CPA increased while conversion rate remained stable
   - Counter-evidence: No major competitor campaign launches detected

2. **Audience Saturation** - Confidence: Medium
   - Evidence: Frequency metrics show increase over past 2 weeks

### Recommended Immediate Actions
- Monitor competitor auction insights for next 24 hours
- Consider increasing brand keyword bids by 15-20%

### Additional Data Needed
- Auction insights report for past 7 days
"""
    
    def _mock_diagnosis(self) -> str:
        return '''{
    "root_cause": "Increased competition in brand keyword auctions driving up CPCs",
    "confidence": 0.78,
    "supporting_evidence": [
        "CPA increased 35% while conversion rate stable",
        "Impression share dropped from 85% to 72%",
        "Average CPC increased by $0.45"
    ],
    "recommended_actions": [
        "Increase brand keyword bids by 20%",
        "Add competitor brand terms as negative keywords",
        "Launch brand defense campaign"
    ],
    "executive_summary": "A competitor has entered our brand keyword auction, driving up costs by 35%. Recommend defensive bid increase.",
    "director_summary": "We are seeing increased competition on brand terms. The CPA spike is due to higher CPCs, not conversion issues.",
    "marketer_summary": "Action required: In Google Ads, increase target CPA by 20%. Add competitor names to negative keyword list.",
    "technical_details": "Z-score analysis shows 2.8 sigma deviation in CPA."
}'''
    
    def _mock_validation(self) -> str:
        return '''{
    "is_valid": true,
    "hallucination_risk": 0.15,
    "data_grounded": true,
    "evidence_verified": true,
    "issues": [],
    "recommendations": "Diagnosis appears well-grounded in available data."
}'''


class MockResponse:
    """Mock response object."""
    def __init__(self, content: str):
        self.content = content