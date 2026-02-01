"""
Production connectors for marketing platform APIs.

Each connector implements BaseActionExecutor for a specific platform.
Import and use via the factory function in action_layer/__init__.py

Available connectors:
- GoogleAdsExecutor: Google Ads API
- MetaAdsExecutor: Meta (Facebook/Instagram) Marketing API
- TikTokAdsExecutor: TikTok Ads API
- LinkedInAdsExecutor: LinkedIn Marketing API
- ProgrammaticExecutor: DSP APIs (DV360, The Trade Desk)
- AffiliateExecutor: Affiliate network APIs
- OfflineExecutor: Notification-based for offline channels
"""

from .google_ads import GoogleAdsExecutor
from .meta_ads import MetaAdsExecutor
from .tiktok_ads import TikTokAdsExecutor
from .linkedin_ads import LinkedInAdsExecutor
from .programmatic import ProgrammaticExecutor
from .affiliate import AffiliateExecutor
from .offline import OfflineExecutor

__all__ = [
    "GoogleAdsExecutor",
    "MetaAdsExecutor",
    "TikTokAdsExecutor",
    "LinkedInAdsExecutor",
    "ProgrammaticExecutor",
    "AffiliateExecutor",
    "OfflineExecutor",
]