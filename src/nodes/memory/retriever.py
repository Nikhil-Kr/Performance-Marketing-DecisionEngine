# """Memory Node - Retrieves historical context using RAG."""
# from typing import Any
# from datetime import datetime
# import chromadb
# from chromadb.config import Settings
# from pathlib import Path
# from src.schemas.state import ExpeditionState
# from src.intelligence.models import get_embeddings

# CHROMA_DIR = Path("data/embeddings")
# COLLECTION_NAME = "post_mortems"

# class VertexEmbeddingWrapper:
#     def __init__(self, embeddings):
#         self.embeddings = embeddings
#     def embed_query(self, text):
#         return self.embeddings.embed_query(text)

# def retrieve_historical_context(state: ExpeditionState) -> dict:
#     print("\n📚 Retrieving Historical Context (RAG)...")
    
#     # Defensive checks
#     if not isinstance(state, dict):
#         return {"historical_incidents": [], "rag_context": "State error."}

#     anomaly = state.get("selected_anomaly")
#     current_summary = str(state.get("investigation_summary") or "")
#     current_evidence = str(state.get("investigation_evidence") or "")

#     if not anomaly:
#         return {"historical_incidents": [], "rag_context": "No anomaly selected."}
    
#     # Contextual Query
#     query = f"{anomaly.get('channel', '')} {anomaly.get('metric', '')} {anomaly.get('direction', '')} {anomaly.get('root_cause', '')}"
    
#     # DETERMINE CUTOFF DATE FOR RAG FILTERING
#     # Priority: state's analysis_end_date > anomaly's detected_at > now
#     cutoff_date_str = None
    
#     # Try state's analysis_end_date first
#     if state.get("analysis_end_date"):
#         cutoff_date_str = state["analysis_end_date"]
#     # Fallback to anomaly's detected_at
#     elif anomaly.get("detected_at"):
#         cutoff_date_str = anomaly["detected_at"]
#     # Final fallback to today
#     else:
#         cutoff_date_str = datetime.now().strftime("%Y-%m-%d")
    
#     # Convert string date to integer (YYYYMMDD) for ChromaDB comparison
#     try:
#         cutoff_date_int = int(cutoff_date_str.replace('-', ''))
#     except (ValueError, AttributeError):
#         # Fallback to a future date if parsing fails so we don't filter everything out
#         cutoff_date_int = 20991231
    
#     print(f"  📅 RAG cutoff date: {cutoff_date_str} (only incidents before this)")
    
#     if not CHROMA_DIR.exists():
#         return {"historical_incidents": [], "rag_context": "Knowledge base offline."}

#     client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
    
#     raw_embeddings = get_embeddings()
#     embedding_fn = None
#     if raw_embeddings:
#         embedding_fn = VertexEmbeddingWrapper(raw_embeddings)
#         print("  🧠 RAG: Using Vertex AI Embeddings (768 dim)")
#     else:
#         print("  ⚠️ RAG: Using default embeddings")
    
#     try:
#         # Load collection without embedding function (we will embed query manually)
#         collection = client.get_collection(name=COLLECTION_NAME)
        
#         # Query with Integer Date Filtering
#         # ChromaDB Where clause: date_int <= cutoff_date_int
#         where_filter = {"date_int": {"$lte": cutoff_date_int}}
        
#         if embedding_fn:
#             query_vec = embedding_fn.embed_query(query)
#             results = collection.query(query_embeddings=[query_vec], n_results=3, where=where_filter)
#         else:
#             results = collection.query(query_texts=[query], n_results=3, where=where_filter)
        
#         incidents = []
#         context_parts = []
        
#         if results and results.get("metadatas") and results["metadatas"][0]:
#             metas = results["metadatas"][0]
#             distances = results["distances"][0] if results.get("distances") else [0]*len(metas)
            
#             for i, meta in enumerate(metas):
#                 similarity = 1.0 / (1.0 + distances[i])
                
#                 incidents.append({
#                     "incident_id": meta.get("incident_id"),
#                     "date": meta.get("date"),
#                     "channel": meta.get("channel"),
#                     "anomaly_type": meta.get("anomaly_type"),
#                     "root_cause": meta.get("root_cause"),
#                     "resolution": meta.get("resolution"),
#                     "similarity_score": round(similarity, 2)
#                 })
#                 context_parts.append(f"- {meta.get('date')}: {meta.get('anomaly_type')} in {meta.get('channel')}. Fix: {meta.get('resolution')}")
            
#             rag_text = "\n".join(context_parts)
#             print(f"  📖 Found {len(incidents)} historical incidents (prior to {cutoff_date_str})")
            
#             return {
#                 "historical_incidents": incidents,
#                 "rag_context": rag_text,
#                 "investigation_summary": f"{current_summary}\n\n## Historical Context (RAG)\n{rag_text}",
#                 "investigation_evidence": f"{current_evidence}\n\n## Historical Context (RAG)\n{rag_text}"
#             }
            
#     except Exception as e:
#         print(f"  ❌ RAG failed: {e}")
#         # Return empty context on failure to allow pipeline to proceed
#         return {
#             "historical_incidents": [], 
#             "rag_context": "Search error.",
#             "investigation_summary": current_summary,
#             "investigation_evidence": current_evidence
#         }

#     return {"historical_incidents": [], "rag_context": "No matches found."}

## <--------- V3 - store_resolution + get_recovery_curve, No Temporal Filtering (Previous Active) --------->

# ## <--------- Updated - 3/3 --------->
# V3 added store_resolution() and get_recovery_curve() (kept in V4 below) but removed
# the ChromaDB where={"date_int": {"$lte": cutoff_date_int}} clause, causing RAG to
# return incidents from AFTER the analysis date when analyzing historical anomalies.
# The query ran without any date filter: collection.query(n_results=5) — no where clause.

## <--------- V4 - RAG Temporal Filtering Restored (P5) --------->

"""
Memory Node - Retrieves historical context using RAG.

- P5: Restored ChromaDB temporal filtering — only incidents BEFORE the analysis cutoff
      date are returned, preventing future-incident contamination in historical analysis.
- V3 additions preserved: store_resolution() (RAG feedback loop) and get_recovery_curve().
"""
from datetime import datetime
from pathlib import Path
import csv
import chromadb
from chromadb.config import Settings
from src.schemas.state import ExpeditionState
from src.intelligence.models import get_embeddings

# Paths
CHROMA_DIR = Path("data/embeddings")
INCIDENTS_CSV = Path("data/post_mortems/incidents.csv")
COLLECTION_NAME = "post_mortems"


class VertexEmbeddingWrapper:
    """Wrapper to make LangChain embeddings compatible with ChromaDB."""

    def __init__(self, embeddings):
        self.embeddings = embeddings

    def embed_query(self, text):
        return self.embeddings.embed_query(text)


def get_rag_collection(client):
    """Get the ChromaDB collection."""
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"  ❌ Failed to load collection: {e}")
        return None


def retrieve_historical_context(state: ExpeditionState) -> dict:
    """
    Retrieve similar past incidents from vector store.

    P5: Only returns incidents dated BEFORE the analysis cutoff (from state's
    analysis_end_date or anomaly's detected_at). Prevents time-travel contamination
    where future incidents could influence historical analysis.
    """
    print("\n📚 Retrieving Historical Context (RAG)...")

    if not isinstance(state, dict):
        return {"historical_incidents": [], "rag_context": "State error."}

    anomaly = state.get("selected_anomaly")
    current_summary = str(state.get("investigation_summary") or "")
    current_evidence = str(state.get("investigation_evidence") or "")

    if not anomaly or not isinstance(anomaly, dict):
        return {"historical_incidents": [], "rag_context": "No valid anomaly selected."}

    # Construct search query
    query = (
        f"{anomaly.get('channel', '')} {anomaly.get('metric', '')} "
        f"{anomaly.get('direction', '')} {anomaly.get('root_cause', '')}"
    )

    # --- P5: Determine cutoff date for temporal filtering ---
    # Priority: state's analysis_end_date > anomaly's detected_at > today
    cutoff_date_str = (
        state.get("analysis_end_date")
        or anomaly.get("detected_at")
        or datetime.now().strftime("%Y-%m-%d")
    )

    # Convert YYYY-MM-DD to integer YYYYMMDD for ChromaDB $lte comparison
    try:
        cutoff_date_int = int(cutoff_date_str.replace("-", ""))
    except (ValueError, AttributeError):
        cutoff_date_int = 20991231  # Safety: don't filter out everything if parse fails

    print(f"  📅 RAG cutoff: {cutoff_date_str} (only incidents before this date)")

    if not CHROMA_DIR.exists():
        print("  ⚠️ Vector store not found. Run 'make init-rag'")
        incidents = _csv_keyword_search(anomaly, cutoff_date_str)
        return {
            "historical_incidents": incidents,
            "rag_context": _format_incidents_as_context(incidents),
        }

    # Initialize ChromaDB client
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    raw_embeddings = get_embeddings()
    embedding_fn = None
    if raw_embeddings:
        embedding_fn = VertexEmbeddingWrapper(raw_embeddings)
        print("  🧠 RAG: Using Vertex AI Embeddings (768 dim)")
    else:
        print("  ⚠️ RAG: Using default embeddings (384 dim)")

    collection = get_rag_collection(client)
    if not collection:
        incidents = _csv_keyword_search(anomaly, cutoff_date_str)
        return {
            "historical_incidents": incidents,
            "rag_context": _format_incidents_as_context(incidents),
        }

    # --- Query with temporal filter ---
    where_filter = {"date_int": {"$lte": cutoff_date_int}}

    try:
        if embedding_fn:
            query_embedding = embedding_fn.embed_query(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                where=where_filter,
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=5,
                where=where_filter,
            )

        incidents = _parse_chroma_results(results)
        print(f"  ✅ Found {len(incidents)} similar incidents (prior to {cutoff_date_str})")

    except Exception as e:
        print(f"  ⚠️ Vector search failed: {e}")
        incidents = _csv_keyword_search(anomaly, cutoff_date_str)

    rag_context = _format_incidents_as_context(incidents)

    return {
        "historical_incidents": incidents,
        "rag_context": rag_context,
        "investigation_summary": f"{current_summary}\n\n## Historical Context (RAG)\n{rag_context}" if incidents else current_summary,
        "investigation_evidence": f"{current_evidence}\n\n## Historical Context (RAG)\n{rag_context}" if incidents else current_evidence,
    }


def _parse_chroma_results(results: dict) -> list:
    """Parse ChromaDB query results into incident dicts."""
    incidents = []
    if not results or not results.get("documents"):
        return incidents
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
    distances = results["distances"][0] if results.get("distances") else [1.0] * len(documents)
    for doc, meta, dist in zip(documents, metadatas, distances):
        similarity = max(0, 1 - dist)
        incidents.append({
            "incident_id": meta.get("incident_id", "unknown"),
            "date": meta.get("date", "unknown"),
            "channel": meta.get("channel", "unknown"),
            "anomaly_type": meta.get("anomaly_type", "unknown"),
            "root_cause": meta.get("root_cause", doc[:200]),
            "resolution": meta.get("resolution", ""),
            "similarity_score": round(similarity, 2),
        })
    return incidents


def _csv_keyword_search(anomaly: dict, cutoff_date_str: str = None) -> list:
    """Fallback: Search incidents.csv by keyword matching, optionally date-filtered."""
    if not INCIDENTS_CSV.exists():
        return []
    try:
        import pandas as pd
        df = pd.read_csv(INCIDENTS_CSV)
        channel = anomaly.get("channel", "")
        metric = anomaly.get("metric", "")
        matches = df[
            df["channel"].str.contains(channel, case=False, na=False) |
            df["anomaly_type"].str.contains(metric, case=False, na=False) |
            df["root_cause"].str.contains(channel, case=False, na=False)
        ]
        # Apply date filter if cutoff provided
        if cutoff_date_str and "date" in matches.columns:
            matches = matches[matches["date"] <= cutoff_date_str]
        return matches.head(5).to_dict("records")
    except Exception as e:
        print(f"  ⚠️ CSV search failed: {e}")
        return []


def _format_incidents_as_context(incidents: list) -> str:
    """Format incidents as readable context string."""
    if not incidents:
        return "No similar historical incidents found."
    lines = ["## Similar Past Incidents\n"]
    for inc in incidents:
        lines.append(
            f"- **{inc.get('incident_id', 'N/A')}** ({inc.get('date', 'N/A')}) "
            f"[{inc.get('channel', 'N/A')}]: {inc.get('root_cause', 'N/A')} "
            f"→ Resolution: {inc.get('resolution', 'N/A')}"
        )
    return "\n".join(lines)


# ============================================================================
# Store Resolution (RAG Feedback Loop) — added in V3, preserved in V4
# ============================================================================

def store_resolution(anomaly: dict, diagnosis: dict, actions: list) -> bool:
    """
    Write an approved diagnosis back to the knowledge base.
    Called when user clicks Approve on an action.
    """
    print("  💾 Storing resolution to knowledge base...")
    try:
        new_incident = {
            "incident_id": f"INC-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "date_int": int(datetime.now().strftime("%Y%m%d")),
            "channel": anomaly.get("channel", "unknown"),
            "anomaly_type": f"{anomaly.get('metric', 'unknown')} {anomaly.get('direction', 'anomaly')}",
            "severity": anomaly.get("severity", "medium"),
            "root_cause": diagnosis.get("root_cause", "Unknown"),
            "resolution": "; ".join([a.get("operation", "") for a in actions[:3]]),
            "similarity_score": diagnosis.get("confidence", 0.5),
        }
        INCIDENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
        file_exists = INCIDENTS_CSV.exists()
        with open(INCIDENTS_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=new_incident.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(new_incident)
        print(f"  ✅ Stored as {new_incident['incident_id']}")
        _add_to_vector_store(new_incident)
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to store resolution: {e}")
        return False


def _add_to_vector_store(incident: dict) -> None:
    """Best-effort addition to ChromaDB vector store."""
    if not CHROMA_DIR.exists():
        return
    try:
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = get_rag_collection(client)
        if not collection:
            return
        doc_text = (
            f"Channel: {incident['channel']}. "
            f"Type: {incident['anomaly_type']}. "
            f"Root Cause: {incident['root_cause']}. "
            f"Resolution: {incident['resolution']}"
        )
        raw_embeddings = get_embeddings()
        if raw_embeddings:
            embedding = raw_embeddings.embed_query(doc_text)
            collection.add(
                ids=[incident["incident_id"]],
                documents=[doc_text],
                embeddings=[embedding],
                metadatas=[{k: v for k, v in incident.items() if isinstance(v, (str, int, float, bool))}],
            )
        else:
            collection.add(
                ids=[incident["incident_id"]],
                documents=[doc_text],
                metadatas=[{k: v for k, v in incident.items() if isinstance(v, (str, int, float, bool))}],
            )
        print(f"  🧠 Added to vector store: {incident['incident_id']}")
    except Exception as e:
        print(f"  ⚠️ Vector store addition failed (non-critical): {e}")


# ============================================================================
# Recovery Curves from Historical Data — added in V3, preserved in V4
# ============================================================================

def get_recovery_curve(anomaly_type: str, channel: str) -> dict | None:
    """
    Look up actual recovery timelines from resolved incidents.
    Used by the impact simulator for realistic projections.
    """
    if not INCIDENTS_CSV.exists():
        return None
    try:
        import pandas as pd
        df = pd.read_csv(INCIDENTS_CSV)
        matches = df[
            df["channel"].str.contains(channel, case=False, na=False) |
            df["anomaly_type"].str.contains(anomaly_type, case=False, na=False)
        ]
        if matches.empty:
            return None
        severity_map = {"critical": 5, "high": 3, "medium": 2, "low": 1}
        avg_severity = matches["severity"].map(severity_map).mean()
        if avg_severity >= 4:
            pattern, avg_days = "slow", 7
        elif avg_severity >= 2.5:
            pattern, avg_days = "medium", 3
        else:
            pattern, avg_days = "fast", 1
        return {
            "avg_days_to_resolve": avg_days,
            "recovery_pattern": pattern,
            "similar_count": len(matches),
            "similar_resolutions": matches["resolution"].head(3).tolist(),
        }
    except Exception as e:
        print(f"  ⚠️ Recovery curve lookup failed: {e}")
        return None
