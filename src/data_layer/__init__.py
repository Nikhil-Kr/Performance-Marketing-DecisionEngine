# """
# Data Layer Factory - Returns mock or production implementations.

# Usage:
#     from src.data_layer import get_marketing_data, get_influencer_data
    
#     marketing = get_marketing_data()  # Returns based on DATA_LAYER_MODE
#     influencer = get_influencer_data()
    
# To switch from mock to production:
#     1. Set DATA_LAYER_MODE=production in .env
#     2. Implement BigQueryMarketingData in connectors/bigquery.py
#     3. That's it - all your code works unchanged
# """
# import os
# from functools import lru_cache


# @lru_cache()
# def get_marketing_data():
#     """
#     Factory function for marketing data source.
#     Returns mock or production based on DATA_LAYER_MODE env var.
#     """
#     mode = os.getenv("DATA_LAYER_MODE", "mock")
    
#     if mode == "mock":
#         from .mock.marketing import MockMarketingData
#         print("📊 Loading mock marketing data...")
#         return MockMarketingData()
    
#     elif mode == "production":
#         # TODO: Implement when at GoFundMe
#         # from .connectors.bigquery import BigQueryMarketingData
#         # return BigQueryMarketingData()
#         raise NotImplementedError(
#             "Production mode not yet implemented.\n"
#             "Set DATA_LAYER_MODE=mock or implement BigQueryMarketingData."
#         )
    
#     else:
#         raise ValueError(f"Unknown DATA_LAYER_MODE: {mode}")


# @lru_cache()
# def get_influencer_data():
#     """
#     Factory function for influencer data source.
#     Returns mock or production based on DATA_LAYER_MODE env var.
#     """
#     mode = os.getenv("DATA_LAYER_MODE", "mock")
    
#     if mode == "mock":
#         from .mock.influencer import MockInfluencerData
#         print("👥 Loading mock influencer data...")
#         return MockInfluencerData()
    
#     elif mode == "production":
#         # TODO: Implement when at GoFundMe
#         # from .connectors.creatoriq import CreatorIQData
#         # return CreatorIQData()
#         raise NotImplementedError(
#             "Production mode not yet implemented.\n"
#             "Set DATA_LAYER_MODE=mock or implement CreatorIQData."
#         )
    
#     else:
#         raise ValueError(f"Unknown DATA_LAYER_MODE: {mode}")


# def clear_cache():
#     """Clear cached data sources (useful for testing)."""
#     get_marketing_data.cache_clear()
#     get_influencer_data.cache_clear()

# <------- TIER 3 & TIER 4 -------->
"""Data Layer Factory."""
import os
from functools import lru_cache

@lru_cache()
def get_marketing_data():
    mode = os.getenv("DATA_LAYER_MODE", "mock")
    if mode == "mock":
        from .mock.marketing import MockMarketingData
        return MockMarketingData()
    raise NotImplementedError("Production not implemented")

@lru_cache()
def get_influencer_data():
    mode = os.getenv("DATA_LAYER_MODE", "mock")
    if mode == "mock":
        from .mock.influencer import MockInfluencerData
        return MockInfluencerData()
    raise NotImplementedError("Production not implemented")

@lru_cache()
def get_market_data():
    mode = os.getenv("DATA_LAYER_MODE", "mock")
    if mode == "mock":
        from .mock.market import MockMarketData
        print("🕵️‍♀️ Loading mock market intelligence...")
        return MockMarketData()
    raise NotImplementedError("Production not implemented")

@lru_cache()
def get_strategy_data():
    mode = os.getenv("DATA_LAYER_MODE", "mock")
    if mode == "mock":
        from .mock.strategy import MockStrategyData
        print("🧠 Loading mock strategy data (MMM/MTA)...")
        return MockStrategyData()
    raise NotImplementedError("Production not implemented")

def clear_cache():
    get_marketing_data.cache_clear()
    get_influencer_data.cache_clear()
    get_market_data.cache_clear()
    get_strategy_data.cache_clear()
