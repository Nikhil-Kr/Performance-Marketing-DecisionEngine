"""
Slack notifications for Expedition alerts.

Setup:
1. Create a Slack app at https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Add webhook to a channel
4. Copy webhook URL to .env as SLACK_WEBHOOK_URL
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_diagnosis_alert(
    anomaly: dict,
    diagnosis: dict,
    actions: list,
    channel_override: str = None,
    analysis_period: tuple = None,
) -> bool:
    """
    Send diagnosis summary to Slack.
    
    Args:
        anomaly: Anomaly data dict
        diagnosis: Diagnosis result dict
        actions: List of proposed actions
        channel_override: Override default webhook channel
        analysis_period: Optional tuple of (start_date, end_date) for context
        
    Returns:
        True if sent successfully
    """
    webhook_url = channel_override or SLACK_WEBHOOK_URL
    
    if not webhook_url:
        print("⚠️ SLACK_WEBHOOK_URL not configured in .env")
        return False
    
    if not HTTPX_AVAILABLE:
        print("⚠️ httpx not installed. Run: pip install httpx")
        return False
    
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }
    
    emoji = severity_emoji.get(anomaly.get("severity", ""), "⚪")
    confidence = diagnosis.get("confidence", 0)
    
    # Build Slack Block Kit message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Expedition Alert: {anomaly.get('channel', 'Unknown')}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Metric:*\n{anomaly.get('metric', 'N/A')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{anomaly.get('severity', 'N/A').upper()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Direction:*\n{anomaly.get('direction', 'N/A')} {anomaly.get('deviation_pct', 0):+.1f}%"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Confidence:*\n{confidence:.0%}"
                },
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎯 Root Cause:*\n{diagnosis.get('root_cause', 'Unknown')}"
            }
        },
    ]
    
    # Add evidence
    evidence = diagnosis.get("supporting_evidence", [])
    if evidence:
        evidence_text = "\n".join([f"• {e}" for e in evidence[:3]])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📊 Evidence:*\n{evidence_text}"
            }
        })
    
    # Add recommended actions
    if actions:
        action_text = "\n".join([
            f"• *{a.get('action_type', 'N/A')}*: {a.get('operation', 'N/A')} ({a.get('risk_level', 'N/A')} risk)"
            for a in actions[:3]
        ])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*💡 Recommended Actions:*\n{action_text}"
            }
        })
    
    # Add executive summary
    exec_summary = diagnosis.get("executive_summary", "")
    if exec_summary:
        blocks.append({
            "type": "divider"
        })
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📝 Executive Summary:*\n{exec_summary[:500]}"
            }
        })
    
    # Add timestamp with analysis period context
    timestamp_text = f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Expedition v0.1"
    if analysis_period:
        start_str = analysis_period[0].strftime('%Y-%m-%d') if hasattr(analysis_period[0], 'strftime') else str(analysis_period[0])
        end_str = analysis_period[1].strftime('%Y-%m-%d') if hasattr(analysis_period[1], 'strftime') else str(analysis_period[1])
        timestamp_text = f"📅 Analysis: {start_str} to {end_str} | {timestamp_text}"
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": timestamp_text
            }
        ]
    })
    
    payload = {"blocks": blocks}
    
    try:
        response = httpx.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10.0,
        )
        
        if response.status_code == 200:
            print("✅ Slack notification sent")
            return True
        else:
            print(f"❌ Slack error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Slack notification failed: {e}")
        return False


def send_batch_summary(
    results: list[dict],
    channel_override: str = None,
) -> bool:
    """
    Send batch processing summary to Slack.
    
    Args:
        results: List of batch diagnosis results
        channel_override: Override default webhook channel
        
    Returns:
        True if sent successfully
    """
    webhook_url = channel_override or SLACK_WEBHOOK_URL
    
    if not webhook_url or not HTTPX_AVAILABLE:
        return False
    
    total = len(results)
    validated = sum(1 for r in results if r.get("validation_passed"))
    
    # Count by severity
    severity_counts = {}
    for r in results:
        sev = r.get("anomaly", {}).get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    severity_text = " | ".join([f"{k.upper()}: {v}" for k, v in severity_counts.items()])
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Expedition Batch Summary",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Anomalies:*\n{total}"},
                {"type": "mrkdwn", "text": f"*Validated:*\n{validated}/{total}"},
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*By Severity:* {severity_text}"
            }
        },
        {"type": "divider"},
    ]
    
    # Add top 3 anomalies
    for i, r in enumerate(results[:3], 1):
        anomaly = r.get("anomaly", {})
        diagnosis = r.get("diagnosis", {})
        status = "✅" if r.get("validation_passed") else "⚠️"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{status} *{i}. {anomaly.get('channel', 'Unknown')} - {anomaly.get('metric', 'Unknown')}*\n{diagnosis.get('root_cause', 'N/A')[:100]}"
            }
        })
    
    if len(results) > 3:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_...and {len(results) - 3} more anomalies_"}
            ]
        })
    
    payload = {"blocks": blocks}
    
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        return response.status_code == 200
    except Exception:
        return False


def test_slack_connection() -> bool:
    """Test Slack webhook connection."""
    if not SLACK_WEBHOOK_URL:
        print("❌ SLACK_WEBHOOK_URL not set in .env")
        return False
    
    if not HTTPX_AVAILABLE:
        print("❌ httpx not installed")
        return False
    
    payload = {
        "text": "🧪 Expedition test message - Slack integration working!"
    }
    
    try:
        response = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=10.0)
        if response.status_code == 200:
            print("✅ Slack connection successful!")
            return True
        else:
            print(f"❌ Slack error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test the connection
    test_slack_connection()
