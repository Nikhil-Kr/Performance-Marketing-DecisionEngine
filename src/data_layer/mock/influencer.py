"""Mock implementation of influencer/creator data."""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

from ..interfaces.base import BaseDataSource


class MockInfluencerData(BaseDataSource):
    """Mock influencer data source using CSV files."""
    
    def __init__(self, data_dir: str = "data/mock_csv"):
        self.data_dir = Path(data_dir)
        self._campaigns: pd.DataFrame = pd.DataFrame()
        self._load_data()
    
    def _load_data(self) -> None:
        csv_path = self.data_dir / "influencer_campaigns.csv"
        if csv_path.exists():
            try:
                self._campaigns = pd.read_csv(csv_path, parse_dates=["post_date"])
                print(f"  ✓ Loaded influencer campaigns: {len(self._campaigns)} rows")
            except Exception as e:
                print(f"  ✗ Failed to load influencer data: {e}")
        else:
            print(f"  ⚠️ Influencer file missing: {csv_path}")

    # --- REQUIRED INTERFACE METHODS (Fixed) ---

    def list_channels(self) -> list[str]:
        """List all loaded channels."""
        if not self._campaigns.empty:
            return ["influencer_campaigns"]
        return []

    def get_metrics(
        self,
        channel: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch performance metrics for a channel (Required by Base Class)."""
        if self._campaigns.empty:
            return pd.DataFrame()
        
        # Filter by date range (using post_date)
        mask = (self._campaigns["post_date"] >= pd.Timestamp(start_date)) & (self._campaigns["post_date"] <= pd.Timestamp(end_date))
        df = self._campaigns[mask].copy()
        
        # Rename post_date to date for consistency with generic marketing data interface
        df = df.rename(columns={"post_date": "date"})
        
        if metrics:
            # Ensure 'date' is preserved
            cols = ["date"] + [m for m in metrics if m in df.columns]
            df = df[cols]
            
        return df

    # --- TIME TRAVEL & SPECIFIC METHODS ---

    def get_campaign_performance(self) -> pd.DataFrame:
        """Get all campaign performance data."""
        return self._campaigns

    def get_anomalies(
        self,
        channel: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        threshold_sigma: float = 2.0,
    ) -> list[dict[str, Any]]:
        """
        Detect anomalies in influencer campaigns within a date range.
        
        Args:
            channel: Ignored for influencer (always checks influencer_campaigns)
            start_date: Start of analysis window
            end_date: End of analysis window (detect anomalies as of this date)
            threshold_sigma: Z-score threshold
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        if self._campaigns.empty: 
            return anomalies
        
        # Default end_date to now
        if not end_date:
            end_date = datetime.now()
        
        # Default start_date to 30 days before end_date
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        end_ts = pd.Timestamp(end_date)
        start_ts = pd.Timestamp(start_date)
        
        # Filter: Only look at posts within a small window of the end date
        # (e.g. last 3 days leading up to end_date)
        scan_window_start = end_ts - timedelta(days=3)
        
        # "Current" posts are ones in the scan window AND within our analysis period
        recent_posts = self._campaigns[
            (self._campaigns["post_date"] <= end_ts) & 
            (self._campaigns["post_date"] >= scan_window_start) &
            (self._campaigns["post_date"] >= start_ts)  # Must be within analysis window
        ]
        
        for _, post in recent_posts.iterrows():
            creator_id = post["creator_id"]
            
            # Get history for this creator strictly BEFORE this post
            # and ideally within or before the analysis window
            history = self._campaigns[
                (self._campaigns["creator_id"] == creator_id) & 
                (self._campaigns["post_date"] < post["post_date"]) &
                (self._campaigns["post_date"] <= end_ts)
            ]
            
            if len(history) < 2: 
                continue  # Need history to judge
            
            # Check Engagement Rate
            recent = post["engagement_rate"]
            mean = history["engagement_rate"].mean()
            std = history["engagement_rate"].std()
            
            if std > 0:
                z_score = (recent - mean) / std
                if abs(z_score) >= threshold_sigma:
                    severity = "critical" if abs(z_score) > 3 else "high"
                    
                    anomalies.append({
                        "channel": "influencer_campaigns",
                        "metric": "engagement_rate",
                        "entity": post["creator_name"],
                        "current_value": round(recent, 4),
                        "expected_value": round(mean, 4),
                        "deviation_pct": round(((recent - mean) / mean) * 100, 1),
                        "severity": severity,
                        "direction": "spike" if z_score > 0 else "drop",
                        "detected_at": post["post_date"].strftime('%Y-%m-%d'),
                        # Include analysis context
                        "analysis_start": start_date.strftime('%Y-%m-%d') if isinstance(start_date, datetime) else str(start_date),
                        "analysis_end": end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime) else str(end_date),
                    })
        
        return anomalies

    def is_healthy(self) -> bool:
        """Check if data is loaded."""
        return not self._campaigns.empty
        
    def check_data_freshness(self) -> dict[str, datetime]:
        """Check data freshness."""
        return {"influencer_campaigns": datetime.now()}