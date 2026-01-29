"""Abstract base class for all data sources."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
import pandas as pd


class BaseDataSource(ABC):
    """
    Abstract interface for data sources.
    
    Implement this for each data source type:
    - Mock implementations use CSV files
    - Production implementations use BigQuery/APIs
    
    The key is that ALL implementations have the SAME interface,
    so swapping mock → production is just changing an import.
    """
    
    @abstractmethod
    def get_metrics(
        self,
        channel: str,
        start_date: datetime,
        end_date: datetime,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Fetch performance metrics for a channel.
        
        Args:
            channel: Channel identifier (e.g., "google_search", "meta_ads")
            start_date: Start of date range
            end_date: End of date range
            metrics: Optional list of specific metrics to fetch
            
        Returns:
            DataFrame with date column and metric columns
        """
        pass
    
    @abstractmethod
    def get_anomalies(
        self,
        channel: str | None = None,
        lookback_hours: int = 24,
        threshold_sigma: float = 2.0,
    ) -> list[dict[str, Any]]:
        """
        Detect anomalies in recent data.
        
        Args:
            channel: Specific channel or None for all
            lookback_hours: How far back to check
            threshold_sigma: Standard deviation threshold for anomaly
            
        Returns:
            List of anomaly dictionaries
        """
        pass
    
    @abstractmethod
    def check_data_freshness(self) -> dict[str, datetime]:
        """
        Check when each data source was last updated.
        
        Used by Pre-Flight Check node to ensure data isn't stale.
        
        Returns:
            Dict mapping source name to last updated timestamp
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if data source is accessible and has recent data.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def list_channels(self) -> list[str]:
        """
        List all available channels.
        
        Returns:
            List of channel identifiers
        """
        pass
