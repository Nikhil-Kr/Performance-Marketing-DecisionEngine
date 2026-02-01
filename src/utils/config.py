# """Configuration management for Expedition."""
# import os
# from functools import lru_cache
# from pathlib import Path
# from typing import Literal

# from pydantic_settings import BaseSettings
# from dotenv import load_dotenv

# # Load .env file
# load_dotenv()


# class Settings(BaseSettings):
#     """Application settings loaded from environment variables."""
    
#     # Google Cloud
#     google_cloud_project: str = "nk-expedition-dev"
#     google_application_credentials: str = ""
#     vertex_ai_location: str = "us-central1"
    
#     # Models (Tiered Intelligence)
#     gemini_tier1_model: str = "gemini-2.0-flash"  # Fast, cheap
#     gemini_tier2_model: str = "gemini-2.5-pro"    # Smart, expensive
#     embedding_model: str = "text-embedding-004"
    
#     # Data Layer
#     data_layer_mode: Literal["mock", "production"] = "mock"
#     bq_project: str = ""
#     bq_dataset: str = ""
    
#     # RAG
#     chroma_persist_dir: str = "./data/embeddings"
#     rag_top_k: int = 3
    
#     # Action Layer
#     action_layer_mode: Literal["mock", "production"] = "mock"
    
#     # Notifications
#     slack_webhook_url: str = ""
    
#     # API Keys (Phase 3)
#     google_ads_developer_token: str = ""
#     google_ads_client_id: str = ""
#     google_ads_client_secret: str = ""
#     google_ads_refresh_token: str = ""
#     google_ads_customer_id: str = ""
    
#     meta_access_token: str = ""
#     meta_ad_account_id: str = ""
    
#     tiktok_access_token: str = ""
#     tiktok_advertiser_id: str = ""
    
#     creatoriq_api_key: str = ""
#     creatoriq_account_id: str = ""
    
#     class Config:
#         env_file = ".env"
#         case_sensitive = False
    
#     @property
#     def has_gcp_credentials(self) -> bool:
#         """Check if GCP credentials are available."""
#         # Check for explicit credentials file
#         if self.google_application_credentials:
#             return Path(self.google_application_credentials).exists()
        
#         # Check for application default credentials
#         default_creds = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
#         return default_creds.exists()
    
#     @property
#     def has_slack(self) -> bool:
#         """Check if Slack is configured."""
#         return bool(self.slack_webhook_url)


# @lru_cache()
# def get_settings() -> Settings:
#     """Get cached settings instance."""
#     return Settings()


# # Convenience export
# settings = get_settings()

"""
Configuration management for Project Expedition.

Loads settings from environment variables with sensible defaults.
Supports both mock and production modes for data and action layers.
"""
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Usage:
        from src.utils.config import settings
        print(settings.google_cloud_project)
    """
    
    # ===========================================
    # LAYER MODES
    # ===========================================
    data_layer_mode: str = Field(default="mock", description="mock or production")
    action_layer_mode: str = Field(default="mock", description="mock or production")
    
    # ===========================================
    # GOOGLE CLOUD / VERTEX AI
    # ===========================================
    google_cloud_project: str = Field(default="", description="GCP Project ID")
    vertex_ai_location: str = Field(default="us-central1", description="Vertex AI region")
    google_application_credentials: str = Field(default="", description="Path to service account key")
    
    # ===========================================
    # GEMINI MODELS
    # ===========================================
    gemini_tier1_model: str = Field(default="gemini-2.0-flash", description="Fast model for routing")
    gemini_tier2_model: str = Field(default="gemini-2.5-pro", description="Powerful model for reasoning")
    embedding_model: str = Field(default="text-embedding-004", description="Embedding model")
    
    # ===========================================
    # RAG CONFIGURATION
    # ===========================================
    chroma_persist_dir: str = Field(default="./data/embeddings", description="ChromaDB storage path")
    rag_top_k: int = Field(default=3, description="Number of RAG results to retrieve")
    
    # ===========================================
    # BIGQUERY (Production)
    # ===========================================
    bq_project: str = Field(default="", description="BigQuery project")
    bq_dataset: str = Field(default="", description="BigQuery dataset")
    
    # ===========================================
    # SLACK NOTIFICATIONS
    # ===========================================
    slack_webhook_url: str = Field(default="", description="Slack webhook URL")
    slack_channel_alerts: str = Field(default="#marketing-alerts", description="General alerts channel")
    slack_channel_media_buying: str = Field(default="#media-buying", description="Media buying team channel")
    slack_channel_engineering: str = Field(default="#marketing-engineering", description="Engineering alerts")
    slack_channel_creative: str = Field(default="#creative-team", description="Creative team channel")
    
    # ===========================================
    # EMAIL NOTIFICATIONS
    # ===========================================
    email_smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    email_smtp_port: int = Field(default=587, description="SMTP server port")
    email_sender: str = Field(default="", description="Sender email address")
    email_sender_password: str = Field(default="", description="Sender email password")
    email_enabled: bool = Field(default=False, description="Enable email notifications")
    
    # ===========================================
    # GOOGLE ADS API
    # ===========================================
    google_ads_developer_token: str = Field(default="", description="Google Ads developer token")
    google_ads_client_id: str = Field(default="", description="OAuth client ID")
    google_ads_client_secret: str = Field(default="", description="OAuth client secret")
    google_ads_refresh_token: str = Field(default="", description="OAuth refresh token")
    google_ads_customer_id: str = Field(default="", description="Google Ads customer ID")
    google_ads_login_customer_id: str = Field(default="", description="MCC login customer ID")
    
    # ===========================================
    # META ADS API
    # ===========================================
    meta_access_token: str = Field(default="", description="Meta access token")
    meta_ad_account_id: str = Field(default="", description="Meta ad account ID")
    meta_app_id: str = Field(default="", description="Meta app ID")
    meta_app_secret: str = Field(default="", description="Meta app secret")
    
    # ===========================================
    # TIKTOK ADS API
    # ===========================================
    tiktok_access_token: str = Field(default="", description="TikTok access token")
    tiktok_advertiser_id: str = Field(default="", description="TikTok advertiser ID")
    tiktok_app_id: str = Field(default="", description="TikTok app ID")
    tiktok_secret: str = Field(default="", description="TikTok app secret")
    
    # ===========================================
    # LINKEDIN ADS API
    # ===========================================
    linkedin_access_token: str = Field(default="", description="LinkedIn access token")
    linkedin_ad_account_id: str = Field(default="", description="LinkedIn ad account ID")
    linkedin_client_id: str = Field(default="", description="LinkedIn client ID")
    linkedin_client_secret: str = Field(default="", description="LinkedIn client secret")
    
    # ===========================================
    # PROGRAMMATIC / DSP
    # ===========================================
    # DV360
    dv360_access_token: str = Field(default="", description="DV360 access token")
    dv360_advertiser_id: str = Field(default="", description="DV360 advertiser ID")
    dv360_partner_id: str = Field(default="", description="DV360 partner ID")
    
    # The Trade Desk
    ttd_api_key: str = Field(default="", description="TTD API key")
    ttd_advertiser_id: str = Field(default="", description="TTD advertiser ID")
    ttd_partner_id: str = Field(default="", description="TTD partner ID")
    
    # ===========================================
    # AFFILIATE NETWORKS
    # ===========================================
    # Impact.com
    impact_account_sid: str = Field(default="", description="Impact account SID")
    impact_auth_token: str = Field(default="", description="Impact auth token")
    
    # Commission Junction
    cj_api_key: str = Field(default="", description="CJ API key")
    cj_website_id: str = Field(default="", description="CJ website ID")
    
    # Rakuten
    rakuten_api_key: str = Field(default="", description="Rakuten API key")
    rakuten_account_id: str = Field(default="", description="Rakuten account ID")
    
    # ===========================================
    # CREATORIQ (Influencer)
    # ===========================================
    creatoriq_api_key: str = Field(default="", description="CreatorIQ API key")
    creatoriq_account_id: str = Field(default="", description="CreatorIQ account ID")
    
    # ===========================================
    # OFFLINE CHANNEL VENDOR CONTACTS
    # ===========================================
    vendor_email_tv: str = Field(default="", description="TV vendor contact email")
    vendor_email_radio: str = Field(default="", description="Radio vendor contact email")
    vendor_email_podcast: str = Field(default="", description="Podcast vendor contact email")
    vendor_email_direct_mail: str = Field(default="", description="Direct mail vendor email")
    vendor_email_ooh: str = Field(default="", description="OOH vendor contact email")
    vendor_email_events: str = Field(default="", description="Events team email")
    
    # ===========================================
    # FEATURE FLAGS
    # ===========================================
    feature_mmm_guardrails: bool = Field(default=True, description="Enable MMM guardrails")
    feature_mta_comparison: bool = Field(default=True, description="Enable MTA comparison")
    feature_competitor_intel: bool = Field(default=True, description="Enable competitor intelligence")
    feature_impact_simulation: bool = Field(default=True, description="Enable impact simulation")
    feature_batch_processing: bool = Field(default=True, description="Enable batch processing")
    
    # ===========================================
    # LOGGING & DEBUG
    # ===========================================
    log_level: str = Field(default="INFO", description="Logging level")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    debug_llm_calls: bool = Field(default=False, description="Print LLM prompts/responses")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars
    
    # ===========================================
    # HELPER METHODS
    # ===========================================
    
    @property
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self.data_layer_mode == "mock"
    
    @property
    def is_production_mode(self) -> bool:
        """Check if running in production mode."""
        return self.data_layer_mode == "production"
    
    @property
    def has_google_ads_credentials(self) -> bool:
        """Check if Google Ads credentials are configured."""
        return bool(self.google_ads_developer_token and self.google_ads_customer_id)
    
    @property
    def has_meta_credentials(self) -> bool:
        """Check if Meta Ads credentials are configured."""
        return bool(self.meta_access_token and self.meta_ad_account_id)
    
    @property
    def has_tiktok_credentials(self) -> bool:
        """Check if TikTok Ads credentials are configured."""
        return bool(self.tiktok_access_token and self.tiktok_advertiser_id)
    
    @property
    def has_linkedin_credentials(self) -> bool:
        """Check if LinkedIn Ads credentials are configured."""
        return bool(self.linkedin_access_token and self.linkedin_ad_account_id)
    
    @property
    def has_slack_configured(self) -> bool:
        """Check if Slack is configured."""
        return bool(self.slack_webhook_url)
    
    @property
    def has_email_configured(self) -> bool:
        """Check if email is configured."""
        return self.email_enabled and bool(self.email_sender and self.email_sender_password)
    
    def get_vendor_email(self, channel: str) -> str:
        """Get vendor email for a specific offline channel."""
        channel_lower = channel.lower()
        email_map = {
            "tv": self.vendor_email_tv,
            "radio": self.vendor_email_radio,
            "podcast": self.vendor_email_podcast,
            "direct_mail": self.vendor_email_direct_mail,
            "ooh": self.vendor_email_ooh,
            "events": self.vendor_email_events,
        }
        return email_map.get(channel_lower, "")
    
    def get_slack_channel_for_team(self, team: str) -> str:
        """Get Slack channel for a specific team."""
        team_lower = team.lower()
        channel_map = {
            "engineering": self.slack_channel_engineering,
            "creative": self.slack_channel_creative,
            "media_buying": self.slack_channel_media_buying,
            "decision_science": self.slack_channel_alerts,
            "ops": self.slack_channel_alerts,
            "analytics": self.slack_channel_alerts,
        }
        return channel_map.get(team_lower, self.slack_channel_alerts)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()