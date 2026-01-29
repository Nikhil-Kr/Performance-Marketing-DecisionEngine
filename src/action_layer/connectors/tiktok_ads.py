"""
TikTok Ads API connector for production action execution.

STUB: Implement when you have TikTok Business API access at GoFundMe.

Prerequisites:
1. TikTok Business Center account
2. App with Ads Management permissions
3. Long-lived access token
4. Advertiser ID

Docs: https://business-api.tiktok.com/portal/docs
"""
from typing import Any

from ..interfaces.base import BaseActionExecutor


class TikTokAdsExecutor(BaseActionExecutor):
    """
    Production executor for TikTok Ads API.
    
    Supports:
    - Campaign budget changes
    - Bid adjustments
    - Campaign/ad group pause/enable
    
    TODO: Implement when you have API access at GoFundMe.
    """
    
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    
    def __init__(self):
        from src.utils.config import settings
        import httpx
        
        self.access_token = settings.tiktok_access_token
        self.advertiser_id = settings.tiktok_advertiser_id
        
        if not all([self.access_token, self.advertiser_id]):
            raise ValueError(
                "TikTok Ads credentials not configured. "
                "Set TIKTOK_ACCESS_TOKEN and TIKTOK_ADVERTISER_ID in .env"
            )
        
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Access-Token": self.access_token,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    
    @property
    def platform_name(self) -> str:
        return "tiktok_ads"
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "budget_change",
            "bid_adjustment",
            "pause",
            "enable",
        ]
    
    def execute(self, action: dict) -> dict[str, Any]:
        """
        Execute action via TikTok Ads API.
        
        Example for budget change:
        ```python
        response = self.client.post(
            "/campaign/update/",
            json={
                "advertiser_id": self.advertiser_id,
                "campaign_id": campaign_id,
                "budget": new_budget,  # In currency units
                "budget_mode": "BUDGET_MODE_DAY",
            }
        )
        ```
        """
        raise NotImplementedError(
            "TikTok Ads execution not yet implemented. "
            "See docstring for implementation pattern."
        )
    
    def validate(self, action: dict) -> tuple[bool, str]:
        """Validate action against TikTok Ads constraints."""
        action_type = action.get("action_type")
        
        if action_type not in self.supported_actions:
            return False, f"Unsupported action type for TikTok Ads: {action_type}"
        
        # TikTok has minimum budget of $20/day for some objectives
        if action_type == "budget_change":
            params = action.get("parameters", {})
            if params.get("new_budget_usd", 0) < 20:
                return False, "TikTok minimum daily budget is $20"
        
        return True, ""
    
    def preview(self, action: dict) -> dict[str, Any]:
        """Preview TikTok Ads changes."""
        raise NotImplementedError("Implement preview with real API")
    
    def rollback(self, execution_id: str) -> dict[str, Any]:
        """Rollback a TikTok Ads change."""
        raise NotImplementedError("Implement rollback with execution tracking")
    
    # =========================================================================
    # TikTok Ads Specific Methods (implement these)
    # =========================================================================
    
    def get_campaign(self, campaign_id: str) -> dict:
        """
        Fetch campaign details.
        
        Endpoint: GET /campaign/get/
        """
        raise NotImplementedError()
    
    def get_adgroup(self, adgroup_id: str) -> dict:
        """
        Fetch ad group details.
        
        Endpoint: GET /adgroup/get/
        """
        raise NotImplementedError()
    
    def update_campaign_budget(
        self, 
        campaign_id: str, 
        budget: float,
        budget_mode: str = "BUDGET_MODE_DAY"
    ) -> dict:
        """
        Update campaign budget.
        
        Endpoint: POST /campaign/update/
        
        budget_mode options:
        - BUDGET_MODE_DAY: Daily budget
        - BUDGET_MODE_TOTAL: Lifetime budget
        """
        raise NotImplementedError()
    
    def update_campaign_status(
        self, 
        campaign_id: str, 
        operation: str  # "enable" or "disable"
    ) -> dict:
        """
        Update campaign status.
        
        Endpoint: POST /campaign/status/update/
        """
        raise NotImplementedError()
    
    def update_adgroup_bid(
        self, 
        adgroup_id: str, 
        bid: float,
        bid_type: str = "BID"
    ) -> dict:
        """
        Update ad group bid.
        
        Endpoint: POST /adgroup/update/
        """
        raise NotImplementedError()
