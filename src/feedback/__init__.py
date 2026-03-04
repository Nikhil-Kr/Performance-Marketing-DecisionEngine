"""
Feedback & Audit Logging for Project Expedition.

Improvement #7: Persistent feedback storage (thumbs up/down, approve/reject)
Improvement #10: Action audit trail with lifecycle tracking
"""
import csv
from datetime import datetime
from pathlib import Path

FEEDBACK_DIR = Path("data/feedback")
AUDIT_DIR = Path("data/audit")

FEEDBACK_CSV = FEEDBACK_DIR / "feedback_log.csv"
AUDIT_CSV = AUDIT_DIR / "action_log.csv"

FEEDBACK_FIELDS = [
    "timestamp", "anomaly_channel", "anomaly_metric", "diagnosis_root_cause",
    "feedback_type", "feedback_value", "diagnosis_confidence",
]

AUDIT_FIELDS = [
    "timestamp", "action_id", "anomaly_channel", "anomaly_metric",
    "action_type", "operation", "decision", "risk_level",
    "diagnosis_root_cause", "status",
]


def log_feedback(
    anomaly: dict,
    diagnosis: dict,
    feedback_type: str,  # "helpful" or "not_helpful"
) -> bool:
    """
    Log user feedback on a diagnosis.
    
    Called when user clicks 👍 or 👎 in the Diagnosis tab.
    """
    try:
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        
        row = {
            "timestamp": datetime.now().isoformat(),
            "anomaly_channel": anomaly.get("channel", "unknown"),
            "anomaly_metric": anomaly.get("metric", "unknown"),
            "diagnosis_root_cause": diagnosis.get("root_cause", "")[:200],
            "feedback_type": feedback_type,
            "feedback_value": 1 if feedback_type == "helpful" else -1,
            "diagnosis_confidence": diagnosis.get("confidence", 0),
        }
        
        file_exists = FEEDBACK_CSV.exists()
        with open(FEEDBACK_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FEEDBACK_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        
        return True
    except Exception as e:
        print(f"⚠️ Feedback logging failed: {e}")
        return False


def log_action_decision(
    anomaly: dict,
    diagnosis: dict,
    action: dict,
    decision: str,  # "approved" or "rejected"
) -> bool:
    """
    Log an action approval/rejection decision.
    
    Called when user clicks ✅ Approve or ❌ Reject in the Actions tab.
    """
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        
        row = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action.get("action_id", "unknown"),
            "anomaly_channel": anomaly.get("channel", "unknown"),
            "anomaly_metric": anomaly.get("metric", "unknown"),
            "action_type": action.get("action_type", "unknown"),
            "operation": action.get("operation", "unknown"),
            "decision": decision,
            "risk_level": action.get("risk_level", "unknown"),
            "diagnosis_root_cause": diagnosis.get("root_cause", "")[:200],
            "status": "approved" if decision == "approved" else "rejected",
        }
        
        file_exists = AUDIT_CSV.exists()
        with open(AUDIT_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        
        return True
    except Exception as e:
        print(f"⚠️ Audit logging failed: {e}")
        return False


def get_feedback_stats() -> dict:
    """Get summary stats from feedback log."""
    if not FEEDBACK_CSV.exists():
        return {"total": 0, "helpful": 0, "not_helpful": 0}
    
    try:
        import pandas as pd
        df = pd.read_csv(FEEDBACK_CSV)
        return {
            "total": len(df),
            "helpful": int((df["feedback_value"] > 0).sum()),
            "not_helpful": int((df["feedback_value"] < 0).sum()),
        }
    except Exception:
        return {"total": 0, "helpful": 0, "not_helpful": 0}


def get_audit_stats() -> dict:
    """Get summary stats from audit log."""
    if not AUDIT_CSV.exists():
        return {"total": 0, "approved": 0, "rejected": 0}
    
    try:
        import pandas as pd
        df = pd.read_csv(AUDIT_CSV)
        return {
            "total": len(df),
            "approved": int((df["decision"] == "approved").sum()),
            "rejected": int((df["decision"] == "rejected").sum()),
        }
    except Exception:
        return {"total": 0, "approved": 0, "rejected": 0}
