"""Mock implementation of strategy data (MMM & MTA) with Time-Series Support."""
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

class MockStrategyData:
    """
    Mock strategy data source.
    Loads MMM Saturation and MTA Attribution data with time-series support.
    """
    
    def __init__(self, data_dir: str = "data/mock_csv"):
        self.data_dir = Path(data_dir)
        self._mmm_json = {}  # Legacy JSON format
        self._mmm_ts = pd.DataFrame()  # Time-series CSV format
        self._mta_ts = pd.DataFrame()  # Time-series CSV format
        self._load_data()
    
    def _load_data(self) -> None:
        """Load strategy data files (supports both legacy JSON and new CSV time-series)."""
        mmm_json_path = self.data_dir / "mmm_saturation.json"
        mmm_csv_path = self.data_dir / "mmm_saturation.csv"
        mta_csv_path = self.data_dir / "mta_attribution.csv"
        
        # Try loading time-series CSV first (preferred)
        if mmm_csv_path.exists():
            try:
                self._mmm_ts = pd.read_csv(mmm_csv_path, parse_dates=["date"])
                print(f"  ✓ Loaded MMM time-series: {len(self._mmm_ts)} rows")
            except Exception as e:
                print(f"  ✗ Failed to load MMM CSV: {e}")
        # Fallback to legacy JSON
        elif mmm_json_path.exists():
            try:
                with open(mmm_json_path, "r") as f:
                    self._mmm_json = json.load(f)
                print(f"  ✓ Loaded MMM guardrails (legacy JSON): {len(self._mmm_json)} channels")
            except Exception as e:
                print(f"  ✗ Failed to load MMM JSON: {e}")
        else:
            print(f"  ⚠️ MMM file missing: {mmm_csv_path} or {mmm_json_path}")
                
        if mta_csv_path.exists():
            try:
                self._mta_ts = pd.read_csv(mta_csv_path, parse_dates=["date"] if "date" in pd.read_csv(mta_csv_path, nrows=1).columns else None)
                # Check if it's time-series (has date column) or static
                if "date" not in self._mta_ts.columns:
                    # Legacy static format - add a dummy date for compatibility
                    self._mta_ts["date"] = datetime.now()
                print(f"  ✓ Loaded MTA attribution: {len(self._mta_ts)} rows")
            except Exception as e:
                print(f"  ✗ Failed to load MTA: {e}")
        else:
            print(f"  ⚠️ MTA file missing: {mta_csv_path}")

    def get_mmm_guardrails(self, channel: str, reference_date: datetime | None = None) -> dict:
        """
        Get MMM saturation data for a channel as of a specific date.
        
        Args:
            channel: Channel name
            reference_date: Date to look up (defaults to most recent)
            
        Returns:
            Dict with saturation_point_daily, current_marginal_roas, recommendation
        """
        # If we have time-series data, use it
        if not self._mmm_ts.empty:
            df = self._mmm_ts[self._mmm_ts["channel"] == channel]
            
            if df.empty:
                return {}
            
            if reference_date:
                ref_ts = pd.Timestamp(reference_date)
                # Get the row closest to (but not after) the reference date
                df = df[df["date"] <= ref_ts]
                
            if df.empty:
                return {}
                
            # Get the most recent row
            row = df.sort_values("date").iloc[-1]
            
            return {
                "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None,
                "saturation_point_daily": row.get("saturation_point_daily", 0),
                "current_marginal_roas": row.get("current_marginal_roas", 0),
                "recommendation": row.get("recommendation", "maintain"),
            }
        
        # Fallback to legacy JSON
        return self._mmm_json.get(channel, {})

    def get_mta_comparison(self, channel: str, reference_date: datetime | None = None) -> dict:
        """
        Get MTA vs Last Click comparison for a channel as of a specific date.
        
        Args:
            channel: Channel name
            reference_date: Date to look up (defaults to most recent)
            
        Returns:
            Dict with last_click_roas, data_driven_roas, assist_ratio
        """
        if self._mta_ts.empty:
            return {}
        
        df = self._mta_ts[self._mta_ts["channel"] == channel]
        
        if df.empty:
            return {}
        
        if reference_date and "date" in df.columns:
            ref_ts = pd.Timestamp(reference_date)
            df = df[df["date"] <= ref_ts]
            
        if df.empty:
            return {}
        
        # Get the most recent row
        if "date" in df.columns:
            row = df.sort_values("date").iloc[-1]
        else:
            row = df.iloc[0]
        
        return {
            "date": row["date"].strftime("%Y-%m-%d") if "date" in row and pd.notna(row["date"]) else None,
            "channel": channel,
            "last_click_roas": row.get("last_click_roas", 0),
            "data_driven_roas": row.get("data_driven_roas", 0),
            "assist_ratio": row.get("assist_ratio", 0),
        }
    
    def get_mmm_history(self, channel: str, days: int = 30, end_date: datetime | None = None) -> pd.DataFrame:
        """
        Get MMM history for a channel over a time period.
        
        Useful for trend analysis and visualizations.
        """
        if self._mmm_ts.empty:
            return pd.DataFrame()
        
        if not end_date:
            end_date = datetime.now()
            
        start_date = end_date - timedelta(days=days)
        
        df = self._mmm_ts[
            (self._mmm_ts["channel"] == channel) &
            (self._mmm_ts["date"] >= pd.Timestamp(start_date)) &
            (self._mmm_ts["date"] <= pd.Timestamp(end_date))
        ].copy()
        
        return df.sort_values("date")
    
    def get_mta_history(self, channel: str, days: int = 30, end_date: datetime | None = None) -> pd.DataFrame:
        """
        Get MTA history for a channel over a time period.
        """
        if self._mta_ts.empty or "date" not in self._mta_ts.columns:
            return pd.DataFrame()
        
        if not end_date:
            end_date = datetime.now()
            
        start_date = end_date - timedelta(days=days)
        
        df = self._mta_ts[
            (self._mta_ts["channel"] == channel) &
            (self._mta_ts["date"] >= pd.Timestamp(start_date)) &
            (self._mta_ts["date"] <= pd.Timestamp(end_date))
        ].copy()
        
        return df.sort_values("date")