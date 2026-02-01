"""
Action Layer - Executes proposed actions on marketing platforms.

This module provides a clean abstraction for action execution:
- Mock mode: Logs actions without executing (for development/testing)
- Production mode: Calls real platform APIs

Usage:
    from src.action_layer import get_executor
    
    executor = get_executor("meta_ads")
    result = executor.execute(action_payload)
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces.base import BaseActionExecutor


def get_executor(platform: str) -> "BaseActionExecutor":
    """
    Factory function to get the appropriate executor for a platform.
    
    In mock mode: Always returns MockActionExecutor (logs without executing)
    In production mode: Returns platform-specific executor with real API calls
    
    Args:
        platform: Platform identifier (e.g., "google_ads", "meta_ads", "tv")
        
    Returns:
        BaseActionExecutor implementation for the platform
        
    Raises:
        ValueError: If platform is unknown in production mode
        
    Example:
        >>> executor = get_executor("meta_ads")
        >>> result = executor.execute({
        ...     "action_type": "budget_change",
        ...     "operation": "decrease",
        ...     "parameters": {"adjustment_pct": 20}
        ... })
    """
    from src.utils.config import settings
    
    # Normalize platform name
    platform = platform.lower().strip()
    
    # Mock mode - always use mock executor
    if settings.action_layer_mode == "mock":
        from .mock.executor import MockActionExecutor
        return MockActionExecutor()
    
    # Production mode - route to real executors
    # Digital advertising platforms
    if platform == "google_ads":
        from .connectors.google_ads import GoogleAdsExecutor
        return GoogleAdsExecutor()
    
    elif platform == "meta_ads":
        from .connectors.meta_ads import MetaAdsExecutor
        return MetaAdsExecutor()
    
    elif platform == "tiktok_ads":
        from .connectors.tiktok_ads import TikTokAdsExecutor
        return TikTokAdsExecutor()
    
    elif platform == "linkedin_ads":
        from .connectors.linkedin_ads import LinkedInAdsExecutor
        return LinkedInAdsExecutor()
    
    elif platform in ("programmatic", "dsp", "dv360", "ttd"):
        from .connectors.programmatic import ProgrammaticExecutor
        return ProgrammaticExecutor()
    
    elif platform in ("affiliate", "affiliate_network"):
        from .connectors.affiliate import AffiliateExecutor
        return AffiliateExecutor()
    
    elif platform == "creatoriq":
        from .connectors.creatoriq import CreatorIQExecutor
        return CreatorIQExecutor()
    
    # Offline channels - route to notification-based executor
    elif platform in ("tv", "tv_buying", "podcast", "podcast_network", "radio", 
                      "radio_buying", "direct_mail", "ooh", "ooh_vendor", 
                      "events", "events_team"):
        from .connectors.offline import OfflineExecutor
        return OfflineExecutor(channel=platform)
    
    # Notification-only platforms
    elif platform in ("slack", "email", "notification"):
        from .connectors.offline import OfflineExecutor
        return OfflineExecutor(channel="notification")
    
    else:
        raise ValueError(
            f"Unknown platform: {platform}. "
            f"Available platforms: google_ads, meta_ads, tiktok_ads, linkedin_ads, "
            f"programmatic, affiliate, creatoriq, tv, podcast, radio, direct_mail, ooh, events"
        )


def execute_action(action: dict) -> dict:
    """
    Convenience function to execute a single action.
    
    Automatically routes to the correct executor based on action["platform"].
    
    Args:
        action: Action payload with platform, action_type, operation, parameters
        
    Returns:
        Execution result dict with status, message, and details
    """
    platform = action.get("platform", "unknown")
    executor = get_executor(platform)
    return executor.execute(action)


def preview_action(action: dict) -> dict:
    """
    Preview what an action would do without executing.
    
    Args:
        action: Action payload to preview
        
    Returns:
        Preview dict with expected changes and impact
    """
    platform = action.get("platform", "unknown")
    executor = get_executor(platform)
    return executor.preview(action)


def validate_action(action: dict) -> tuple[bool, str]:
    """
    Validate an action before execution.
    
    Args:
        action: Action payload to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    platform = action.get("platform", "unknown")
    executor = get_executor(platform)
    return executor.validate(action)


# Platform registry for documentation/introspection
SUPPORTED_PLATFORMS = {
    # Digital advertising
    "google_ads": "Google Ads (Search, Display, YouTube, PMax)",
    "meta_ads": "Meta Ads (Facebook, Instagram)",
    "tiktok_ads": "TikTok Ads",
    "linkedin_ads": "LinkedIn Ads",
    "programmatic": "Programmatic DSP (DV360, The Trade Desk)",
    "affiliate": "Affiliate Networks (Impact, CJ, Rakuten)",
    "creatoriq": "CreatorIQ (Influencer management)",
    
    # Offline (notification-based)
    "tv": "TV Media Buying",
    "podcast": "Podcast Networks",
    "radio": "Radio Buying",
    "direct_mail": "Direct Mail Vendors",
    "ooh": "Out-of-Home Vendors",
    "events": "Events Team",
}


__all__ = [
    "get_executor",
    "execute_action",
    "preview_action",
    "validate_action",
    "SUPPORTED_PLATFORMS",
]