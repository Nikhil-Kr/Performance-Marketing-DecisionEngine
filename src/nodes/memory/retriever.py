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
from src.utils.logging import get_logger

logger = get_logger("memory")

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
        logger.error("Failed to load collection: %s", e)
        return None


def retrieve_historical_context(state: ExpeditionState) -> dict:
    """
    Retrieve similar past incidents from vector store.

    P5: Only returns incidents dated BEFORE the analysis cutoff (from state's
    analysis_end_date or anomaly's detected_at). Prevents time-travel contamination
    where future incidents could influence historical analysis.
    """
    logger.info("Retrieving Historical Context (RAG)...")

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
    raw_cutoff = (
        state.get("analysis_end_date")
        or anomaly.get("detected_at")
        or datetime.now().strftime("%Y-%m-%d")
    )
    # Normalize to "YYYY-MM-DD" string (handles datetime objects)
    cutoff_date_str = (
        raw_cutoff.strftime("%Y-%m-%d") if hasattr(raw_cutoff, "strftime") else str(raw_cutoff)[:10]
    )

    # Convert YYYY-MM-DD to integer YYYYMMDD for ChromaDB $lte comparison
    try:
        cutoff_date_int = int(cutoff_date_str.replace("-", ""))
    except (ValueError, AttributeError):
        cutoff_date_int = 20991231  # Safety: don't filter out everything if parse fails

    logger.info("RAG cutoff: %s (only incidents before this date)", cutoff_date_str)

    if not CHROMA_DIR.exists():
        logger.warning("Vector store not found. Run 'make init-rag'")
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
        logger.info("RAG: Using Vertex AI Embeddings (768 dim)")
    else:
        logger.info("RAG: Using default embeddings (384 dim)")

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
        logger.info("Found %d similar incidents (prior to %s)", len(incidents), cutoff_date_str)

    except Exception as e:
        logger.error("Vector search failed: %s", e, exc_info=True)
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
        # L2 distance is unbounded [0, inf); convert to [0, 1] similarity
        similarity = 1.0 / (1.0 + dist)
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
        # Score each row by how many keyword criteria it matches (0-3)
        channel_match = df["channel"].str.contains(channel, case=False, na=False)
        metric_match = df["anomaly_type"].str.contains(metric, case=False, na=False)
        cause_match = df["root_cause"].str.contains(channel, case=False, na=False)
        df["_match_count"] = channel_match.astype(int) + metric_match.astype(int) + cause_match.astype(int)
        matches = df[df["_match_count"] > 0].copy()
        # Apply date filter if cutoff provided
        if cutoff_date_str and "date" in matches.columns:
            matches = matches[matches["date"] <= cutoff_date_str]
        # Compute a keyword-based similarity score (fraction of criteria matched)
        matches["similarity_score"] = (matches["_match_count"] / 3.0).round(2)
        matches = matches.sort_values("_match_count", ascending=False).head(5)
        matches = matches.drop(columns=["_match_count"])
        return matches.to_dict("records")
    except Exception as e:
        logger.error("CSV search failed: %s", e, exc_info=True)
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
    logger.info("Storing resolution to knowledge base...")
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
        logger.info("Stored as %s", new_incident['incident_id'])
        _add_to_vector_store(new_incident)
        return True
    except Exception as e:
        logger.error("Failed to store resolution: %s", e, exc_info=True)
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
        logger.info("Added to vector store: %s", incident['incident_id'])
    except Exception as e:
        logger.warning("Vector store addition failed (non-critical): %s", e)


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
        logger.error("Recovery curve lookup failed: %s", e, exc_info=True)
        return None
