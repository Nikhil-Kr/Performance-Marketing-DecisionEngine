"""Mock implementation of influencer/creator data."""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

from ..interfaces.base import BaseDataSource


class MockInfluencerData(BaseDataSource):
    """
    Mock influencer data source using CSV files.
    
    In production, this would connect to CreatorIQ API or similar.
    """
    
    def __init__(self, data_dir: str = "data/mock_csv"):
        self.data_dir = Path(data_dir)
        self._campaigns: pd.DataFrame = pd.DataFrame()
        self._load_data()
    
    def _load_data(self) -> None:
        """Load influencer campaign data."""
        csv_path = self.data_dir / "influencer_campaigns.csv"
        if csv_path.exists():
            try:
                self._campaigns = pd.read_csv(csv_path, parse_dates=["post_date"])
                print(f"  ✓ Loaded influencer campaigns: {len(self._campaigns)} rows")
            except Exception as e:
                print(f"  ✗ Failed to load influencer data: {e}")
    
    def get_metrics(
        self,
        channel: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Get influencer metrics aggregated by date."""
        if self._campaigns.empty:
            return pd.DataFrame()
        
        df = self._campaigns.copy()
        mask = (df["post_date"] >= pd.Timestamp(start_date)) & (df["post_date"] <= pd.Timestamp(end_date))
        df = df[mask]
        
        # Aggregate by date
        daily = df.groupby(df["post_date"].dt.date).agg({
            "contract_value": "sum",
            "impressions": "sum",
            "engagements": "sum",
            "clicks": "sum",
            "conversions": "sum",
            "earned_media_value": "sum",
        }).reset_index()
        daily.columns = ["date", "spend", "impressions", "engagements", "clicks", "conversions", "emv"]
        
        return daily
    
    def get_campaign_performance(
        self,
        campaign_id: str | None = None,
    ) -> pd.DataFrame:
        """Get performance by campaign."""
        if self._campaigns.empty:
            return pd.DataFrame()
        
        df = self._campaigns.copy()
        if campaign_id:
            df = df[df["campaign_id"] == campaign_id]
        
        return df
    
    def get_creator_performance(
        self,
        creator_id: str | None = None,
    ) -> pd.DataFrame:
        """Get performance by creator."""
        if self._campaigns.empty:
            return pd.DataFrame()
        
        df = self._campaigns.copy()
        if creator_id:
            df = df[df["creator_id"] == creator_id]
        
        # Aggregate by creator
        return df.groupby(["creator_id", "creator_name", "platform"]).agg({
            "contract_value": "sum",
            "impressions": "sum",
            "engagements": "sum",
            "clicks": "sum",
            "conversions": "sum",
            "earned_media_value": "sum",
        }).reset_index()
    
    def get_anomalies(
        self,
        channel: str | None = None,
        lookback_hours: int = 24,
        threshold_sigma: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Detect anomalies in influencer campaigns."""
        anomalies = []
        
        if self._campaigns.empty:
            return anomalies
        
        # Check engagement rate anomalies by creator
        for creator_id in self._campaigns["creator_id"].unique():
            creator_data = self._campaigns[self._campaigns["creator_id"] == creator_id]
            
            if len(creator_data) < 3:
                continue
            
            # Check engagement rate
            engagement_rates = creator_data["engagement_rate"]
            recent = engagement_rates.iloc[-1]
            mean = engagement_rates.mean()
            std = engagement_rates.std()
            
            if std > 0:
                z_score = (recent - mean) / std
                if abs(z_score) >= threshold_sigma:
                    anomalies.append({
                        "channel": "influencer",
                        "metric": "engagement_rate",
                        "entity": creator_data["creator_name"].iloc[0],
                        "current_value": round(recent, 4),
                        "expected_value": round(mean, 4),
                        "deviation_pct": round(((recent - mean) / mean) * 100, 1),
                        "severity": "high" if abs(z_score) >= 3 else "medium",
                        "direction": "spike" if z_score > 0 else "drop",
                        "detected_at": datetime.now().isoformat(),
                    })
        
        return anomalies
    
    def check_data_freshness(self) -> dict[str, datetime]:
        """Check data freshness."""
        if self._campaigns.empty:
            return {}
        
        return {"influencer_campaigns": datetime.now()}
    
    def is_healthy(self) -> bool:
        """Check if data is loaded."""
        return not self._campaigns.empty
    
    def list_channels(self) -> list[str]:
        """List available channels."""
        return ["influencer_campaigns"] if not self._campaigns.empty else []
    
    def get_attribution_analysis(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """
        Get attribution/lift analysis for a campaign.
        Mock: Returns synthetic causal analysis.
        """
        campaign = self._campaigns[self._campaigns["campaign_id"] == campaign_id]
        
        if campaign.empty:
            return {}
        
        total_conversions = campaign["conversions"].sum()
        total_spend = campaign["contract_value"].sum()
        
        # Mock incremental lift calculation
        baseline_rate = 0.02  # 2% baseline conversion
        observed_rate = total_conversions / max(campaign["clicks"].sum(), 1)
        incremental_lift = max(0, (observed_rate - baseline_rate) / baseline_rate * 100)
        
        return {
            "campaign_id": campaign_id,
            "total_spend": round(total_spend, 2),
            "total_conversions": int(total_conversions),
            "observed_conversion_rate": round(observed_rate, 4),
            "baseline_conversion_rate": baseline_rate,
            "incremental_lift_pct": round(incremental_lift, 1),
            "statistical_significance": np.random.uniform(0.85, 0.99),
            "confidence_interval": [round(incremental_lift * 0.8, 1), round(incremental_lift * 1.2, 1)],
        }
