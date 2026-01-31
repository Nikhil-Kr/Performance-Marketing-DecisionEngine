"""Configuration management for Expedition."""
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud
    google_cloud_project: str = "nk-expedition-dev"
    google_application_credentials: str = ""
    vertex_ai_location: str = "us-central1"
    
    # Models (Tiered Intelligence)
    gemini_tier1_model: str = "gemini-2.0-flash"  # Fast, cheap
    gemini_tier2_model: str = "gemini-2.5-pro"    # Smart, expensive
    embedding_model: str = "text-embedding-004"
    
    # Data Layer
    data_layer_mode: Literal["mock", "production"] = "mock"
    bq_project: str = ""
    bq_dataset: str = ""
    
    # RAG
    chroma_persist_dir: str = "./data/embeddings"
    rag_top_k: int = 3
    
    # Action Layer
    action_layer_mode: Literal["mock", "production"] = "mock"
    
    # Notifications
    slack_webhook_url: str = ""
    
    # API Keys (Phase 3)
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""
    google_ads_customer_id: str = ""
    
    meta_access_token: str = ""
    meta_ad_account_id: str = ""
    
    tiktok_access_token: str = ""
    tiktok_advertiser_id: str = ""
    
    creatoriq_api_key: str = ""
    creatoriq_account_id: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def has_gcp_credentials(self) -> bool:
        """Check if GCP credentials are available."""
        # Check for explicit credentials file
        if self.google_application_credentials:
            return Path(self.google_application_credentials).exists()
        
        # Check for application default credentials
        default_creds = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
        return default_creds.exists()
    
    @property
    def has_slack(self) -> bool:
        """Check if Slack is configured."""
        return bool(self.slack_webhook_url)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
