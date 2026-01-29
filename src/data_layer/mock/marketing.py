"""Mock implementation of marketing data using CSV files."""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

from ..interfaces.base import BaseDataSource


class MockMarketingData(BaseDataSource):
    """
    Mock data source using CSV files.
    
    When you join GoFundMe and have real data:
    1. Create BigQueryMarketingData with same interface
    2. Change DATA_LAYER_MODE=production in .env
    3. That's it - everything else works unchanged
    """
    
    # Channel categories for routing
    PAID_MEDIA_CHANNELS = [
        "google_search", "google_pmax", "google_display", "google_youtube",
        "meta_ads", "tiktok_ads", "linkedin_ads", "programmatic"
    ]
    INFLUENCER_CHANNELS = ["influencer_campaigns"]
    OFFLINE_CHANNELS = ["direct_mail", "tv", "radio", "ooh", "events"]
    
    def __init__(self, data_dir: str = "data/mock_csv"):
        self.data_dir = Path(data_dir)
        self._data: dict[str, pd.DataFrame] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load all CSV files into memory."""
        if not self.data_dir.exists():
            print(f"⚠️ Mock data directory not found: {self.data_dir}")
            print("   Run 'make mock-data' to generate mock data")
            return
            
        for csv_file in self.data_dir.glob("*.csv"):
            channel = csv_file.stem

            if "influencer" in channel:
                continue
                
            try:
                df = pd.read_csv(csv_file, parse_dates=["date"])
                self._data[channel] = df
                print(f"  ✓ Loaded {channel}: {len(df)} rows")
            except Exception as e:
                print(f"  ✗ Failed to load {csv_file}: {e}")
    
    def get_metrics(
        self,
        channel: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch performance metrics for a channel."""
        if channel not in self._data:
            return pd.DataFrame()
        
        df = self._data[channel].copy()
        
        # Filter date range
        mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
        df = df[mask]
        
        # Select specific metrics if requested
        if metrics:
            cols = ["date"] + [m for m in metrics if m in df.columns]
            df = df[cols]
        
        return df
    
    def get_channel_performance(
        self,
        channel: str,
        days: int = 30,
    ) -> pd.DataFrame:
        """Get recent performance data for a channel."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.get_metrics(channel, start_date, end_date)
    
    def get_anomalies(
        self,
        channel: str | None = None,
        lookback_hours: int = 24,
        threshold_sigma: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Detect anomalies using z-score method."""
        anomalies = []
        channels_to_check = [channel] if channel else list(self._data.keys())
        
        for ch in channels_to_check:
            df = self._data.get(ch)
            if df is None or df.empty:
                continue
            
            # Check key metrics
            for metric in ["cpa", "spend", "roas", "conversions"]:
                if metric not in df.columns:
                    continue
                
                # Get recent value vs historical
                recent_value = df[metric].iloc[-1]
                historical_mean = df[metric].iloc[:-1].mean()
                historical_std = df[metric].iloc[:-1].std()
                
                if historical_std == 0 or pd.isna(historical_std):
                    continue
                
                z_score = (recent_value - historical_mean) / historical_std
                
                if abs(z_score) >= threshold_sigma:
                    deviation_pct = ((recent_value - historical_mean) / historical_mean) * 100
                    
                    # Determine severity
                    if abs(z_score) >= 4:
                        severity = "critical"
                    elif abs(z_score) >= 3:
                        severity = "high"
                    elif abs(z_score) >= 2.5:
                        severity = "medium"
                    else:
                        severity = "low"
                    
                    anomalies.append({
                        "channel": ch,
                        "metric": metric,
                        "current_value": round(recent_value, 2),
                        "expected_value": round(historical_mean, 2),
                        "deviation_pct": round(deviation_pct, 1),
                        "z_score": round(z_score, 2),
                        "severity": severity,
                        "direction": "spike" if z_score > 0 else "drop",
                        "detected_at": datetime.now().isoformat(),
                    })
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        anomalies.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
        return anomalies
    
    def check_data_freshness(self) -> dict[str, datetime]:
        """Return last update timestamp for each source."""
        freshness = {}
        for channel, df in self._data.items():
            if "date" in df.columns and not df.empty:
                # For mock data, pretend it's fresh (today)
                freshness[channel] = datetime.now()
        return freshness
    
    def is_healthy(self) -> bool:
        """Check if mock data is loaded."""
        return len(self._data) > 0
    
    def list_channels(self) -> list[str]:
        """List all loaded channels."""
        return list(self._data.keys())
    
    def get_channel_category(self, channel: str) -> str:
        """Determine channel category for routing."""
        if channel in self.PAID_MEDIA_CHANNELS:
            return "paid_media"
        elif channel in self.INFLUENCER_CHANNELS:
            return "influencer"
        elif channel in self.OFFLINE_CHANNELS:
            return "offline"
        else:
            return "paid_media"  # Default
    
    def get_campaign_breakdown(
        self,
        channel: str,
        days: int = 30,
    ) -> pd.DataFrame:
        """Get campaign-level breakdown (mock: generates synthetic campaigns)."""
        df = self.get_channel_performance(channel, days)
        if df.empty:
            return df
        
        # Simulate 3-5 campaigns
        campaigns = []
        num_campaigns = np.random.randint(3, 6)
        weights = np.random.dirichlet(np.ones(num_campaigns))
        
        for i, weight in enumerate(weights):
            campaign_df = df.copy()
            campaign_df["campaign_id"] = f"{channel}_campaign_{i+1:03d}"
            campaign_df["campaign_name"] = f"Campaign {i+1}"
            
            # Distribute metrics
            for col in ["spend", "impressions", "clicks", "conversions", "revenue"]:
                if col in campaign_df.columns:
                    campaign_df[col] = (campaign_df[col] * weight).round(2)
            
            campaigns.append(campaign_df)
        
        return pd.concat(campaigns, ignore_index=True)
