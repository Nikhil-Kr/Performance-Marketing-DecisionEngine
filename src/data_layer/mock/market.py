# """Mock implementation of market intelligence data."""
# from pathlib import Path
# import pandas as pd
# from datetime import datetime, timedelta

# class MockMarketData:
#     """Mock market intelligence data source."""
    
#     def __init__(self, data_dir: str = "data/mock_csv"):
#         self.data_dir = Path(data_dir)
#         self._competitors = pd.DataFrame()
#         self._trends = pd.DataFrame()
#         self._load_data()
    
#     def _load_data(self) -> None:
#         comp_path = self.data_dir / "competitors.csv"
#         trends_path = self.data_dir / "market_trends.csv"
        
#         if comp_path.exists():
#             try:
#                 self._competitors = pd.read_csv(comp_path, parse_dates=["date"])
#             except Exception: pass
                
#         if trends_path.exists():
#             try:
#                 self._trends = pd.read_csv(trends_path, parse_dates=["date"])
#             except Exception: pass

#     def get_competitor_signals(self, channel: str, lookback_days: int = 7) -> list[dict]:
#         if self._competitors.empty: return []
#         start_date = datetime.now() - timedelta(days=lookback_days)
#         mask = (self._competitors["date"] >= pd.Timestamp(start_date)) & (self._competitors["channel"] == channel)
#         df = self._competitors[mask].copy()
        
#         # Format dates for JSON
#         results = df.to_dict(orient="records")
#         for r in results:
#             if isinstance(r.get('date'), (pd.Timestamp, datetime)):
#                 r['date'] = r['date'].strftime('%Y-%m-%d')
#         return results

#     def get_market_interest(self, topic: str = "Donation", days: int = 30) -> list[dict]:
#         if self._trends.empty: return []
#         start_date = datetime.now() - timedelta(days=days)
#         mask = (self._trends["date"] >= pd.Timestamp(start_date))
#         df = self._trends[mask].copy()
        
#         results = df.to_dict(orient="records")
#         for r in results:
#             if isinstance(r.get('date'), (pd.Timestamp, datetime)):
#                 r['date'] = r['date'].strftime('%Y-%m-%d')
#         return results

"""Mock implementation of market intelligence data."""
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

class MockMarketData:
    def __init__(self, data_dir: str = "data/mock_csv"):
        self.data_dir = Path(data_dir)
        self._competitors = pd.DataFrame()
        self._trends = pd.DataFrame()
        self._load_data()
    
    def _load_data(self) -> None:
        try: 
            self._competitors = pd.read_csv(self.data_dir / "competitors.csv", parse_dates=["date"])
        except FileNotFoundError:
            print(f"  ⚠️ competitors.csv not found")
        except Exception as e:
            print(f"  ⚠️ Error loading competitors.csv: {e}")
        try: 
            self._trends = pd.read_csv(self.data_dir / "market_trends.csv", parse_dates=["date"])
        except FileNotFoundError:
            print(f"  ⚠️ market_trends.csv not found")
        except Exception as e:
            print(f"  ⚠️ Error loading market_trends.csv: {e}")

    def get_competitor_signals(self, channel: str, reference_date: datetime = None, lookback_days: int = 7) -> list[dict]:
        """Get competitor activity relative to a reference date."""
        if self._competitors.empty: return []
        
        # TIME TRAVEL LOGIC
        if not reference_date: reference_date = datetime.now()
        start_date = reference_date - timedelta(days=lookback_days)
        
        mask = (
            (self._competitors["date"] <= pd.Timestamp(reference_date)) &
            (self._competitors["date"] >= pd.Timestamp(start_date)) & 
            (self._competitors["channel"] == channel)
        )
        
        df = self._competitors[mask].copy()
        results = df.to_dict(orient="records")
        for r in results:
            if isinstance(r.get('date'), (pd.Timestamp, datetime)):
                r['date'] = r['date'].strftime('%Y-%m-%d')
        return results

    def get_market_interest(self, topic: str = "Donation", days: int = 30, end_date: datetime = None) -> list[dict]:
        """Get Google Trends relative to an end date."""
        if self._trends.empty: return []
        
        if not end_date: end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        mask = (self._trends["date"] <= pd.Timestamp(end_date)) & (self._trends["date"] >= pd.Timestamp(start_date))
        df = self._trends[mask].copy()
        
        results = df.to_dict(orient="records")
        for r in results:
            if isinstance(r.get('date'), (pd.Timestamp, datetime)):
                r['date'] = r['date'].strftime('%Y-%m-%d')
        return results