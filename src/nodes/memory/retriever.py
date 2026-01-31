"""Memory Node - Retrieves historical context using RAG."""
from typing import Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
from pathlib import Path
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_embeddings

CHROMA_DIR = Path("data/embeddings")
COLLECTION_NAME = "post_mortems"

class VertexEmbeddingWrapper:
    def __init__(self, embeddings):
        self.embeddings = embeddings
    def embed_query(self, text):
        return self.embeddings.embed_query(text)

def retrieve_historical_context(state: ExpeditionState) -> dict:
    print("\n📚 Retrieving Historical Context (RAG)...")
    
    # Defensive checks
    if not isinstance(state, dict):
        return {"historical_incidents": [], "rag_context": "State error."}

    anomaly = state.get("selected_anomaly")
    current_summary = str(state.get("investigation_summary") or "")
    current_evidence = str(state.get("investigation_evidence") or "")

    if not anomaly:
        return {"historical_incidents": [], "rag_context": "No anomaly selected."}
    
    # Contextual Query
    query = f"{anomaly.get('channel', '')} {anomaly.get('metric', '')} {anomaly.get('direction', '')} {anomaly.get('root_cause', '')}"
    
    # DETERMINE CUTOFF DATE FOR RAG FILTERING
    # Priority: state's analysis_end_date > anomaly's detected_at > now
    cutoff_date_str = None
    
    # Try state's analysis_end_date first
    if state.get("analysis_end_date"):
        cutoff_date_str = state["analysis_end_date"]
    # Fallback to anomaly's detected_at
    elif anomaly.get("detected_at"):
        cutoff_date_str = anomaly["detected_at"]
    # Final fallback to today
    else:
        cutoff_date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Convert string date to integer (YYYYMMDD) for ChromaDB comparison
    try:
        cutoff_date_int = int(cutoff_date_str.replace('-', ''))
    except (ValueError, AttributeError):
        # Fallback to a future date if parsing fails so we don't filter everything out
        cutoff_date_int = 20991231
    
    print(f"  📅 RAG cutoff date: {cutoff_date_str} (only incidents before this)")
    
    if not CHROMA_DIR.exists():
        return {"historical_incidents": [], "rag_context": "Knowledge base offline."}

    client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
    
    raw_embeddings = get_embeddings()
    embedding_fn = None
    if raw_embeddings:
        embedding_fn = VertexEmbeddingWrapper(raw_embeddings)
        print("  🧠 RAG: Using Vertex AI Embeddings (768 dim)")
    else:
        print("  ⚠️ RAG: Using default embeddings")
    
    try:
        # Load collection without embedding function (we will embed query manually)
        collection = client.get_collection(name=COLLECTION_NAME)
        
        # Query with Integer Date Filtering
        # ChromaDB Where clause: date_int <= cutoff_date_int
        where_filter = {"date_int": {"$lte": cutoff_date_int}}
        
        if embedding_fn:
            query_vec = embedding_fn.embed_query(query)
            results = collection.query(query_embeddings=[query_vec], n_results=3, where=where_filter)
        else:
            results = collection.query(query_texts=[query], n_results=3, where=where_filter)
        
        incidents = []
        context_parts = []
        
        if results and results.get("metadatas") and results["metadatas"][0]:
            metas = results["metadatas"][0]
            distances = results["distances"][0] if results.get("distances") else [0]*len(metas)
            
            for i, meta in enumerate(metas):
                similarity = 1.0 / (1.0 + distances[i])
                
                incidents.append({
                    "incident_id": meta.get("incident_id"),
                    "date": meta.get("date"),
                    "channel": meta.get("channel"),
                    "anomaly_type": meta.get("anomaly_type"),
                    "root_cause": meta.get("root_cause"),
                    "resolution": meta.get("resolution"),
                    "similarity_score": round(similarity, 2)
                })
                context_parts.append(f"- {meta.get('date')}: {meta.get('anomaly_type')} in {meta.get('channel')}. Fix: {meta.get('resolution')}")
            
            rag_text = "\n".join(context_parts)
            print(f"  📖 Found {len(incidents)} historical incidents (prior to {cutoff_date_str})")
            
            return {
                "historical_incidents": incidents,
                "rag_context": rag_text,
                "investigation_summary": f"{current_summary}\n\n## Historical Context (RAG)\n{rag_text}",
                "investigation_evidence": f"{current_evidence}\n\n## Historical Context (RAG)\n{rag_text}"
            }
            
    except Exception as e:
        print(f"  ❌ RAG failed: {e}")
        # Return empty context on failure to allow pipeline to proceed
        return {
            "historical_incidents": [], 
            "rag_context": "Search error.",
            "investigation_summary": current_summary,
            "investigation_evidence": current_evidence
        }

    return {"historical_incidents": [], "rag_context": "No matches found."}