"""
Mock action executor for testing without real API calls.

Supports ALL action types defined in action_mapper.py.
Logs actions for review without making any real changes.
"""
import uuid
from datetime import datetime
from typing import Any

from ..interfaces.base import BaseActionExecutor


class MockActionExecutor(BaseActionExecutor):
    """
    Mock executor that logs actions without executing them.
    
    Used for:
    - Local development and testing
    - Demo purposes before having real API access
    - Validating action payloads
    - Reviewing proposed actions before going to production
    
    All actions are logged and can be reviewed, but no real
    changes are made to any platform.
    """
    
    def __init__(self):
        self._execution_log: list[dict] = []
    
    @property
    def platform_name(self) -> str:
        return "mock"
    
    @property
    def supported_actions(self) -> list[str]:
        """
        All action types from action_mapper.py ACTION_TEMPLATES.
        """
        return [
            # Budget & Bidding
            "budget_change",
            "bid_adjustment",
            
            # Campaign Control
            "pause",
            "enable",
            
            # Notifications
            "notification",
            
            # Fraud & Compliance
            "exclusion",
            "contract",
            
            # Offline / Vendor
            "negotiation",
            "communication",
        ]
    
    def execute(self, action: dict) -> dict[str, Any]:
        """
        Mock execute - logs the action without real execution.
        
        Returns a simulated success response that mimics what a real
        platform API would return.
        """
        execution_id = f"mock_exec_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        
        # Validate first
        is_valid, error = self.validate(action)
        if not is_valid:
            return {
                "status": "failed",
                "execution_id": execution_id,
                "timestamp": timestamp,
                "error": error,
                "action": action,
            }
        
        # Build descriptive message based on action type
        message = self._build_execution_message(action)
        
        # Log the execution
        log_entry = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "action": action,
            "status": "success",
            "message": message,
            "simulated_response": self._simulate_response(action),
        }
        
        self._execution_log.append(log_entry)
        
        # Print for visibility during development
        self._print_execution(action, execution_id)
        
        return {
            "status": "success",
            "execution_id": execution_id,
            "timestamp": timestamp,
            "message": message,
            "simulated_response": log_entry["simulated_response"],
        }
    
    def _build_execution_message(self, action: dict) -> str:
        """Build a descriptive message for the mock execution."""
        action_type = action.get("action_type", "unknown")
        platform = action.get("platform", "unknown")
        operation = action.get("operation", "unknown")
        params = action.get("parameters", {})
        resource_id = action.get("resource_id", "N/A")
        
        messages = {
            "budget_change": (
                f"[MOCK] Would {operation} budget by {params.get('adjustment_pct', 'N/A')}% "
                f"on {platform} for {resource_id}"
            ),
            "bid_adjustment": (
                f"[MOCK] Would {operation} bids by {params.get('adjustment_pct', 'N/A')}% "
                f"on {platform} for {resource_id}"
            ),
            "pause": (
                f"[MOCK] Would pause {action.get('resource_type', 'campaign')} "
                f"{resource_id} on {platform} for {params.get('duration_hours', 24)} hours"
            ),
            "enable": (
                f"[MOCK] Would enable {action.get('resource_type', 'campaign')} "
                f"{resource_id} on {platform}"
            ),
            "notification": (
                f"[MOCK] Would send {params.get('urgency', 'normal')} priority alert "
                f"to {params.get('team', 'team')} team"
            ),
            "exclusion": (
                f"[MOCK] Would add exclusion to {params.get('list', 'blocklist')} "
                f"on {platform}"
            ),
            "contract": (
                f"[MOCK] Would {operation} contract for {resource_id} "
                f"(reason: {params.get('reason', 'N/A')})"
            ),
            "negotiation": (
                f"[MOCK] Would {operation} with vendor for {platform} "
                f"(type: {params.get('inventory_type', 'N/A')})"
            ),
            "communication": (
                f"[MOCK] Would contact partner via {platform} "
                f"(priority: {params.get('priority', 'normal')})"
            ),
        }
        
        return messages.get(action_type, f"[MOCK] Would execute {action_type} on {platform}")
    
    def _print_execution(self, action: dict, execution_id: str) -> None:
        """Print execution details for development visibility."""
        action_type = action.get("action_type", "unknown")
        platform = action.get("platform", "unknown")
        operation = action.get("operation", "N/A")
        params = action.get("parameters", {})
        risk = action.get("risk_level", "unknown")
        
        # Emoji based on action type
        emoji_map = {
            "budget_change": "💰",
            "bid_adjustment": "📊",
            "pause": "⏸️",
            "enable": "▶️",
            "notification": "🔔",
            "exclusion": "🚫",
            "contract": "📝",
            "negotiation": "🤝",
            "communication": "📞",
        }
        emoji = emoji_map.get(action_type, "🎭")
        
        print(f"\n  {emoji} [MOCK EXECUTE] {action_type}")
        print(f"     ID: {execution_id}")
        print(f"     Platform: {platform}")
        print(f"     Operation: {operation}")
        print(f"     Parameters: {params}")
        print(f"     Risk Level: {risk}")
    
    def validate(self, action: dict) -> tuple[bool, str]:
        """Validate action payload structure."""
        # Required fields
        required_fields = ["action_type", "platform", "operation"]
        
        for field in required_fields:
            if field not in action:
                return False, f"Missing required field: {field}"
        
        # Validate action type
        if action["action_type"] not in self.supported_actions:
            return False, f"Unsupported action type: {action['action_type']}. Supported: {self.supported_actions}"
        
        # Type-specific validation
        action_type = action["action_type"]
        params = action.get("parameters", {})
        
        if action_type in ("budget_change", "bid_adjustment"):
            if "adjustment_pct" not in params:
                return False, f"{action_type} requires 'adjustment_pct' in parameters"
        
        if action_type == "notification":
            if "team" not in params:
                return False, "notification requires 'team' in parameters"
        
        return True, ""
    
    def preview(self, action: dict) -> dict[str, Any]:
        """Preview what the action would do."""
        action_type = action.get("action_type", "unknown")
        operation = action.get("operation", "unknown")
        params = action.get("parameters", {})
        resource_type = action.get("resource_type", "resource")
        resource_id = action.get("resource_id", "N/A")
        
        previews = {
            "budget_change": {
                "preview": f"Would {operation} budget by {params.get('adjustment_pct', 'N/A')}%",
                "affected_resource": f"{resource_type}: {resource_id}",
                "reversible": True,
            },
            "bid_adjustment": {
                "preview": f"Would {operation} bids by {params.get('adjustment_pct', 'N/A')}%",
                "affected_resource": f"{resource_type}: {resource_id}",
                "reversible": True,
            },
            "pause": {
                "preview": f"Would pause {resource_type} for {params.get('duration_hours', 24)} hours",
                "affected_resource": f"{resource_type}: {resource_id}",
                "reversible": True,
            },
            "enable": {
                "preview": f"Would enable {resource_type}",
                "affected_resource": f"{resource_type}: {resource_id}",
                "reversible": True,
            },
            "notification": {
                "preview": f"Would send {params.get('urgency', 'normal')} alert to {params.get('team', 'team')} team",
                "affected_resource": "Team notification",
                "reversible": False,
            },
            "exclusion": {
                "preview": f"Would add to {params.get('list', 'blocklist')}",
                "affected_resource": "Traffic exclusion list",
                "reversible": True,
            },
            "contract": {
                "preview": f"Would {operation} contract",
                "affected_resource": f"Contract: {resource_id}",
                "reversible": False,
            },
            "negotiation": {
                "preview": f"Would {operation} with vendor",
                "affected_resource": "Vendor relationship",
                "reversible": False,
            },
            "communication": {
                "preview": f"Would contact partner",
                "affected_resource": "Partner communication",
                "reversible": False,
            },
        }
        
        preview_data = previews.get(action_type, {
            "preview": f"Would execute {action_type}",
            "affected_resource": "Unknown",
            "reversible": False,
        })
        
        return {
            **preview_data,
            "estimated_impact": action.get("estimated_impact", "Unknown"),
            "risk_level": action.get("risk_level", "medium"),
            "requires_approval": action.get("requires_approval", True),
        }
    
    def rollback(self, execution_id: str) -> dict[str, Any]:
        """Mock rollback of an action."""
        # Find the original execution
        original = None
        for entry in self._execution_log:
            if entry["execution_id"] == execution_id:
                original = entry
                break
        
        if not original:
            return {
                "status": "failed",
                "error": f"Execution {execution_id} not found in log",
            }
        
        action = original["action"]
        action_type = action.get("action_type", "unknown")
        
        # Check if action is reversible
        non_reversible = ["notification", "contract", "negotiation", "communication"]
        if action_type in non_reversible:
            return {
                "status": "failed",
                "error": f"Action type '{action_type}' cannot be rolled back",
                "original_action": action,
            }
        
        return {
            "status": "success",
            "message": f"[MOCK] Would rollback execution {execution_id}",
            "original_action": action,
            "rollback_action": self._generate_rollback_action(action),
        }
    
    def _generate_rollback_action(self, original_action: dict) -> dict:
        """Generate the inverse action for rollback."""
        action_type = original_action.get("action_type")
        operation = original_action.get("operation")
        
        rollback = original_action.copy()
        
        # Invert operations
        if action_type == "budget_change":
            rollback["operation"] = "decrease" if operation == "increase" else "increase"
        elif action_type == "bid_adjustment":
            rollback["operation"] = "decrease" if operation == "increase" else "increase"
        elif action_type == "pause":
            rollback["action_type"] = "enable"
            rollback["operation"] = "enable"
        elif action_type == "enable":
            rollback["action_type"] = "pause"
            rollback["operation"] = "pause"
        
        return rollback
    
    def _simulate_response(self, action: dict) -> dict:
        """Simulate what a real API response might look like."""
        return {
            "platform": action.get("platform", "unknown"),
            "resource_id": action.get("resource_id", "unknown"),
            "changes_applied": action.get("parameters", {}),
            "effective_time": "immediate",
            "api_response_code": 200,
            "api_request_id": f"mock_req_{uuid.uuid4().hex[:12]}",
        }
    
    def get_execution_log(self) -> list[dict]:
        """Get all logged executions for review."""
        return self._execution_log.copy()
    
    def clear_log(self) -> None:
        """Clear the execution log."""
        self._execution_log = []
    
    def get_log_summary(self) -> dict:
        """Get summary statistics of the execution log."""
        if not self._execution_log:
            return {"total": 0, "by_type": {}, "by_platform": {}}
        
        by_type = {}
        by_platform = {}
        
        for entry in self._execution_log:
            action = entry.get("action", {})
            
            action_type = action.get("action_type", "unknown")
            by_type[action_type] = by_type.get(action_type, 0) + 1
            
            platform = action.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1
        
        return {
            "total": len(self._execution_log),
            "by_type": by_type,
            "by_platform": by_platform,
        }