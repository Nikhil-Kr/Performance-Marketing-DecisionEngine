"""
Memory Node - Retrieves historical context using RAG.
"""
from typing import Any
import chromadb
from chromadb.config import Settings
from pathlib import Path
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_embeddings
from src.utils.config import settings

# Paths
CHROMA_DIR = Path("data/embeddings")
COLLECTION_NAME = "post_mortems"

class VertexEmbeddingWrapper:
    """Wrapper to make LangChain embeddings compatible with ChromaDB."""
    
    def __init__(self, embeddings):
        self.embeddings = embeddings
    
    def embed_query(self, text):
        """Embed a single query string."""
        return self.embeddings.embed_query(text)

def get_rag_collection(client):
    """Get the ChromaDB collection."""
    # We do NOT pass embedding_function here to avoid compatibility issues.
    # We will embed queries manually.
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"  ❌ Failed to load collection: {e}")
        return None

def retrieve_historical_context(state: ExpeditionState) -> dict:
    """
    Retrieve similar past incidents from vector store.
    """
    print("\n📚 Retrieving Historical Context (RAG)...")
    
    # Defensive check: Ensure state is a dict
    if not isinstance(state, dict):
        print(f"  ⚠️ Error: State is not a dict, got {type(state)}")
        return {"historical_incidents": [], "rag_context": "State error."}

    anomaly = state.get("selected_anomaly")
    
    # Safely get summary and evidence, ensuring they are strings
    current_summary = str(state.get("investigation_summary") or "")
    current_evidence = str(state.get("investigation_evidence") or "")

    # Defensive check: Ensure anomaly is a dict
    if not anomaly or not isinstance(anomaly, dict):
        return {"historical_incidents": [], "rag_context": "No valid anomaly selected."}
    
    # Construct query
    query = f"{anomaly.get('channel', '')} {anomaly.get('metric', '')} {anomaly.get('direction', '')} {anomaly.get('root_cause', '')}"
    
    if not CHROMA_DIR.exists():
        print("  ⚠️ Vector store not found. Run 'make init-rag'")
        return {"historical_incidents": [], "rag_context": "Knowledge base offline."}

    # Initialize Client
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    
    # Setup Embeddings (Explicitly)
    raw_embeddings = get_embeddings()
    embedding_fn = None
    
    if raw_embeddings:
        embedding_fn = VertexEmbeddingWrapper(raw_embeddings)
        print("  🧠 RAG: Using Vertex AI Embeddings (768 dim)")
    else:
        print("  ⚠️ RAG: Using default embeddings (384 dim)")
        
    collection = get_rag_collection(client)
    
    if not collection:
        return {"historical_incidents": [], "rag_context": "Collection unavailable."}
        
    try:
        # Perform Query
        if embedding_fn:
            # Manual embedding (Robust method)
            query_vec = embedding_fn.embed_query(query)
            results = collection.query(
                query_embeddings=[query_vec],
                n_results=3
            )
        else:
            # Fallback (Likely to fail if dims mismatch)
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
        
        incidents = []
        context_parts = []
        
        # Validate results structure before accessing
        if results and isinstance(results, dict) and results.get("metadatas"):
            metas = results["metadatas"][0]
            distances = results["distances"][0] if results.get("distances") else [0]*len(metas)
            
            for i, meta in enumerate(metas):
                # Defensive check: Ensure meta is a dict
                if not isinstance(meta, dict):
                    continue

                # Calculate similarity score (1 - distance for cosine)
                similarity = 1.0 / (1.0 + distances[i])
                
                incident = {
                    "incident_id": meta.get("incident_id"),
                    "date": meta.get("date"),
                    "channel": meta.get("channel"),
                    "anomaly_type": meta.get("anomaly_type"),
                    "root_cause": meta.get("root_cause"),
                    "resolution": meta.get("resolution"),
                    "similarity_score": round(similarity, 2)
                }
                incidents.append(incident)
                
                context_parts.append(
                    f"- Incident {incident['incident_id']} ({incident['date']}): "
                    f"{incident['anomaly_type']} in {incident['channel']}. "
                    f"Cause: {incident['root_cause']}. Fix: {incident['resolution']}"
                )
            
            rag_text = "\n".join(context_parts)
            print(f"  📖 Found {len(incidents)} similar past incidents")
            
            # CRITICAL FIX: Append RAG context to BOTH summary (for Explainer) and evidence (for Critic)
            updated_summary = f"{current_summary}\n\n## Historical Context (RAG)\n{rag_text}"
            updated_evidence = f"{current_evidence}\n\n## Historical Context (RAG)\n{rag_text}"
            
            return {
                "historical_incidents": incidents,
                "rag_context": rag_text,
                "investigation_summary": updated_summary,
                "investigation_evidence": updated_evidence
            }
            
    except Exception as e:
        print(f"  ❌ ChromaDB search failed: {e}")
        import traceback
        traceback.print_exc()
        return {"historical_incidents": [], "rag_context": "Search error."}

    return {"historical_incidents": [], "rag_context": "No matches found."}