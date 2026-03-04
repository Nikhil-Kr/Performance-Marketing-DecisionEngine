# """Mock implementation of marketing data using CSV files."""
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Any
# import pandas as pd
# import numpy as np

# from ..interfaces.base import BaseDataSource


# class MockMarketingData(BaseDataSource):
#     """
#     Mock data source using CSV files.
#     """
    
#     def __init__(self, data_dir: str = "data/mock_csv"):
#         self.data_dir = Path(data_dir)
#         self._data: dict[str, pd.DataFrame] = {}
#         self._load_data()
    
#     def _load_data(self) -> None:
#         """Load all CSV files into memory."""
#         if not self.data_dir.exists():
#             print(f"⚠️ Mock data directory not found: {self.data_dir}")
#             return
            
#         for csv_file in self.data_dir.glob("*.csv"):
#             channel = csv_file.stem
#             # Skip files handled by other loaders
#             if any(x in channel for x in ["influencer", "mta_", "competitors", "market_trends", "mmm_"]):
#                 continue

#             try:
#                 df = pd.read_csv(csv_file, parse_dates=["date"])
#                 self._data[channel] = df
#             except Exception as e:
#                 print(f"  ✗ Failed to load {csv_file}: {e}")

#     # --- REQUIRED INTERFACE METHODS (Fixed) ---

#     def list_channels(self) -> list[str]:
#         """List all loaded channels."""
#         return list(self._data.keys())

#     def get_metrics(
#         self,
#         channel: str,
#         start_date: datetime,
#         end_date: datetime,
#         metrics: list[str] | None = None,
#     ) -> pd.DataFrame:
#         """Fetch performance metrics for a channel (Required by Base Class)."""
#         if channel not in self._data:
#             return pd.DataFrame()
        
#         df = self._data[channel].copy()
        
#         # Filter date range
#         mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
#         df = df[mask]
        
#         # Select specific metrics if requested
#         if metrics:
#             # Ensure 'date' is always preserved
#             cols = ["date"] + [m for m in metrics if m in df.columns]
#             df = df[cols]
        
#         return df

#     # --- TIME TRAVEL METHODS (Tier 4) ---

#     def get_channel_performance(
#         self,
#         channel: str,
#         days: int = 30,
#         end_date: datetime = None
#     ) -> pd.DataFrame:
#         """Get recent performance data relative to a specific end date."""
#         if channel not in self._data:
#             return pd.DataFrame()
        
#         # TIME TRAVEL LOGIC
#         if not end_date:
#             end_date = datetime.now()
        
#         start_date = end_date - timedelta(days=days)
        
#         # Reuse get_metrics to ensure consistency
#         return self.get_metrics(channel, start_date, end_date)
    
#     def get_campaign_breakdown(
#         self,
#         channel: str,
#         days: int = 30,
#         end_date: datetime = None
#     ) -> pd.DataFrame:
#         """Get campaign-level breakdown relative to specific date."""
#         df = self.get_channel_performance(channel, days, end_date)
#         if df.empty:
#             return df
        
#         # Mock breakdown logic...
#         campaigns = []
#         # Weights for synthetic campaigns
#         weights = [0.5, 0.3, 0.2]
        
#         for i, weight in enumerate(weights):
#             campaign_df = df.copy()
#             campaign_df["campaign_id"] = f"{channel}_campaign_{i+1:03d}"
#             campaign_df["campaign_name"] = f"Campaign {i+1}"
            
#             # Distribute metrics
#             for col in ["spend", "impressions", "clicks", "conversions", "revenue"]:
#                 if col in campaign_df.columns:
#                     campaign_df[col] = (campaign_df[col] * weight).round(2)
            
#             campaigns.append(campaign_df)
        
#         return pd.concat(campaigns, ignore_index=True)

#     def get_anomalies(
#         self,
#         channel: str | None = None,
#         start_date: datetime | None = None,
#         end_date: datetime | None = None,
#         threshold_sigma: float = 2.0,
#     ) -> list[dict[str, Any]]:
#         """
#         Detect anomalies within a specified date range.
        
#         Args:
#             channel: Specific channel or None for all
#             start_date: Start of analysis window (used for baseline context)
#             end_date: End of analysis window (detect anomalies as of this date)
#             threshold_sigma: Z-score threshold for anomaly detection
            
#         Returns:
#             List of anomaly dictionaries sorted by severity
#         """
#         anomalies = []
#         channels_to_check = [channel] if channel else list(self._data.keys())
        
#         # Default end_date to now if not provided
#         if not end_date:
#             end_date = datetime.now()
        
#         # Default start_date to 30 days before end_date if not provided
#         if not start_date:
#             start_date = end_date - timedelta(days=30)
            
#         end_ts = pd.Timestamp(end_date)
#         start_ts = pd.Timestamp(start_date)
        
#         for ch in channels_to_check:
#             df = self._data.get(ch)
#             if df is None or df.empty:
#                 continue
            
#             # TIME TRAVEL: Filter data to be within or before the analysis window
#             # We need data UP TO end_date for the current value
#             # And data BEFORE end_date for the baseline
#             history = df[df["date"] <= end_ts].sort_values("date")
            
#             if history.empty:
#                 continue
                
#             # Get the most recent row as "current" (the row closest to end_date)
#             current_row = history.iloc[-1]
            
#             # Ensure data isn't stale (row should be within 2 days of end_date)
#             if (end_ts - current_row["date"]).days > 2:
#                 continue

#             # Calculate baseline from data WITHIN the analysis window (excluding current)
#             # This respects the user's selected date range
#             baseline_data = history[
#                 (history["date"] >= start_ts) & 
#                 (history["date"] < current_row["date"])
#             ]
            
#             # If we don't have enough data in the window, extend baseline lookback
#             if len(baseline_data) < 7:
#                 baseline_data = history.iloc[:-1].tail(30)
                
#             if baseline_data.empty:
#                 continue
            
#             for metric in ["cpa", "spend", "roas", "conversions"]:
#                 if metric not in df.columns:
#                     continue
                
#                 recent_value = current_row[metric]
#                 hist_mean = baseline_data[metric].mean()
#                 hist_std = baseline_data[metric].std()
                
#                 if hist_std == 0 or pd.isna(hist_std):
#                     continue
                
#                 z_score = (recent_value - hist_mean) / hist_std
                
#                 if abs(z_score) >= threshold_sigma:
#                     deviation_pct = ((recent_value - hist_mean) / hist_mean) * 100 if hist_mean != 0 else 0
                    
#                     if abs(z_score) >= 4: severity = "critical"
#                     elif abs(z_score) >= 3: severity = "high"
#                     elif abs(z_score) >= 2.5: severity = "medium"
#                     else: severity = "low"
                    
#                     anomalies.append({
#                         "channel": ch,
#                         "metric": metric,
#                         "current_value": round(recent_value, 2),
#                         "expected_value": round(hist_mean, 2),
#                         "deviation_pct": round(deviation_pct, 1),
#                         "severity": severity,
#                         "direction": "spike" if z_score > 0 else "drop",
#                         "detected_at": current_row["date"].strftime('%Y-%m-%d'),
#                         # Include analysis context for downstream use
#                         "analysis_start": start_date.strftime('%Y-%m-%d') if isinstance(start_date, datetime) else str(start_date),
#                         "analysis_end": end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime) else str(end_date),
#                     })
        
#         # Sort by severity
#         severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
#         anomalies.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
#         return anomalies

#     def is_healthy(self) -> bool:
#         """Check if mock data is loaded."""
#         return len(self._data) > 0
    
#     def check_data_freshness(self) -> dict[str, datetime]:
#         """Return last update timestamp."""
#         return {k: datetime.now() for k in self._data}

## <--------- Updated - 3/3 --------->

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
        "meta_ads", "tiktok_ads", "linkedin_ads", "programmatic", "affiliate"
    ]
    INFLUENCER_CHANNELS = ["influencer_campaigns"]
    OFFLINE_CHANNELS = ["direct_mail", "tv", "radio", "ooh", "events", "podcast"]
    
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
        """
        Detect anomalies using multiple methods:
        
        1. WINDOWED Z-SCORE: Compare last 3 days vs prior 30 days (not just last point)
        2. DAY-OF-WEEK SEASONALITY: Account for weekday/weekend patterns
        3. RATE-OF-CHANGE: Detect sustained trends (7-day slope)
        4. MULTI-METRIC CORRELATION: Flag when related metrics move together
        
        Improvement #4: Robust anomaly detection replacing single-point z-score.
        """
        anomalies = []
        channels_to_check = [channel] if channel else list(self._data.keys())
        
        for ch in channels_to_check:
            df = self._data.get(ch)
            if df is None or df.empty or len(df) < 14:
                continue
            
            channel_anomalies = []
            
            # --- Method 1: Windowed Z-Score (last 3 days vs prior 30) ---
            for metric in ["cpa", "spend", "roas", "conversions"]:
                if metric not in df.columns:
                    continue
                
                recent_window = df[metric].iloc[-3:]  # Last 3 days
                historical = df[metric].iloc[:-3]      # Everything before
                
                if len(historical) < 7 or historical.std() == 0 or pd.isna(historical.std()):
                    continue
                
                recent_avg = recent_window.mean()
                hist_mean = historical.mean()
                hist_std = historical.std()
                
                z_score = (recent_avg - hist_mean) / hist_std
                
                if abs(z_score) >= threshold_sigma:
                    deviation_pct = ((recent_avg - hist_mean) / hist_mean) * 100
                    severity = self._classify_severity(abs(z_score))
                    
                    anom = {
                        "channel": ch,
                        "metric": metric,
                        "current_value": round(recent_avg, 2),
                        "expected_value": round(hist_mean, 2),
                        "deviation_pct": round(deviation_pct, 1),
                        "z_score": round(z_score, 2),
                        "severity": severity,
                        "direction": "spike" if z_score > 0 else "drop",
                        "detection_method": "windowed_zscore",
                        "detected_at": datetime.now().isoformat(),
                    }
                    channel_anomalies.append(anom)
            
            # --- Method 2: Day-of-Week Seasonality Check ---
            if "date" in df.columns:
                df_copy = df.copy()
                df_copy["dow"] = pd.to_datetime(df_copy["date"]).dt.dayofweek
                last_dow = df_copy["dow"].iloc[-1]
                
                for metric in ["cpa", "spend", "roas", "conversions"]:
                    if metric not in df_copy.columns:
                        continue
                    
                    # Compare today vs same-day-of-week historical
                    same_dow = df_copy[df_copy["dow"] == last_dow][metric].iloc[:-1]
                    if len(same_dow) < 3 or same_dow.std() == 0:
                        continue
                    
                    current = df_copy[metric].iloc[-1]
                    dow_mean = same_dow.mean()
                    dow_std = same_dow.std()
                    
                    dow_z = (current - dow_mean) / dow_std
                    
                    # Only add if this is a NEW anomaly not already caught by windowed z-score
                    if abs(dow_z) >= (threshold_sigma + 0.5):  # Higher bar for seasonal
                        already_found = any(
                            a["metric"] == metric and a["channel"] == ch 
                            for a in channel_anomalies
                        )
                        if not already_found:
                            deviation_pct = ((current - dow_mean) / dow_mean) * 100
                            channel_anomalies.append({
                                "channel": ch,
                                "metric": metric,
                                "current_value": round(current, 2),
                                "expected_value": round(dow_mean, 2),
                                "deviation_pct": round(deviation_pct, 1),
                                "z_score": round(dow_z, 2),
                                "severity": self._classify_severity(abs(dow_z)),
                                "direction": "spike" if dow_z > 0 else "drop",
                                "detection_method": "seasonal_zscore",
                                "detected_at": datetime.now().isoformat(),
                            })
            
            # --- Method 3: Rate-of-Change (7-day slope) ---
            for metric in ["cpa", "spend", "roas"]:
                if metric not in df.columns or len(df) < 10:
                    continue
                
                recent_7 = df[metric].iloc[-7:].values
                if len(recent_7) < 7:
                    continue
                
                # Linear regression slope
                x = np.arange(7)
                try:
                    slope, intercept = np.polyfit(x, recent_7, 1)
                except (np.linalg.LinAlgError, ValueError):
                    continue
                
                # Normalize slope as % of mean
                mean_val = recent_7.mean()
                if mean_val == 0:
                    continue
                daily_change_pct = (slope / mean_val) * 100
                
                # Flag if metric is changing > 3% per day consistently
                if abs(daily_change_pct) > 3.0:
                    already_found = any(
                        a["metric"] == metric and a["channel"] == ch
                        for a in channel_anomalies
                    )
                    if not already_found:
                        channel_anomalies.append({
                            "channel": ch,
                            "metric": metric,
                            "current_value": round(recent_7[-1], 2),
                            "expected_value": round(recent_7[0], 2),
                            "deviation_pct": round(daily_change_pct * 7, 1),  # Total 7-day change
                            "z_score": round(abs(daily_change_pct), 2),
                            "severity": "high" if abs(daily_change_pct) > 5 else "medium",
                            "direction": "spike" if daily_change_pct > 0 else "drop",
                            "detection_method": "rate_of_change",
                            "detected_at": datetime.now().isoformat(),
                        })
            
            # --- Method 4: Multi-Metric Correlation ---
            # Flag when spend goes up BUT conversions go down (or vice versa)
            if "spend" in df.columns and "conversions" in df.columns:
                recent_spend = df["spend"].iloc[-3:].mean()
                prior_spend = df["spend"].iloc[-10:-3].mean()
                recent_conv = df["conversions"].iloc[-3:].mean()
                prior_conv = df["conversions"].iloc[-10:-3].mean()
                
                if prior_spend > 0 and prior_conv > 0:
                    spend_change = (recent_spend - prior_spend) / prior_spend
                    conv_change = (recent_conv - prior_conv) / prior_conv
                    
                    # Divergence: spend up significantly + conversions down significantly
                    if spend_change > 0.2 and conv_change < -0.2:
                        already_found = any(
                            a["metric"] == "efficiency" and a["channel"] == ch
                            for a in channel_anomalies
                        )
                        if not already_found:
                            channel_anomalies.append({
                                "channel": ch,
                                "metric": "efficiency",
                                "current_value": round(recent_spend / max(recent_conv, 1), 2),
                                "expected_value": round(prior_spend / max(prior_conv, 1), 2),
                                "deviation_pct": round((spend_change - conv_change) * 100, 1),
                                "z_score": 3.0,  # Synthetic high score
                                "severity": "high",
                                "direction": "spike",
                                "detection_method": "multi_metric_divergence",
                                "detail": f"Spend {spend_change:+.0%} while conversions {conv_change:+.0%}",
                                "detected_at": datetime.now().isoformat(),
                            })
            
            anomalies.extend(channel_anomalies)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        anomalies.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
        return anomalies
    
    @staticmethod
    def _classify_severity(abs_z: float) -> str:
        """Classify anomaly severity from z-score magnitude."""
        if abs_z >= 4:
            return "critical"
        elif abs_z >= 3:
            return "high"
        elif abs_z >= 2.5:
            return "medium"
        else:
            return "low"
    
    def check_data_freshness(self) -> dict[str, datetime]:
        """Return last update timestamp for each source."""
        freshness = {}
        for channel, df in self._data.items():
            if not df.empty and "date" in df.columns:
                last_date = pd.to_datetime(df["date"]).max()
                freshness[channel] = last_date.to_pydatetime()
        return freshness
    
    def is_healthy(self) -> bool:
        """Check if data is loaded and recent."""
        return len(self._data) > 0
    
    def list_channels(self) -> list[str]:
        """List all available channels."""
        return list(self._data.keys())
    
    def get_campaign_breakdown(
        self,
        channel: str,
        days: int = 14,
    ) -> pd.DataFrame:
        """
        Get campaign-level breakdown.
        Mock: generates synthetic campaign splits from channel data.
        """
        df = self.get_channel_performance(channel, days)
        if df.empty:
            return pd.DataFrame()
        
        # Simulate 3 campaigns per channel
        campaigns = []
        campaign_names = [
            f"{channel}_brand_awareness",
            f"{channel}_conversion",
            f"{channel}_retargeting",
        ]
        
        for name in campaign_names:
            split = np.random.dirichlet([3, 2, 1])
            idx = campaign_names.index(name)
            
            camp_df = df.copy()
            camp_df["campaign_name"] = name
            camp_df["spend"] = camp_df["spend"] * split[idx]
            camp_df["conversions"] = (camp_df["conversions"] * split[idx]).astype(int)
            campaigns.append(camp_df)
        
        return pd.concat(campaigns, ignore_index=True)
