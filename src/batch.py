"""
Batch processing for multiple anomalies.

Run with: python -m src.batch
"""
from datetime import datetime
from src.graph import run_expedition
from src.data_layer import get_marketing_data, get_influencer_data


def run_batch_diagnosis(
    max_anomalies: int = 5,
    min_severity: str = "low",
    send_notifications: bool = False,
) -> list[dict]:
    """
    Process multiple anomalies in sequence.
    
    Args:
        max_anomalies: Maximum number of anomalies to process
        min_severity: Minimum severity to process ("low", "medium", "high", "critical")
        send_notifications: Whether to send Slack notifications
        
    Returns:
        List of diagnosis results
    """
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    min_severity_level = severity_order.get(min_severity, 3)
    
    # Get all anomalies
    print("📊 Loading data sources...")
    marketing = get_marketing_data()
    influencer = get_influencer_data()
    
    all_anomalies = marketing.get_anomalies() + influencer.get_anomalies()
    
    # Filter by severity
    filtered_anomalies = [
        a for a in all_anomalies 
        if severity_order.get(a.get("severity", "low"), 3) <= min_severity_level
    ]
    
    if not filtered_anomalies:
        print("✅ No anomalies detected matching criteria")
        return []
    
    print(f"\n🚨 Found {len(filtered_anomalies)} anomalies (filtered from {len(all_anomalies)} total)")
    print(f"   Processing top {min(len(filtered_anomalies), max_anomalies)}...\n")
    
    results = []
    
    for i, anomaly in enumerate(filtered_anomalies[:max_anomalies], 1):
        print(f"\n{'='*60}")
        print(f"🔍 ANOMALY {i}/{min(len(filtered_anomalies), max_anomalies)}")
        print(f"{'='*60}")
        print(f"   Channel:   {anomaly['channel']}")
        print(f"   Metric:    {anomaly['metric']}")
        print(f"   Severity:  {anomaly['severity'].upper()}")
        print(f"   Direction: {anomaly['direction']} ({anomaly.get('deviation_pct', 0):+.1f}%)")
        
        # Run expedition with this specific anomaly
        result = run_expedition({
            "anomalies": [anomaly],
            "selected_anomaly": anomaly,
        })
        
        diagnosis_result = {
            "anomaly": anomaly,
            "diagnosis": result.get("diagnosis"),
            "proposed_actions": result.get("proposed_actions", []),
            "validation_passed": result.get("validation_passed", False),
            "historical_incidents": result.get("historical_incidents", []),
            "timestamp": datetime.now().isoformat(),
        }
        
        results.append(diagnosis_result)
        
        # Send notification if enabled
        if send_notifications and result.get("diagnosis"):
            try:
                from src.notifications.slack import send_diagnosis_alert
                send_diagnosis_alert(
                    anomaly=anomaly,
                    diagnosis=result["diagnosis"],
                    actions=result.get("proposed_actions", [])
                )
                print("   📤 Slack notification sent")
            except ImportError:
                print("   ⚠️ Slack notifications not configured")
            except Exception as e:
                print(f"   ❌ Notification failed: {e}")
    
    # Print summary
    print_batch_summary(results)
    
    return results


def print_batch_summary(results: list[dict]) -> None:
    """Print a summary of batch processing results."""
    print(f"\n{'='*60}")
    print("📋 BATCH SUMMARY")
    print(f"{'='*60}\n")
    
    validated = sum(1 for r in results if r["validation_passed"])
    
    print(f"Total Processed: {len(results)}")
    print(f"Validated:       {validated}/{len(results)}")
    print()
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["validation_passed"] else "⚠️"
        anomaly = r["anomaly"]
        diagnosis = r.get("diagnosis", {})
        
        print(f"{status} {i}. [{anomaly.get('severity', 'N/A').upper()}] {anomaly['channel']} - {anomaly['metric']}")
        
        if diagnosis:
            root_cause = diagnosis.get("root_cause", "N/A")
            confidence = diagnosis.get("confidence", 0)
            print(f"      Confidence: {confidence:.0%}")
            print(f"      Root cause: {root_cause[:70]}{'...' if len(root_cause) > 70 else ''}")
        
        actions = r.get("proposed_actions", [])
        if actions:
            print(f"      Actions: {len(actions)} proposed")
        print()


def generate_batch_report(results: list[dict], output_path: str = "batch_report.md") -> str:
    """Generate a markdown report from batch results."""
    lines = [
        "# Expedition Batch Diagnosis Report",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\nTotal Anomalies Processed: {len(results)}",
        "",
        "---",
        "",
    ]
    
    for i, r in enumerate(results, 1):
        anomaly = r["anomaly"]
        diagnosis = r.get("diagnosis", {})
        actions = r.get("proposed_actions", [])
        
        lines.extend([
            f"## {i}. {anomaly['channel']} - {anomaly['metric']}",
            "",
            f"**Severity:** {anomaly.get('severity', 'N/A').upper()}",
            f"**Direction:** {anomaly.get('direction', 'N/A')} ({anomaly.get('deviation_pct', 0):+.1f}%)",
            f"**Validation:** {'✅ Passed' if r['validation_passed'] else '⚠️ Review Needed'}",
            "",
        ])
        
        if diagnosis:
            lines.extend([
                "### Diagnosis",
                "",
                f"**Root Cause:** {diagnosis.get('root_cause', 'N/A')}",
                "",
                f"**Confidence:** {diagnosis.get('confidence', 0):.0%}",
                "",
                "**Evidence:**",
            ])
            for evidence in diagnosis.get("supporting_evidence", []):
                lines.append(f"- {evidence}")
            
            lines.extend([
                "",
                "### Executive Summary",
                "",
                diagnosis.get("executive_summary", "N/A"),
                "",
            ])
        
        if actions:
            lines.extend([
                "### Recommended Actions",
                "",
            ])
            for j, action in enumerate(actions, 1):
                lines.append(f"{j}. **{action.get('action_type', 'N/A')}**: {action.get('operation', 'N/A')} ({action.get('risk_level', 'N/A')} risk)")
            lines.append("")
        
        lines.extend(["---", ""])
    
    report = "\n".join(lines)
    
    with open(output_path, "w") as f:
        f.write(report)
    
    print(f"📄 Report saved to {output_path}")
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run batch diagnosis on anomalies")
    parser.add_argument("--max", type=int, default=5, help="Max anomalies to process")
    parser.add_argument("--severity", type=str, default="low", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--notify", action="store_true", help="Send Slack notifications")
    parser.add_argument("--report", type=str, help="Generate markdown report to file")
    
    args = parser.parse_args()
    
    results = run_batch_diagnosis(
        max_anomalies=args.max,
        min_severity=args.severity,
        send_notifications=args.notify,
    )
    
    if args.report and results:
        generate_batch_report(results, args.report)
