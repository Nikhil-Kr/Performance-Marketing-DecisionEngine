"""Abstract base class for action executors."""
from abc import ABC, abstractmethod
from typing import Any


class BaseActionExecutor(ABC):
    """
    Abstract interface for action execution.
    
    Implement this for each platform:
    - Mock implementations log actions without executing
    - Production implementations call real platform APIs
    """
    
    @abstractmethod
    def execute(self, action: dict) -> dict[str, Any]:
        """
        Execute an action on the platform.
        
        Args:
            action: Action payload with type, operation, parameters
            
        Returns:
            Result dict with status, message, and any platform response
        """
        pass
    
    @abstractmethod
    def validate(self, action: dict) -> tuple[bool, str]:
        """
        Validate an action before execution.
        
        Args:
            action: Action payload to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def preview(self, action: dict) -> dict[str, Any]:
        """
        Preview what an action would do without executing.
        
        Args:
            action: Action payload to preview
            
        Returns:
            Preview of expected changes
        """
        pass
    
    @abstractmethod
    def rollback(self, execution_id: str) -> dict[str, Any]:
        """
        Rollback a previously executed action.
        
        Args:
            execution_id: ID of the execution to rollback
            
        Returns:
            Result of rollback attempt
        """
        pass
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'google_ads', 'meta_ads')."""
        pass
    
    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """Return list of supported action types."""
        pass
