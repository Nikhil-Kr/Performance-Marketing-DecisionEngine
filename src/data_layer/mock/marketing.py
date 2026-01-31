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
    """
    
    def __init__(self, data_dir: str = "data/mock_csv"):
        self.data_dir = Path(data_dir)
        self._data: dict[str, pd.DataFrame] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load all CSV files into memory."""
        if not self.data_dir.exists():
            print(f"⚠️ Mock data directory not found: {self.data_dir}")
            return
            
        for csv_file in self.data_dir.glob("*.csv"):
            channel = csv_file.stem
            # Skip files handled by other loaders
            if any(x in channel for x in ["influencer", "mta_", "competitors", "market_trends", "mmm_"]):
                continue

            try:
                df = pd.read_csv(csv_file, parse_dates=["date"])
                self._data[channel] = df
            except Exception as e:
                print(f"  ✗ Failed to load {csv_file}: {e}")

    # --- REQUIRED INTERFACE METHODS (Fixed) ---

    def list_channels(self) -> list[str]:
        """List all loaded channels."""
        return list(self._data.keys())

    def get_metrics(
        self,
        channel: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch performance metrics for a channel (Required by Base Class)."""
        if channel not in self._data:
            return pd.DataFrame()
        
        df = self._data[channel].copy()
        
        # Filter date range
        mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
        df = df[mask]
        
        # Select specific metrics if requested
        if metrics:
            # Ensure 'date' is always preserved
            cols = ["date"] + [m for m in metrics if m in df.columns]
            df = df[cols]
        
        return df

    # --- TIME TRAVEL METHODS (Tier 4) ---

    def get_channel_performance(
        self,
        channel: str,
        days: int = 30,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Get recent performance data relative to a specific end date."""
        if channel not in self._data:
            return pd.DataFrame()
        
        # TIME TRAVEL LOGIC
        if not end_date:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=days)
        
        # Reuse get_metrics to ensure consistency
        return self.get_metrics(channel, start_date, end_date)
    
    def get_campaign_breakdown(
        self,
        channel: str,
        days: int = 30,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """Get campaign-level breakdown relative to specific date."""
        df = self.get_channel_performance(channel, days, end_date)
        if df.empty:
            return df
        
        # Mock breakdown logic...
        campaigns = []
        # Weights for synthetic campaigns
        weights = [0.5, 0.3, 0.2]
        
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

    def get_anomalies(
        self,
        channel: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        threshold_sigma: float = 2.0,
    ) -> list[dict[str, Any]]:
        """
        Detect anomalies within a specified date range.
        
        Args:
            channel: Specific channel or None for all
            start_date: Start of analysis window (used for baseline context)
            end_date: End of analysis window (detect anomalies as of this date)
            threshold_sigma: Z-score threshold for anomaly detection
            
        Returns:
            List of anomaly dictionaries sorted by severity
        """
        anomalies = []
        channels_to_check = [channel] if channel else list(self._data.keys())
        
        # Default end_date to now if not provided
        if not end_date:
            end_date = datetime.now()
        
        # Default start_date to 30 days before end_date if not provided
        if not start_date:
            start_date = end_date - timedelta(days=30)
            
        end_ts = pd.Timestamp(end_date)
        start_ts = pd.Timestamp(start_date)
        
        for ch in channels_to_check:
            df = self._data.get(ch)
            if df is None or df.empty:
                continue
            
            # TIME TRAVEL: Filter data to be within or before the analysis window
            # We need data UP TO end_date for the current value
            # And data BEFORE end_date for the baseline
            history = df[df["date"] <= end_ts].sort_values("date")
            
            if history.empty:
                continue
                
            # Get the most recent row as "current" (the row closest to end_date)
            current_row = history.iloc[-1]
            
            # Ensure data isn't stale (row should be within 2 days of end_date)
            if (end_ts - current_row["date"]).days > 2:
                continue

            # Calculate baseline from data WITHIN the analysis window (excluding current)
            # This respects the user's selected date range
            baseline_data = history[
                (history["date"] >= start_ts) & 
                (history["date"] < current_row["date"])
            ]
            
            # If we don't have enough data in the window, extend baseline lookback
            if len(baseline_data) < 7:
                baseline_data = history.iloc[:-1].tail(30)
                
            if baseline_data.empty:
                continue
            
            for metric in ["cpa", "spend", "roas", "conversions"]:
                if metric not in df.columns:
                    continue
                
                recent_value = current_row[metric]
                hist_mean = baseline_data[metric].mean()
                hist_std = baseline_data[metric].std()
                
                if hist_std == 0 or pd.isna(hist_std):
                    continue
                
                z_score = (recent_value - hist_mean) / hist_std
                
                if abs(z_score) >= threshold_sigma:
                    deviation_pct = ((recent_value - hist_mean) / hist_mean) * 100 if hist_mean != 0 else 0
                    
                    if abs(z_score) >= 4: severity = "critical"
                    elif abs(z_score) >= 3: severity = "high"
                    elif abs(z_score) >= 2.5: severity = "medium"
                    else: severity = "low"
                    
                    anomalies.append({
                        "channel": ch,
                        "metric": metric,
                        "current_value": round(recent_value, 2),
                        "expected_value": round(hist_mean, 2),
                        "deviation_pct": round(deviation_pct, 1),
                        "severity": severity,
                        "direction": "spike" if z_score > 0 else "drop",
                        "detected_at": current_row["date"].strftime('%Y-%m-%d'),
                        # Include analysis context for downstream use
                        "analysis_start": start_date.strftime('%Y-%m-%d') if isinstance(start_date, datetime) else str(start_date),
                        "analysis_end": end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime) else str(end_date),
                    })
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        anomalies.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
        return anomalies

    def is_healthy(self) -> bool:
        """Check if mock data is loaded."""
        return len(self._data) > 0
    
    def check_data_freshness(self) -> dict[str, datetime]:
        """Return last update timestamp."""
        return {k: datetime.now() for k in self._data}