"""
Action Layer Factory - Returns mock or production executors.

Usage:
    from src.action_layer import get_executor
    
    executor = get_executor("google_ads")  # Returns based on ACTION_LAYER_MODE
    result = executor.execute(action_payload)
    
To switch from mock to production:
    1. Set ACTION_LAYER_MODE=production in .env
    2. Set the appropriate API credentials
    3. That's it - all your code works unchanged
"""
import os
from functools import lru_cache

from .interfaces.base import BaseActionExecutor


@lru_cache()
def get_executor(platform: str = "mock") -> BaseActionExecutor:
    """
    Factory function for action executors.
    
    Args:
        platform: Platform name or "mock" for mock executor
        
    Returns:
        Appropriate executor based on ACTION_LAYER_MODE
    """
    mode = os.getenv("ACTION_LAYER_MODE", "mock")
    
    if mode == "mock":
        from .mock.executor import MockActionExecutor
        return MockActionExecutor()
    
    elif mode == "production":
        return _get_production_executor(platform)
    
    else:
        raise ValueError(f"Unknown ACTION_LAYER_MODE: {mode}")


def _get_production_executor(platform: str) -> BaseActionExecutor:
    """Get production executor for a specific platform."""
    
    if platform == "google_ads":
        from .connectors.google_ads import GoogleAdsExecutor
        return GoogleAdsExecutor()
    
    elif platform in ["meta_ads", "meta"]:
        from .connectors.meta_ads import MetaAdsExecutor
        return MetaAdsExecutor()
    
    elif platform in ["tiktok_ads", "tiktok"]:
        from .connectors.tiktok_ads import TikTokAdsExecutor
        return TikTokAdsExecutor()
    
    else:
        raise ValueError(f"No production executor for platform: {platform}")


def execute_action(action: dict) -> dict:
    """
    Convenience function to execute an action.
    
    Automatically routes to the correct executor based on the action's platform.
    """
    platform = action.get("platform", "mock")
    executor = get_executor(platform)
    return executor.execute(action)


def preview_action(action: dict) -> dict:
    """Convenience function to preview an action."""
    platform = action.get("platform", "mock")
    executor = get_executor(platform)
    return executor.preview(action)


def clear_cache():
    """Clear cached executors (useful for testing)."""
    get_executor.cache_clear()
