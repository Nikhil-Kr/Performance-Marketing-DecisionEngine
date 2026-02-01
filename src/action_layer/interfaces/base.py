"""Abstract base class for action executors."""
from abc import ABC, abstractmethod
from typing import Any


class BaseActionExecutor(ABC):
    """
    Abstract interface for action execution.
    
    Implement this for each platform:
    - Mock implementations log actions without executing
    - Production implementations call real platform APIs
    
    All executors must implement:
    - execute(): Run the action
    - validate(): Check action validity before execution
    - preview(): Show what would happen without executing
    - rollback(): Undo a previous execution (if possible)
    - platform_name: Identifier for this platform
    - supported_actions: List of action types this executor handles
    """
    
    @abstractmethod
    def execute(self, action: dict) -> dict[str, Any]:
        """
        Execute an action on the platform.
        
        Args:
            action: Action payload with structure:
                {
                    "action_id": "act_xxx",
                    "action_type": "budget_change",
                    "platform": "google_ads",
                    "resource_type": "campaign",
                    "resource_id": "campaign_123",
                    "operation": "increase",
                    "parameters": {"adjustment_pct": 20},
                    "risk_level": "medium",
                    "estimated_impact": "Resume spend...",
                    "requires_approval": True,
                }
                
        Returns:
            Result dict with:
                {
                    "status": "success" | "failed",
                    "execution_id": "exec_xxx",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "message": "Action executed successfully",
                    "error": None | "Error message",
                    ...platform-specific fields
                }
        """
        pass
    
    @abstractmethod
    def validate(self, action: dict) -> tuple[bool, str]:
        """
        Validate an action before execution.
        
        Checks:
        - Required fields are present
        - Action type is supported
        - Parameters are within acceptable ranges
        - Platform-specific constraints
        
        Args:
            action: Action payload to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, "")
            If invalid: (False, "Descriptive error message")
        """
        pass
    
    @abstractmethod
    def preview(self, action: dict) -> dict[str, Any]:
        """
        Preview what an action would do without executing.
        
        Useful for:
        - Showing users expected changes before approval
        - Validating action logic
        - Calculating expected impact
        
        Args:
            action: Action payload to preview
            
        Returns:
            Preview dict with:
                {
                    "preview": "Would increase budget by 20%",
                    "current_value": 1000,
                    "new_value": 1200,
                    "estimated_impact": "Resume spend...",
                    "risk_level": "medium",
                    "requires_approval": True,
                    "reversible": True,
                }
        """
        pass
    
    @abstractmethod
    def rollback(self, execution_id: str) -> dict[str, Any]:
        """
        Rollback a previously executed action.
        
        Not all actions are reversible. For irreversible actions,
        return an error explaining why.
        
        Args:
            execution_id: ID of the execution to rollback
            
        Returns:
            Result dict with:
                {
                    "status": "success" | "failed",
                    "message": "Rolled back successfully" | "Cannot rollback...",
                    "original_action": {...},
                    "rollback_action": {...},
                }
        """
        pass
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Return the platform identifier.
        
        Examples: 'google_ads', 'meta_ads', 'mock', 'offline_tv'
        """
        pass
    
    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """
        Return list of supported action types.
        
        Examples: ['budget_change', 'bid_adjustment', 'pause', 'enable']
        """
        pass
    
    # =========================================================================
    # Optional helper methods (can be overridden)
    # =========================================================================
    
    def supports_action(self, action_type: str) -> bool:
        """Check if this executor supports a specific action type."""
        return action_type in self.supported_actions
    
    def get_action_schema(self, action_type: str) -> dict:
        """
        Get the expected schema for a specific action type.
        
        Override in subclasses to provide platform-specific schemas.
        """
        return {
            "action_type": action_type,
            "platform": self.platform_name,
            "resource_type": "campaign",
            "resource_id": "string",
            "operation": "string",
            "parameters": {},
        }