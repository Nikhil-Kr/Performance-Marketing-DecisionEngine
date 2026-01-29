"""Mock action executor for testing without real API calls."""
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
        return [
            "budget_change",
            "bid_adjustment",
            "pause",
            "enable",
            "notification",
        ]
    
    def execute(self, action: dict) -> dict[str, Any]:
        """
        Mock execute - logs the action without real execution.
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
        
        # Log the execution
        log_entry = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "action": action,
            "status": "success",
            "message": f"[MOCK] Would execute {action.get('action_type')} on {action.get('platform')}",
            "simulated_response": self._simulate_response(action),
        }
        
        self._execution_log.append(log_entry)
        
        print(f"  🎭 [MOCK EXECUTE] {action.get('action_type', 'unknown')} on {action.get('platform', 'unknown')}")
        print(f"     Resource: {action.get('resource_id', 'N/A')}")
        print(f"     Operation: {action.get('operation', 'N/A')}")
        print(f"     Parameters: {action.get('parameters', {})}")
        
        return {
            "status": "success",
            "execution_id": execution_id,
            "timestamp": timestamp,
            "message": log_entry["message"],
            "simulated_response": log_entry["simulated_response"],
        }
    
    def validate(self, action: dict) -> tuple[bool, str]:
        """Validate action payload structure."""
        required_fields = ["action_type", "platform", "operation"]
        
        for field in required_fields:
            if field not in action:
                return False, f"Missing required field: {field}"
        
        if action["action_type"] not in self.supported_actions:
            return False, f"Unsupported action type: {action['action_type']}"
        
        return True, ""
    
    def preview(self, action: dict) -> dict[str, Any]:
        """Preview what the action would do."""
        action_type = action.get("action_type", "unknown")
        operation = action.get("operation", "unknown")
        params = action.get("parameters", {})
        
        previews = {
            "budget_change": f"Would {operation} budget by {params.get('adjustment_pct', 'N/A')}%",
            "bid_adjustment": f"Would {operation} bids by {params.get('adjustment_pct', 'N/A')}%",
            "pause": f"Would pause {action.get('resource_type', 'resource')} {action.get('resource_id', 'N/A')}",
            "enable": f"Would enable {action.get('resource_type', 'resource')} {action.get('resource_id', 'N/A')}",
            "notification": f"Would send {params.get('urgency', 'normal')} alert to {params.get('team', 'team')}",
        }
        
        return {
            "preview": previews.get(action_type, f"Would execute {action_type}"),
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
                "error": f"Execution {execution_id} not found",
            }
        
        return {
            "status": "success",
            "message": f"[MOCK] Would rollback execution {execution_id}",
            "original_action": original["action"],
        }
    
    def _simulate_response(self, action: dict) -> dict:
        """Simulate what a real API response might look like."""
        return {
            "platform": action.get("platform", "unknown"),
            "resource_id": action.get("resource_id", "unknown"),
            "changes_applied": action.get("parameters", {}),
            "effective_time": "immediate",
            "api_response_code": 200,
        }
    
    def get_execution_log(self) -> list[dict]:
        """Get all logged executions for review."""
        return self._execution_log.copy()
    
    def clear_log(self) -> None:
        """Clear the execution log."""
        self._execution_log = []
