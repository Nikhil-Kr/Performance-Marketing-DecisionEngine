# # #!/usr/bin/env python3
# # """
# # Generate high-fidelity mock marketing data for Project Expedition.
# # Includes "Needle in a Haystack" anomalies and a rich RAG history.
# # """
# # import pandas as pd
# # import numpy as np
# # from datetime import datetime, timedelta
# # from pathlib import Path
# # import random

# # # Configuration
# # np.random.seed(42)  # For reproducibility
# # MOCK_CSV_DIR = Path("data/mock_csv")
# # POST_MORTEMS_DIR = Path("data/post_mortems")
# # MOCK_CSV_DIR.mkdir(parents=True, exist_ok=True)
# # POST_MORTEMS_DIR.mkdir(parents=True, exist_ok=True)

# # # 90 Days of Data
# # END_DATE = datetime.now()
# # START_DATE = END_DATE - timedelta(days=90)
# # DATES = pd.date_range(start=START_DATE, end=END_DATE, freq="D")


# # def add_noise(base: float, volatility: float = 0.1) -> float:
# #     """Add realistic gaussian noise."""
# #     return max(0, base * (1 + np.random.normal(0, volatility)))


# # def generate_channel_data(
# #     channel: str,
# #     config: dict,
# #     anomalies: list = None
# # ) -> pd.DataFrame:
# #     """Generate daily performance data with injected anomalies."""
# #     data = []
    
# #     base_spend = config["base_spend"]
# #     base_cpa = config["base_cpa"]
# #     base_roas = config["base_roas"]
# #     trend = config.get("trend", 0.0)
# #     weekend_factor = config.get("weekend_effect", 0.8)
    
# #     total_days = len(DATES)

# #     for i, date in enumerate(DATES):
# #         # 1. Base Metrics
# #         daily_trend = (1 + trend) ** i
# #         is_weekend = date.weekday() >= 5
# #         seasonality = weekend_factor if is_weekend else 1.0
        
# #         spend = add_noise(base_spend * daily_trend * seasonality, 0.15)
# #         cpa = add_noise(base_cpa, 0.1)
# #         roas = add_noise(base_roas, 0.1)
        
# #         # 2. Inject Anomalies (The "Needles")
# #         # We calculate "days from end" using the index, which is safer than date math
# #         days_from_end = total_days - 1 - i
        
# #         if anomalies:
# #             for anomaly in anomalies:
# #                 # FIX: Ensure we check the range correctly (0 <= days <= 3)
# #                 if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
# #                     spend *= anomaly.get("spend_mult", 1.0)
# #                     cpa *= anomaly.get("cpa_mult", 1.0)
# #                     roas *= anomaly.get("roas_mult", 1.0)

# #         # 3. Derive Dependent Metrics
# #         conversions = int(spend / cpa) if cpa > 0 else 0
        
# #         # Apply conversion anomaly (e.g., Pixel Death)
# #         if anomalies:
# #             for anomaly in anomalies:
# #                 if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
# #                     conversions = int(conversions * anomaly.get("conv_mult", 1.0))

# #         revenue = spend * roas
# #         cpm = add_noise(15, 0.2)
# #         impressions = int(spend / cpm * 1000)
# #         ctr = add_noise(0.015, 0.1)
# #         clicks = int(impressions * ctr)
        
# #         # Recalculate realized metrics
# #         realized_cpa = spend / max(conversions, 1)
# #         realized_roas = revenue / max(spend, 1)

# #         data.append({
# #             "date": date,
# #             "channel": channel,
# #             "spend": round(spend, 2),
# #             "impressions": impressions,
# #             "clicks": clicks,
# #             "conversions": conversions,
# #             "revenue": round(revenue, 2),
# #             "cpa": round(realized_cpa, 2),
# #             "roas": round(realized_roas, 2),
# #             "ctr": round(clicks / max(impressions, 1), 4),
# #             "cpc": round(spend / max(clicks, 1), 2),
# #         })
        
# #     return pd.DataFrame(data)

# # # ============================================================================
# # # 1. DEFINING THE SCENARIOS
# # # ============================================================================

# # ANOMALIES = [
# #     {
# #         # SCENARIO 1: The "Obvious" Spike
# #         # Google PMax goes crazy spending budget on low-quality YouTube placements
# #         # Last 3 days (Days 3, 2, 1, 0 from end)
# #         "channel": "google_pmax",
# #         "start_day": 3, "end_day": 0,  
# #         "spend_mult": 3.0,  # CRITICAL: 3x Spend
# #         "roas_mult": 0.3,   # CRITICAL: 70% Drop in ROAS
# #         "description": "PMax Spend Spike"
# #     },
# #     {
# #         # SCENARIO 2: The "Silent Killer" (Broken Pixel)
# #         # Meta Ads spend is normal, but Conversions drop to near zero.
# #         # Last 2 days
# #         "channel": "meta_ads",
# #         "start_day": 2, "end_day": 0,
# #         "spend_mult": 1.0,  # Normal spend
# #         "conv_mult": 0.05,  # CRITICAL: 95% Drop in Conversions
# #         "description": "Pixel Tracking Failure"
# #     }
# # ]

# # CHANNELS_CONFIG = {
# #     # --- Paid Media ---
# #     "google_search": {"base_spend": 5000, "base_cpa": 45, "base_roas": 3.2},
# #     "google_pmax":   {"base_spend": 4000, "base_cpa": 35, "base_roas": 4.0},
# #     "google_display":{"base_spend": 2000, "base_cpa": 40, "base_roas": 2.5},
# #     "google_youtube":{"base_spend": 3500, "base_cpa": 45, "base_roas": 2.8},
# #     "meta_ads":      {"base_spend": 6000, "base_cpa": 28, "base_roas": 2.9},
# #     "tiktok_ads":    {"base_spend": 2500, "base_cpa": 22, "base_roas": 1.8},
# #     "linkedin_ads":  {"base_spend": 1500, "base_cpa": 120,"base_roas": 1.2},
# #     "programmatic":  {"base_spend": 3000, "base_cpa": 50, "base_roas": 1.5},
# #     "affiliate":     {"base_spend": 1000, "base_cpa": 15, "base_roas": 5.0},
    
# #     # --- Offline ---
# #     "direct_mail":   {"base_spend": 5000, "base_cpa": 60, "base_roas": 1.5, "weekend_effect": 0.1},
# #     "tv":            {"base_spend": 10000, "base_cpa": 150, "base_roas": 1.2},
# #     "radio":         {"base_spend": 3000, "base_cpa": 80, "base_roas": 1.4},
# #     "ooh":           {"base_spend": 4000, "base_cpa": 200, "base_roas": 1.1},
# #     "events":        {"base_spend": 8000, "base_cpa": 100, "base_roas": 1.3, "weekend_effect": 1.5},
# #     "podcast":       {"base_spend": 2500, "base_cpa": 55, "base_roas": 2.2},
# # }

# # print("📊 Generating Paid Media & Offline Mock Data...")
# # for channel, config in CHANNELS_CONFIG.items():
# #     df = generate_channel_data(channel, config, ANOMALIES)
# #     output_path = MOCK_CSV_DIR / f"{channel}.csv"
# #     df.to_csv(output_path, index=False)
# #     print(f"  ✓ {channel}: {len(df)} rows")


# # # ============================================================================
# # # 2. INFLUENCER DATA (With Fraud Scenario)
# # # ============================================================================

# # def generate_influencer_data():
# #     creators = [
# #         # The Fraudster
# #         {"id": "INF_999", "name": "ViralViper", "platform": "tiktok", "real": False},
# #         # The Good Ones
# #         {"id": "INF_001", "name": "TechGuru", "platform": "youtube", "real": True},
# #         {"id": "INF_002", "name": "FitLife", "platform": "instagram", "real": True},
# #         {"id": "INF_003", "name": "MomHacks", "platform": "instagram", "real": True},
# #         {"id": "INF_004", "name": "GamerX", "platform": "twitch", "real": True},
# #     ]
    
# #     data = []
# #     for creator in creators:
# #         # Create 3-4 posts per creator
# #         for i in range(4):
# #             # FIX: Ensure the Fraudster has a post TODAY (0 days ago) so it's a "Current" anomaly
# #             if not creator["real"] and i == 0:
# #                 date = END_DATE
# #             else:
# #                 date = END_DATE - timedelta(days=random.randint(1, 30))
            
# #             if creator["real"]:
# #                 # Healthy metrics
# #                 spend = random.randint(2000, 8000)
# #                 impressions = spend * random.randint(20, 50)
# #                 eng_rate = random.uniform(0.03, 0.08)
# #                 conv_rate = random.uniform(0.01, 0.03)
# #             else:
# #                 # SCENARIO 3: Fraud (High Vol, Low Eng/Conv)
# #                 spend = 15000  # High fees
# #                 impressions = 500000  # Massive reach (bots)
# #                 eng_rate = 0.001  # Tiny engagement
# #                 conv_rate = 0.0001 # Zero sales
            
# #             engagements = int(impressions * eng_rate)
# #             clicks = int(engagements * 0.2)
# #             conversions = int(clicks * conv_rate)
            
# #             data.append({
# #                 "campaign_id": f"CAMP_{random.randint(100,999)}",
# #                 "creator_id": creator["id"],
# #                 "creator_name": creator["name"],
# #                 "platform": creator["platform"],
# #                 "post_date": date,
# #                 "contract_value": spend,
# #                 "impressions": impressions,
# #                 "engagements": engagements,
# #                 "clicks": clicks,
# #                 "conversions": conversions,
# #                 "engagement_rate": round(eng_rate, 4),
# #                 "earned_media_value": spend * (0.2 if not creator["real"] else 2.5)
# #             })
            
# #     return pd.DataFrame(data)

# # print("\n👥 Generating Influencer Data...")
# # inf_df = generate_influencer_data()
# # inf_df.to_csv(MOCK_CSV_DIR / "influencer_campaigns.csv", index=False)
# # print(f"  ✓ influencer_campaigns: {len(inf_df)} rows")


# # # ============================================================================
# # # 3. RAG HISTORY (Expanded to 30 incidents)
# # # ============================================================================

# # def generate_rag_history():
# #     # Templates with variations to ensure unique embeddings
# #     templates = [
# #         # --- ORIGINAL DIGITAL CHANNELS ---
# #         {
# #             "type": "CPA Spike", 
# #             "channel": "google_search",
# #             "roots": [
# #                 "Competitor 'BrandX' aggressive bidding on brand terms.",
# #                 "New market entrant bidding heavily on our exact match keywords.",
# #                 "Auction insights show 40% overlap increase with top competitor.",
# #                 "Q4 seasonal competition drove up CPCs by 35%."
# #             ],
# #             "fixes": [
# #                 "Increased brand CPC bids by 20% and filed trademark complaint.",
# #                 "Launched defensive brand campaign with aggressive Top IS target.",
# #                 "Adjusted target CPA to defend impression share against BrandX.",
# #                 "Temporarily increased budget caps to capture holiday demand."
# #             ]
# #         },
# #         {
# #             "type": "Zero Conversions", 
# #             "channel": "meta_ads",
# #             "roots": [
# #                 "Tracking pixel fell off checkout page after deployment #1204.",
# #                 "GTM container rollback accidentally removed purchase event.",
# #                 "Server-side API token expired, causing event loss.",
# #                 "iOS update caused 48-hour reporting delay on conversions."
# #             ],
# #             "fixes": [
# #                 "Re-installed GTM container and added automated pixel monitoring.",
# #                 "Restored previous GTM version and verified checkout firing.",
# #                 "Generated new CAPI token and updated server config.",
# #                 "Switched to 7-day click attribution window for reporting."
# #             ]
# #         },
# #         {
# #             "type": "Spend Surge", 
# #             "channel": "google_pmax",
# #             "roots": [
# #                 "PMax auto-expanded to low quality Display inventory.",
# #                 "Algorithm aggressively targeted mobile app placements.",
# #                 "Uncapped budget allowed PMax to spend 300% of daily average.",
# #                 "Bot traffic spike on unknown placements drove up spend."
# #             ],
# #             "fixes": [
# #                 "Added placement exclusions and tightened location settings.",
# #                 "Excluded mobile app categories and gaming sites.",
# #                 "Implemented strict daily spend caps and tROAS targets.",
# #                 "Added negative IP lists and enabled click fraud protection."
# #             ]
# #         },
# #         {
# #             "type": "Low CTR", 
# #             "channel": "meta_ads",
# #             "roots": [
# #                 "Creative fatigue. Ad frequency exceeded 8.0.",
# #                 "Audience saturation in 'Lookalike 1%' audience.",
# #                 "Headline 'Free Shipping' no longer resonating with segment.",
# #                 "Broken video asset rendering as black screen."
# #             ],
# #             "fixes": [
# #                 "Refreshed creative assets and implemented frequency capping.",
# #                 "Expanded audience to 'Lookalike 5%' and broad interest.",
# #                 "Tested new '20% Off' hooks and headlines.",
# #                 "Re-uploaded video assets and cleared cache."
# #             ]
# #         },
        
# #         # --- NEW CHANNELS (TV, AFFILIATE, PODCAST, LINKEDIN) ---
# #         {
# #             "type": "High CPL",
# #             "channel": "linkedin_ads",
# #             "roots": [
# #                 "Audience size too small (<50k), leading to high frequency.",
# #                 "Job title targeting too broad, capturing entry-level roles.",
# #                 "LinkedIn Audience Network delivering low-quality clicks.",
# #             ],
# #             "fixes": [
# #                 "Expanded audience using lookalikes of customer list.",
# #                 "Added seniority exclusions to target decision makers only.",
# #                 "Disabled Audience Network to focus on feed placements.",
# #             ]
# #         },
# #         {
# #             "type": "Conversion Drop",
# #             "channel": "affiliate",
# #             "roots": [
# #                 "Top affiliate partner removed our link from their homepage.",
# #                 "Coupon code leakage to discount sites lowered AOV.",
# #                 "Fraudulent leads detected from new sub-affiliate network.",
# #             ],
# #             "fixes": [
# #                 "Renegotiated placement with top partner.",
# #                 "Invalidated leaked codes and issued exclusive links.",
# #                 "Voided commissions for fraudulent leads and blocked sub-ID.",
# #             ]
# #         },
# #         {
# #             "type": "Reach Drop",
# #             "channel": "tv",
# #             "roots": [
# #                 "Primetime spots preempted by breaking news coverage.",
# #                 "Frequency cap issues on Connected TV (CTV) inventory.",
# #                 "Measurement lag from Nielsen reporting caused data gap.",
# #             ],
# #             "fixes": [
# #                 "Received make-goods for preempted spots next week.",
# #                 "Applied strict frequency capping across CTV publishers.",
# #                 "Used spot logs for interim reporting while awaiting Nielsen.",
# #             ]
# #         },
# #         {
# #             "type": "Low Engagement",
# #             "channel": "podcast",
# #             "roots": [
# #                 "Host read script was truncated during recording.",
# #                 "Promo code mentioned on air didn't match backend.",
# #                 "Episode released on holiday weekend with low downloads.",
# #             ],
# #             "fixes": [
# #                 "Requested re-read/make-good for next episode.",
# #                 "Created vanity URL redirect to fix promo code error.",
# #                 "Shifted future ad buys to mid-week release schedules.",
# #             ]
# #         },
# #         {
# #             "type": "Fraud Alert",
# #             "channel": "influencer",
# #             "roots": [
# #                 "Creator engagement rate 0.01% despite 1M followers.",
# #                 "Comment section filled with generic bot spam.",
# #                 "Sudden spike in followers from non-target geo (click farm).",
# #             ],
# #             "fixes": [
# #                 "Terminated contract for breach of authenticity clause.",
# #                 "Blacklisted creator from future campaigns.",
# #                 "Implemented vetting tool to audit audience quality pre-hire.",
# #             ]
# #         }
# #     ]
    
# #     incidents = []
# #     start_hist = datetime.now() - timedelta(days=365)
    
# #     for i in range(40): # Increased to 40 to cover new channels
# #         template = random.choice(templates)
# #         date = start_hist + timedelta(days=random.randint(1, 360))
        
# #         # Pick random variations
# #         root = random.choice(template["roots"])
# #         fix = random.choice(template["fixes"])
        
# #         incidents.append({
# #             "incident_id": f"INC-{date.year}-{i+100}",
# #             "date": date.strftime("%Y-%m-%d"),
# #             "channel": template["channel"],
# #             "anomaly_type": template["type"],
# #             "severity": random.choice(["high", "medium", "critical"]),
# #             "root_cause": root,
# #             "resolution": fix,
# #             "similarity_score": round(random.uniform(0.7, 0.95), 2) # Mock score for raw file
# #         })
        
# #     return pd.DataFrame(incidents)

# # print("\n📜 Generating 40+ RAG Post-Mortems...")
# # rag_df = generate_rag_history()
# # rag_df.to_csv(POST_MORTEMS_DIR / "incidents.csv", index=False)
# # print(f"  ✓ incidents: {len(rag_df)} rows")

# # print("\n" + "="*60)
# # print("✅ Mock Data Generation Complete")
# # print("   Run 'make init-rag' to load this into the Vector Store.")
# # print("="*60)


# #<------ TIER 3 & TIER 4 UPDATE ----->

# #!/usr/bin/env python3
# """
# Generate high-fidelity mock marketing data for Project Expedition.
# Includes "Needle in a Haystack" anomalies and a rich RAG history.
# """
# import pandas as pd
# import numpy as np
# from datetime import datetime, timedelta
# from pathlib import Path
# import random
# import json

# # Configuration
# np.random.seed(42)  # For reproducibility
# MOCK_CSV_DIR = Path("data/mock_csv")
# POST_MORTEMS_DIR = Path("data/post_mortems")
# MOCK_CSV_DIR.mkdir(parents=True, exist_ok=True)
# POST_MORTEMS_DIR.mkdir(parents=True, exist_ok=True)

# # Default dates (can be overridden via CLI)
# # These will be set by main() based on CLI args
# END_DATE = None
# START_DATE = None
# DATES = None

# def configure_dates(end_date: datetime = None, history_years: int = 6):
#     """Configure date range for data generation."""
#     global END_DATE, START_DATE, DATES
    
#     if end_date is None:
#         END_DATE = datetime.now()
#     else:
#         END_DATE = end_date
    
#     START_DATE = END_DATE - timedelta(days=365 * history_years)
#     DATES = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    
#     return END_DATE, START_DATE, DATES

# # Initialize with defaults for backwards compatibility
# configure_dates()


# def add_noise(base: float, volatility: float = 0.1) -> float:
#     """Add realistic gaussian noise."""
#     return max(0, base * (1 + np.random.normal(0, volatility)))


# def generate_channel_data(
#     channel: str,
#     config: dict,
#     anomalies: list = None
# ) -> pd.DataFrame:
#     """Generate daily performance data with injected anomalies."""
#     data = []
    
#     base_spend = config["base_spend"]
#     base_cpa = config["base_cpa"]
#     base_roas = config["base_roas"]
#     trend = config.get("trend", 0.0001) # Slight long-term trend
#     weekend_factor = config.get("weekend_effect", 0.8)
    
#     total_days = len(DATES)

#     for i, date in enumerate(DATES):
#         # 1. Base Metrics
#         daily_trend = (1 + trend) ** i
#         is_weekend = date.weekday() >= 5
#         seasonality = weekend_factor if is_weekend else 1.0
        
#         # Annual Seasonality (higher in Q4)
#         day_of_year = date.timetuple().tm_yday
#         q4_boost = 1.3 if day_of_year > 300 else 1.0
        
#         spend = add_noise(base_spend * daily_trend * seasonality * q4_boost, 0.15)
#         cpa = add_noise(base_cpa, 0.1)
#         roas = add_noise(base_roas, 0.1)
        
#         # 2. Inject Random Historical Anomalies (visual richness for charts)
#         if random.random() < 0.005 and i < total_days - 30:
#             anomaly_type = random.choice(["spend_spike", "roas_drop", "conversion_blip"])
#             if anomaly_type == "spend_spike":
#                 spend *= 2.5
#             elif anomaly_type == "roas_drop":
#                 roas *= 0.5
#             elif anomaly_type == "conversion_blip":
#                 cpa *= 0.2

#         # 3. Inject DEFINED Anomalies (The "Current Fires")
#         days_from_end = total_days - 1 - i
        
#         if anomalies:
#             for anomaly in anomalies:
#                 if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
#                     spend *= anomaly.get("spend_mult", 1.0)
#                     cpa *= anomaly.get("cpa_mult", 1.0)
#                     roas *= anomaly.get("roas_mult", 1.0)

#         # 4. Derive Dependent Metrics
#         conversions = int(spend / cpa) if cpa > 0 else 0
        
#         if anomalies:
#             for anomaly in anomalies:
#                 if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
#                     conversions = int(conversions * anomaly.get("conv_mult", 1.0))

#         revenue = spend * roas
#         cpm = add_noise(15, 0.2)
#         impressions = int(spend / cpm * 1000)
#         ctr = add_noise(0.015, 0.1)
#         clicks = int(impressions * ctr)
        
#         # Recalculate realized metrics
#         realized_cpa = spend / max(conversions, 1)
#         realized_roas = revenue / max(spend, 1)

#         data.append({
#             "date": date,
#             "channel": channel,
#             "spend": round(spend, 2),
#             "impressions": impressions,
#             "clicks": clicks,
#             "conversions": conversions,
#             "revenue": round(revenue, 2),
#             "cpa": round(realized_cpa, 2),
#             "roas": round(realized_roas, 2),
#             "ctr": round(clicks / max(impressions, 1), 4),
#             "cpc": round(spend / max(clicks, 1), 2),
#         })
        
#     return pd.DataFrame(data)

# # ============================================================================
# # 1. ANOMALY SCENARIOS (RESTORED TO CRITICAL LEVELS)
# # ============================================================================

# ANOMALIES = [
#     {
#         # SCENARIO 1: Competitor Bidding Spike (Google Search)
#         "channel": "google_search",
#         "start_day": 3, "end_day": 0,  
#         "spend_mult": 1.5,  # Moderate spend increase
#         "cpa_mult": 2.5,    # Massive CPA spike (due to bidding war)
#         "description": "Competitor Bidding War"
#     },
#     {
#         # SCENARIO 2: Saturated Channel (Google PMax)
#         "channel": "google_pmax",
#         "start_day": 2, "end_day": 0,
#         "spend_mult": 1.2, # Tried to scale
#         "roas_mult": 0.6,  # ROAS tanked (Saturation)
#         "description": "Inefficient Scaling"
#     },
#     {
#         # SCENARIO 3: The "Silent Killer" (Broken Pixel)
#         # Meta Ads spend is normal, but Conversions drop to near zero.
#         "channel": "meta_ads",
#         "start_day": 2, "end_day": 0,
#         "spend_mult": 1.0,  # Normal spend
#         "conv_mult": 0.05,  # CRITICAL: 95% Drop in Conversions
#         "description": "Pixel Tracking Failure"
#     }
# ]

# CHANNELS_CONFIG = {
#     # --- Paid Media ---
#     "google_search": {"base_spend": 5000, "base_cpa": 45, "base_roas": 3.2},
#     "google_pmax":   {"base_spend": 4000, "base_cpa": 35, "base_roas": 4.0},
#     "google_display":{"base_spend": 2000, "base_cpa": 40, "base_roas": 2.5},
#     "google_youtube":{"base_spend": 3500, "base_cpa": 45, "base_roas": 2.8},
#     "meta_ads":      {"base_spend": 6000, "base_cpa": 28, "base_roas": 2.9},
#     "tiktok_ads":    {"base_spend": 2500, "base_cpa": 22, "base_roas": 1.8},
#     "linkedin_ads":  {"base_spend": 1500, "base_cpa": 120,"base_roas": 1.2},
    
#     # --- Offline ---
#     "tv":            {"base_spend": 10000, "base_cpa": 150, "base_roas": 1.2},
#     "podcast":       {"base_spend": 2500, "base_cpa": 55, "base_roas": 2.2},
# }

# print("📊 Generating Paid Media & Offline Mock Data...")
# for channel, config in CHANNELS_CONFIG.items():
#     df = generate_channel_data(channel, config, ANOMALIES)
#     output_path = MOCK_CSV_DIR / f"{channel}.csv"
#     df.to_csv(output_path, index=False)
#     print(f"  ✓ {channel}: {len(df)} rows")


# # ============================================================================
# # 2. INFLUENCER DATA
# # ============================================================================

# def generate_influencer_data():
#     creators = [
#         {"id": "INF_999", "name": "ViralViper", "platform": "tiktok", "real": False}, # Fraud
#         {"id": "INF_001", "name": "TechGuru", "platform": "youtube", "real": True},
#         {"id": "INF_002", "name": "FitLife", "platform": "instagram", "real": True},
#         {"id": "INF_003", "name": "MomHacks", "platform": "instagram", "real": True},
#         {"id": "INF_004", "name": "GamerX", "platform": "twitch", "real": True},
#     ]
    
#     data = []
#     total_days = (END_DATE - START_DATE).days
    
#     for creator in creators:
#         num_posts = int(total_days / 14) 
#         post_dates = sorted([
#             START_DATE + timedelta(days=random.randint(0, total_days)) 
#             for _ in range(num_posts)
#         ])
        
#         if post_dates[-1] < END_DATE - timedelta(hours=24):
#             post_dates.append(END_DATE)
            
#         for date in post_dates:
#             is_recent = (END_DATE - date).days <= 1
            
#             if not creator["real"]:
#                 if is_recent:
#                     spend = 15000
#                     impressions = 500000
#                     eng_rate = 0.0001
#                     conv_rate = 0.0000
#                 else:
#                     spend = add_noise(5000, 0.2)
#                     impressions = int(spend * 20)
#                     eng_rate = add_noise(0.05, 0.1)
#                     conv_rate = add_noise(0.02, 0.1)
#             else:
#                 spend = add_noise(random.randint(2000, 8000), 0.2)
#                 impressions = int(spend * random.randint(20, 50))
#                 eng_rate = add_noise(random.uniform(0.03, 0.08), 0.1)
#                 conv_rate = add_noise(random.uniform(0.01, 0.03), 0.1)
            
#             engagements = int(impressions * eng_rate)
#             clicks = int(engagements * 0.2)
#             conversions = int(clicks * conv_rate)
            
#             data.append({
#                 "campaign_id": f"CAMP_{random.randint(100,999)}",
#                 "creator_id": creator["id"],
#                 "creator_name": creator["name"],
#                 "platform": creator["platform"],
#                 "post_date": date,
#                 "contract_value": round(spend, 2),
#                 "impressions": impressions,
#                 "engagements": engagements,
#                 "clicks": clicks,
#                 "conversions": conversions,
#                 "engagement_rate": round(eng_rate, 4),
#                 "earned_media_value": round(spend * (0.2 if not creator["real"] and is_recent else 2.5), 2)
#             })
            
#     return pd.DataFrame(data)

# print("\n👥 Generating Influencer Data...")
# inf_df = generate_influencer_data()
# inf_df.to_csv(MOCK_CSV_DIR / "influencer_campaigns.csv", index=False)
# print(f"  ✓ influencer_campaigns: {len(inf_df)} rows")


# # ============================================================================
# # 3. RAG HISTORY
# # ============================================================================

# def generate_rag_history():
#     templates = [
#         {"type": "CPA Spike", "channel": "google_search", "roots": ["Competitor 'BrandX' aggressive bidding."], "fixes": ["Increased brand CPC bids."]},
#         {"type": "Reach Drop", "channel": "tv", "roots": ["Primetime spots preempted by breaking news."], "fixes": ["Received make-goods."]},
#         {"type": "Fraud Alert", "channel": "influencer", "roots": ["Creator engagement rate 0.01% despite 1M followers."], "fixes": ["Terminated contract for breach of authenticity."]},
#         {"type": "Zero Conversions", "channel": "meta_ads", "roots": ["Tracking pixel fell off checkout page."], "fixes": ["Re-installed GTM container."]},
#     ]
#     incidents = []
#     start_hist = START_DATE
    
#     for i in range(100):
#         t = random.choice(templates)
#         days_offset = random.randint(0, (END_DATE - START_DATE).days)
#         date = start_hist + timedelta(days=days_offset)
        
#         incidents.append({
#             "incident_id": f"INC-{date.year}-{i+100}",
#             "date": date.strftime("%Y-%m-%d"),
#             "channel": t["channel"],
#             "anomaly_type": t["type"],
#             "severity": "high",
#             "root_cause": random.choice(t["roots"]),
#             "resolution": random.choice(t["fixes"]),
#             "similarity_score": round(random.uniform(0.7, 0.95), 2)
#         })
#     return pd.DataFrame(incidents)

# print("\n📜 Generating RAG Post-Mortems...")
# rag_df = generate_rag_history()
# rag_df.to_csv(POST_MORTEMS_DIR / "incidents.csv", index=False)
# print(f"  ✓ incidents: {len(rag_df)} rows")


# # ============================================================================
# # 4. MARKET & STRATEGY DATA (TIER 3 & 4)
# # ============================================================================

# def generate_competitor_intel():
#     """Generate mock competitor activity signals."""
#     data = []
#     for i, date in enumerate(DATES):
#         if i >= len(DATES) - 3:
#             data.append({
#                 "date": date,
#                 "competitor": "BrandX",
#                 "channel": "google_search",
#                 "activity_type": "aggressive_bidding",
#                 "impact_level": "high",
#                 "details": "Impression share lost increased 15%"
#             })
#     return pd.DataFrame(data)

# def generate_market_trends():
#     """Generate Google Trends style market interest data."""
#     data = []
#     for i, date in enumerate(DATES):
#         year_trend = (i / len(DATES)) * 20
#         seasonality = 15 * np.sin(i / 180)
#         interest = 40 + year_trend + seasonality + np.random.normal(0, 2)
#         data.append({"date": date, "topic": "Donation", "interest_score": round(interest, 1)})
#     return pd.DataFrame(data)

# def generate_mmm_guardrails_history():
#     """
#     Generate daily MMM saturation data over time (Time-Series).
#     Allows 'Time Travel' analysis.
#     """
#     data = []
    
#     # Base config for channels
#     configs = {
#         "google_search": {"base_sat": 8000, "base_roas": 2.1},
#         "google_pmax":   {"base_sat": 5000, "base_roas": 0.8}, # Saturated
#         "meta_ads":      {"base_sat": 10000, "base_roas": 1.4}
#     }
    
#     for i, date in enumerate(DATES):
#         for channel, cfg in configs.items():
#             # Add some drift over time
#             drift = np.sin(i / 365) * 0.2
            
#             # Scenario: PMax becomes saturated recently (last 30 days)
#             # Before that, it was fine.
#             if channel == "google_pmax":
#                 if i > len(DATES) - 30:
#                     roas = 0.8 # Saturated
#                     rec = "maintain"
#                 else:
#                     roas = 1.3 # Healthy
#                     rec = "scale"
#             else:
#                 roas = cfg["base_roas"] + drift
#                 rec = "scale" if roas > 1.2 else "maintain"
            
#             data.append({
#                 "date": date,
#                 "channel": channel,
#                 "saturation_point_daily": int(cfg["base_sat"] * (1 + drift)),
#                 "current_marginal_roas": round(roas, 2),
#                 "recommendation": rec
#             })
#     return pd.DataFrame(data)

# def generate_mta_attribution_history():
#     """
#     Generate daily MTA vs Last Click comparison (Time-Series).
#     """
#     data = []
    
#     # Base multipliers (MTA / Last Click)
#     multipliers = {
#         "google_youtube": 5.6, # MTA is much higher
#         "google_search": 0.8,  # Last click is higher
#         "meta_ads": 1.16       # Slightly higher MTA
#     }
    
#     for i, date in enumerate(DATES):
#         for channel, mult in multipliers.items():
#             # Generate base last click (randomized around a mean)
#             last_click = 2.0 + np.random.normal(0, 0.2)
#             if channel == "google_youtube": last_click = 0.5
#             if channel == "google_search": last_click = 4.0
#             if channel == "meta_ads": last_click = 2.5
            
#             mta_roas = last_click * mult + np.random.normal(0, 0.1)
            
#             data.append({
#                 "date": date,
#                 "channel": channel,
#                 "last_click_roas": round(last_click, 2),
#                 "data_driven_roas": round(mta_roas, 2),
#                 "assist_ratio": round(1.0 - (1.0/mult if mult > 1 else mult), 2)
#             })
#     return pd.DataFrame(data)

# print("\n🧠 Generating Tier 3 & 4 Data (Time-Series)...")
# comp_df = generate_competitor_intel()
# comp_df.to_csv(MOCK_CSV_DIR / "competitors.csv", index=False)

# trends_df = generate_market_trends()
# trends_df.to_csv(MOCK_CSV_DIR / "market_trends.csv", index=False)

# # NOW SAVING AS CSV (Time Series) instead of JSON
# mmm_df = generate_mmm_guardrails_history()
# mmm_df.to_csv(MOCK_CSV_DIR / "mmm_saturation.csv", index=False)
# print("  ✓ mmm_saturation.csv generated (Time-Series)")

# # NOW SAVING AS CSV (Time Series)
# mta_df = generate_mta_attribution_history()
# mta_df.to_csv(MOCK_CSV_DIR / "mta_attribution.csv", index=False)
# print("  ✓ mta_attribution.csv generated (Time-Series)")

# print("\n" + "="*60)
# print("✅ Mock Data Generation Complete")
# print(f"   Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
# print("   Run 'make init-rag' to load this into the Vector Store.")
# print("="*60)


# def main():
#     """Main entry point with CLI support."""
#     import argparse
    
#     parser = argparse.ArgumentParser(
#         description="Generate mock marketing data for Project Expedition"
#     )
#     parser.add_argument(
#         "--end-date", 
#         type=str, 
#         help="End date for data generation (YYYY-MM-DD). Default: today"
#     )
#     parser.add_argument(
#         "--history-years",
#         type=int,
#         default=6,
#         help="Years of historical data to generate. Default: 6"
#     )
#     parser.add_argument(
#         "--seed",
#         type=int,
#         default=42,
#         help="Random seed for reproducibility. Default: 42"
#     )
    
#     args = parser.parse_args()
    
#     # Set random seed
#     np.random.seed(args.seed)
#     random.seed(args.seed)
    
#     # Parse end date
#     end_date = None
#     if args.end_date:
#         try:
#             end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
#             print(f"📅 Using custom end date: {args.end_date}")
#         except ValueError:
#             print(f"⚠️ Invalid date format: {args.end_date}. Using today's date.")
    
#     # Reconfigure dates with CLI parameters
#     configure_dates(end_date=end_date, history_years=args.history_years)
    
#     print(f"📊 Generating {args.history_years} years of data ending {END_DATE.strftime('%Y-%m-%d')}")
    
#     # Note: The data generation happens at module load time (above)
#     # For a cleaner implementation, you would move all generation into this function
#     # But for backwards compatibility, we keep the existing behavior


# if __name__ == "__main__":
#     # If run directly with CLI args, parse them
#     import sys
#     if len(sys.argv) > 1:
#         main()
#     # Otherwise, data was already generated at module load time

# <--- Latest ---->

#!/usr/bin/env python3
"""
Generate high-fidelity mock marketing data for Project Expedition.
Includes "Needle in a Haystack" anomalies, varied MMM/MTA/Competitor data, and RAG history.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import random

# Configuration
np.random.seed(42)
random.seed(42)
MOCK_CSV_DIR = Path("data/mock_csv")
POST_MORTEMS_DIR = Path("data/post_mortems")
MOCK_CSV_DIR.mkdir(parents=True, exist_ok=True)
POST_MORTEMS_DIR.mkdir(parents=True, exist_ok=True)

# 90 Days of Data
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=90)
DATES = pd.date_range(start=START_DATE, end=END_DATE, freq="D")


def configure_dates(end_date: datetime = None, history_years: int = 0):
    """Reconfigure date ranges (for CLI support)."""
    global END_DATE, START_DATE, DATES
    if end_date:
        END_DATE = end_date
    days = history_years * 365 if history_years > 0 else 90
    START_DATE = END_DATE - timedelta(days=days)
    DATES = pd.date_range(start=START_DATE, end=END_DATE, freq="D")


def add_noise(base: float, volatility: float = 0.1) -> float:
    """Add realistic gaussian noise."""
    return max(0, base * (1 + np.random.normal(0, volatility)))


# ============================================================================
# ALL CHANNELS DEFINITION (Single Source of Truth)
# ============================================================================

ALL_CHANNELS = [
    # Digital - Search & Shopping
    "google_search", "google_pmax", "google_display", "google_youtube",
    # Social
    "meta_ads", "tiktok_ads", "linkedin_ads",
    # Programmatic & Affiliate
    "programmatic", "affiliate",
    # Offline
    "tv", "podcast", "radio", "direct_mail", "ooh", "events",
]

CHANNELS_CONFIG = {
    # --- Paid Media ---
    "google_search": {"base_spend": 5000, "base_cpa": 45, "base_roas": 3.2},
    "google_pmax":   {"base_spend": 4000, "base_cpa": 35, "base_roas": 4.0},
    "google_display":{"base_spend": 2000, "base_cpa": 40, "base_roas": 2.5},
    "google_youtube":{"base_spend": 3500, "base_cpa": 45, "base_roas": 2.8},
    "meta_ads":      {"base_spend": 6000, "base_cpa": 28, "base_roas": 2.9},
    "tiktok_ads":    {"base_spend": 2500, "base_cpa": 22, "base_roas": 1.8},
    "linkedin_ads":  {"base_spend": 1500, "base_cpa": 120,"base_roas": 1.2},
    "programmatic":  {"base_spend": 3000, "base_cpa": 50, "base_roas": 1.5},
    "affiliate":     {"base_spend": 1000, "base_cpa": 15, "base_roas": 5.0},
    
    # --- Offline ---
    "direct_mail":   {"base_spend": 5000, "base_cpa": 60, "base_roas": 1.5, "weekend_effect": 0.1},
    "tv":            {"base_spend": 10000, "base_cpa": 150, "base_roas": 1.2},
    "radio":         {"base_spend": 3000, "base_cpa": 80, "base_roas": 1.4},
    "ooh":           {"base_spend": 4000, "base_cpa": 200, "base_roas": 1.1},
    "events":        {"base_spend": 8000, "base_cpa": 100, "base_roas": 1.3, "weekend_effect": 1.5},
    "podcast":       {"base_spend": 2500, "base_cpa": 55, "base_roas": 2.2},
}


# ============================================================================
# 1. CHANNEL PERFORMANCE DATA
# ============================================================================

ANOMALIES = [
    {
        # SCENARIO 1: The "Obvious" Spike - PMax overspending
        "channel": "google_pmax",
        "start_day": 3, "end_day": 0,
        "spend_mult": 3.0,
        "roas_mult": 0.3,
        "description": "PMax Spend Spike"
    },
    {
        # SCENARIO 2: The "Silent Killer" - Broken Pixel
        "channel": "meta_ads",
        "start_day": 2, "end_day": 0,
        "spend_mult": 1.0,
        "conv_mult": 0.05,
        "description": "Pixel Tracking Failure"
    }
]


def generate_channel_data(channel: str, config: dict, anomalies: list = None) -> pd.DataFrame:
    """Generate daily performance data with injected anomalies."""
    data = []
    
    base_spend = config["base_spend"]
    base_cpa = config["base_cpa"]
    base_roas = config["base_roas"]
    trend = config.get("trend", 0.0)
    weekend_factor = config.get("weekend_effect", 0.8)
    
    total_days = len(DATES)

    for i, date in enumerate(DATES):
        daily_trend = (1 + trend) ** i
        is_weekend = date.weekday() >= 5
        seasonality = weekend_factor if is_weekend else 1.0
        
        spend = add_noise(base_spend * daily_trend * seasonality, 0.15)
        cpa = add_noise(base_cpa, 0.1)
        roas = add_noise(base_roas, 0.1)
        
        days_from_end = total_days - 1 - i
        
        if anomalies:
            for anomaly in anomalies:
                if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
                    spend *= anomaly.get("spend_mult", 1.0)
                    cpa *= anomaly.get("cpa_mult", 1.0)
                    roas *= anomaly.get("roas_mult", 1.0)

        conversions = int(spend / cpa) if cpa > 0 else 0
        
        if anomalies:
            for anomaly in anomalies:
                if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
                    conversions = int(conversions * anomaly.get("conv_mult", 1.0))

        revenue = spend * roas
        cpm = add_noise(15, 0.2)
        impressions = int(spend / cpm * 1000)
        ctr = add_noise(0.015, 0.1)
        clicks = int(impressions * ctr)
        
        realized_cpa = spend / max(conversions, 1)
        realized_roas = revenue / max(spend, 1)

        data.append({
            "date": date,
            "channel": channel,
            "spend": round(spend, 2),
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue": round(revenue, 2),
            "cpa": round(realized_cpa, 2),
            "roas": round(realized_roas, 2),
            "ctr": round(clicks / max(impressions, 1), 4),
            "cpc": round(spend / max(clicks, 1), 2),
        })
        
    return pd.DataFrame(data)


print("📊 Generating Paid Media & Offline Mock Data...")
for channel, config in CHANNELS_CONFIG.items():
    df = generate_channel_data(channel, config, ANOMALIES)
    output_path = MOCK_CSV_DIR / f"{channel}.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✓ {channel}: {len(df)} rows")


# ============================================================================
# 2. INFLUENCER DATA
# ============================================================================

def generate_influencer_data():
    creators = [
        {"id": "INF_999", "name": "ViralViper", "platform": "tiktok", "real": False},
        {"id": "INF_001", "name": "TechGuru", "platform": "youtube", "real": True},
        {"id": "INF_002", "name": "FitLife", "platform": "instagram", "real": True},
        {"id": "INF_003", "name": "MomHacks", "platform": "instagram", "real": True},
        {"id": "INF_004", "name": "GamerX", "platform": "twitch", "real": True},
    ]
    
    data = []
    total_days = (END_DATE - START_DATE).days
    
    for creator in creators:
        num_posts = int(total_days / 14) 
        post_dates = sorted([
            START_DATE + timedelta(days=random.randint(0, total_days)) 
            for _ in range(num_posts)
        ])
        
        if post_dates[-1] < END_DATE - timedelta(hours=24):
            post_dates.append(END_DATE)
            
        for date in post_dates:
            is_recent = (END_DATE - date).days <= 1
            
            if not creator["real"]:
                if is_recent:
                    spend = 15000
                    impressions = 500000
                    eng_rate = 0.0001
                    conv_rate = 0.0000
                else:
                    spend = add_noise(5000, 0.2)
                    impressions = int(spend * 20)
                    eng_rate = add_noise(0.05, 0.1)
                    conv_rate = add_noise(0.02, 0.1)
            else:
                spend = add_noise(random.randint(2000, 8000), 0.2)
                impressions = int(spend * random.randint(20, 50))
                eng_rate = add_noise(random.uniform(0.03, 0.08), 0.1)
                conv_rate = add_noise(random.uniform(0.01, 0.03), 0.1)
            
            engagements = int(impressions * eng_rate)
            clicks = int(engagements * 0.2)
            conversions = int(clicks * conv_rate)
            
            data.append({
                "campaign_id": f"CAMP_{random.randint(100,999)}",
                "creator_id": creator["id"],
                "creator_name": creator["name"],
                "platform": creator["platform"],
                "post_date": date,
                "contract_value": round(spend, 2),
                "impressions": impressions,
                "engagements": engagements,
                "clicks": clicks,
                "conversions": conversions,
                "engagement_rate": round(eng_rate, 4),
                "earned_media_value": round(spend * (0.2 if not creator["real"] and is_recent else 2.5), 2)
            })
            
    return pd.DataFrame(data)

print("\n👥 Generating Influencer Data...")
inf_df = generate_influencer_data()
inf_df.to_csv(MOCK_CSV_DIR / "influencer_campaigns.csv", index=False)
print(f"  ✓ influencer_campaigns: {len(inf_df)} rows")


# ============================================================================
# 3. RAG HISTORY (Post-Mortems)
# ============================================================================

def generate_rag_history():
    """Generate diverse post-mortem incidents for RAG."""
    templates = [
        # Google
        {"type": "CPA Spike", "channel": "google_search", "roots": ["Competitor 'BrandX' aggressive bidding on brand terms.", "Quality Score dropped due to landing page changes.", "Broad match keywords triggered irrelevant searches."], "fixes": ["Increased brand CPC bids by 25%.", "Reverted landing page changes.", "Added negative keywords."]},
        {"type": "ROAS Drop", "channel": "google_pmax", "roots": ["Asset group creative fatigue.", "PMax shifted budget to low-converting placements.", "Shopping feed had stale inventory data."], "fixes": ["Refreshed creative assets.", "Excluded YouTube placements.", "Fixed feed sync issues."]},
        {"type": "Spend Spike", "channel": "google_display", "roots": ["New audience segment had high CPMs.", "Frequency capping disabled accidentally.", "Competitor exited, auctions got cheaper - pacing accelerated."], "fixes": ["Adjusted audience bids.", "Re-enabled frequency caps.", "Set daily budget caps."]},
        
        # Meta
        {"type": "Zero Conversions", "channel": "meta_ads", "roots": ["Tracking pixel removed during site update.", "iOS 14 ATT opt-outs increased.", "Conversion API misconfigured."], "fixes": ["Re-installed GTM container.", "Implemented server-side tracking.", "Fixed CAPI event mapping."]},
        {"type": "CPA Spike", "channel": "meta_ads", "roots": ["Audience fatigue from overexposure.", "Creative approval delays caused delivery gaps.", "Lookalike seed audience became stale."], "fixes": ["Expanded targeting to new segments.", "Built creative approval buffer.", "Refreshed lookalike seed."]},
        
        # TikTok
        {"type": "Engagement Drop", "channel": "tiktok_ads", "roots": ["Algorithm change penalized branded content.", "Competitor viral trend overshadowed ads.", "Creative didn't match platform native style."], "fixes": ["Adopted more native creative format.", "Pivoted messaging to trend.", "Partnered with TikTok creators."]},
        
        # LinkedIn
        {"type": "Low CTR", "channel": "linkedin_ads", "roots": ["B2B audience saturated.", "Ad copy too promotional.", "Wrong job title targeting."], "fixes": ["Expanded to adjacent job functions.", "A/B tested thought leadership copy.", "Refined title targeting."]},
        
        # Programmatic
        {"type": "Bot Traffic", "channel": "programmatic", "roots": ["Low-quality inventory sources.", "Brand safety filter gaps.", "Made-for-advertising sites in rotation."], "fixes": ["Implemented ads.txt verification.", "Added IVT filtering.", "Created inclusion list of quality publishers."]},
        
        # Affiliate
        {"type": "ROAS Drop", "channel": "affiliate", "roots": ["Coupon sites cannibalizing organic.", "Affiliate promoted competitor as alternative.", "Attribution window too long."], "fixes": ["Reduced affiliate commission on brand terms.", "Terminated bad actor affiliate.", "Shortened attribution to 7 days."]},
        
        # TV
        {"type": "Reach Drop", "channel": "tv", "roots": ["Primetime spots preempted by breaking news.", "Upfront deal under-delivered GRPs.", "Nielsen panel issues in key DMAs."], "fixes": ["Received make-goods from network.", "Negotiated additional spots.", "Supplemented with CTV."]},
        {"type": "Low Lift", "channel": "tv", "roots": ["Creative message didn't resonate.", "Wrong daypart mix.", "Competitive clutter during sports event."], "fixes": ["Revised creative brief.", "Shifted to early fringe.", "Avoided event adjacency."]},
        
        # Podcast
        {"type": "Attribution Gap", "channel": "podcast", "roots": ["Promo codes not being used.", "Host read quality inconsistent.", "Download fraud from bots."], "fixes": ["Implemented vanity URLs.", "Provided host talking points.", "Switched to verified podcast networks."]},
        
        # Radio
        {"type": "Response Drop", "channel": "radio", "roots": ["Format change on key station.", "Drive time shifted due to WFH.", "Streaming audio cannibalizing terrestrial."], "fixes": ["Moved budget to new format leader.", "Added midday flights.", "Balanced with Spotify/Pandora."]},
        
        # Direct Mail
        {"type": "Response Rate Drop", "channel": "direct_mail", "roots": ["USPS delivery delays.", "List quality degraded.", "Envelope design didn't stand out."], "fixes": ["Added extra lead time.", "Refreshed list with recent movers.", "Tested dimensional mail."]},
        
        # OOH
        {"type": "Low Visibility", "channel": "ooh", "roots": ["Construction blocked billboard.", "Traffic pattern changed.", "Weather damage to unit."], "fixes": ["Got credit from vendor.", "Moved to new location.", "Requested maintenance."]},
        
        # Events
        {"type": "Low Attendance", "channel": "events", "roots": ["Competing industry event same week.", "Registration page had bugs.", "Email invites went to spam."], "fixes": ["Rescheduled future events.", "Fixed registration flow.", "Switched ESP provider."]},
        
        # Fraud scenarios
        {"type": "Fraud Alert", "channel": "influencer_campaigns", "roots": ["Creator bought fake followers.", "Engagement rate 0.01% despite 1M followers.", "Comments were generic bot spam."], "fixes": ["Terminated contract for breach of authenticity.", "Clawed back payment.", "Added vetting process."]},
    ]
    
    incidents = []
    total_days = (END_DATE - START_DATE).days
    
    # Generate 150 incidents for richer RAG
    for i in range(150):
        t = random.choice(templates)
        days_offset = random.randint(0, total_days)
        date = START_DATE + timedelta(days=days_offset)
        
        severity = random.choices(
            ["critical", "high", "medium", "low"],
            weights=[0.1, 0.3, 0.4, 0.2]
        )[0]
        
        incidents.append({
            "incident_id": f"INC-{date.year}-{i+100}",
            "date": date.strftime("%Y-%m-%d"),
            "channel": t["channel"],
            "anomaly_type": t["type"],
            "severity": severity,
            "root_cause": random.choice(t["roots"]),
            "resolution": random.choice(t["fixes"]),
            "similarity_score": round(random.uniform(0.65, 0.98), 2)
        })
    return pd.DataFrame(incidents)

print("\n📜 Generating RAG Post-Mortems...")
rag_df = generate_rag_history()
rag_df.to_csv(POST_MORTEMS_DIR / "incidents.csv", index=False)
print(f"  ✓ incidents: {len(rag_df)} rows")


# ============================================================================
# 4. COMPETITOR INTELLIGENCE (Now varied per channel!)
# ============================================================================

def generate_competitor_intel():
    """
    Generate competitor activity signals for ALL channels.
    Each channel has different competitor landscape and activity patterns.
    """
    data = []
    
    # Competitor profiles per channel
    competitor_config = {
        "google_search": {
            "competitors": ["BrandX", "CompetitorCo", "RivalBrand"],
            "activity_types": ["aggressive_bidding", "new_campaign", "brand_conquest"],
            "frequency": 0.15,  # 15% of days have activity
        },
        "google_pmax": {
            "competitors": ["BrandX", "DirectCompete"],
            "activity_types": ["budget_increase", "new_asset_groups"],
            "frequency": 0.10,
        },
        "google_display": {
            "competitors": ["DisplayKing", "BrandX"],
            "activity_types": ["retargeting_push", "audience_expansion"],
            "frequency": 0.08,
        },
        "google_youtube": {
            "competitors": ["VideoFirst", "BrandX", "StreamCo"],
            "activity_types": ["pre_roll_blitz", "influencer_collab", "brand_channel_launch"],
            "frequency": 0.12,
        },
        "meta_ads": {
            "competitors": ["SocialNative", "BrandX", "D2C_Rival"],
            "activity_types": ["lookalike_expansion", "creative_refresh", "promo_campaign"],
            "frequency": 0.18,
        },
        "tiktok_ads": {
            "competitors": ["TrendSetters", "GenZ_Brand", "ViralCo"],
            "activity_types": ["hashtag_challenge", "creator_partnership", "spark_ads_push"],
            "frequency": 0.20,
        },
        "linkedin_ads": {
            "competitors": ["B2B_Leader", "EnterpriseCo"],
            "activity_types": ["thought_leadership", "inmail_campaign", "event_promotion"],
            "frequency": 0.06,
        },
        "programmatic": {
            "competitors": ["AdTechGiant", "MediaBuyer"],
            "activity_types": ["inventory_grab", "deal_id_exclusive"],
            "frequency": 0.07,
        },
        "affiliate": {
            "competitors": ["CouponKing", "DealSite"],
            "activity_types": ["commission_increase", "exclusive_deal"],
            "frequency": 0.10,
        },
        "tv": {
            "competitors": ["NationalBrand", "BigSpender", "LegacyCo"],
            "activity_types": ["upfront_commitment", "super_bowl_ad", "primetime_takeover"],
            "frequency": 0.05,
        },
        "podcast": {
            "competitors": ["AudioFirst", "PodcastPro"],
            "activity_types": ["host_endorsement", "exclusive_sponsorship"],
            "frequency": 0.08,
        },
        "radio": {
            "competitors": ["LocalHero", "NationalBrand"],
            "activity_types": ["drive_time_blitz", "format_takeover"],
            "frequency": 0.06,
        },
        "direct_mail": {
            "competitors": ["CatalogKing", "MailOrder"],
            "activity_types": ["postage_increase", "list_acquisition"],
            "frequency": 0.04,
        },
        "ooh": {
            "competitors": ["BillboardBoss", "StreetLevel"],
            "activity_types": ["prime_location_grab", "digital_ooh_expansion"],
            "frequency": 0.05,
        },
        "events": {
            "competitors": ["EventPro", "TradeshowKing"],
            "activity_types": ["booth_upgrade", "keynote_sponsorship", "networking_event"],
            "frequency": 0.03,
        },
    }
    
    # Impact descriptions by activity type
    impact_details = {
        "aggressive_bidding": ["Impression share lost increased by {pct}%", "CPCs up {pct}% in brand auctions", "Position dropped from 1 to {pos}"],
        "new_campaign": ["New campaign launched targeting our audience", "Estimated spend ${spend}K/month", "Bidding on our brand terms"],
        "brand_conquest": ["Direct brand term bidding detected", "Ad copy mentions us by name", "Landing page compares to us"],
        "budget_increase": ["Estimated {pct}% budget increase", "More frequent ad serving observed", "Expanded geo targeting"],
        "new_asset_groups": ["Fresh creative detected", "New product showcase", "Video assets added"],
        "retargeting_push": ["Aggressive remarketing observed", "Following our site visitors", "Dynamic product ads increased"],
        "audience_expansion": ["New audience segments targeted", "Lookalikes of our customers", "Interest expansion detected"],
        "pre_roll_blitz": ["Heavy pre-roll presence", "Bumper ad saturation", "Targeting our video viewers"],
        "influencer_collab": ["Partnered with {creator}", "Sponsored content campaign", "Brand ambassador announced"],
        "brand_channel_launch": ["New YouTube channel launched", "Content series started", "Subscriber push campaign"],
        "lookalike_expansion": ["Expanded lookalike targeting", "New custom audiences", "Broader reach campaign"],
        "creative_refresh": ["All new ad creative", "New brand messaging", "Updated visual identity"],
        "promo_campaign": ["Major sale announced", "{pct}% off promotion", "Limited time offer running"],
        "hashtag_challenge": ["Branded hashtag launched", "Challenge going viral", "UGC campaign active"],
        "creator_partnership": ["Signed top creator {creator}", "Exclusive content deal", "Multi-post campaign"],
        "spark_ads_push": ["Boosting organic content", "Spark ads detected", "Native-style promotion"],
        "thought_leadership": ["Whitepaper promotion", "Executive visibility campaign", "Industry report sponsored"],
        "inmail_campaign": ["InMail campaign to our audience", "Direct outreach detected", "Decision-maker targeting"],
        "event_promotion": ["Event sponsorship announced", "Conference presence", "Webinar campaign"],
        "inventory_grab": ["Bought up premium inventory", "PMPs secured", "Exclusive deal detected"],
        "deal_id_exclusive": ["Locked in deal IDs", "Publisher exclusives", "Premium placement secured"],
        "commission_increase": ["Raised affiliate commissions {pct}%", "Bonus structure improved", "Higher payouts offered"],
        "exclusive_deal": ["Exclusive affiliate partnership", "Top publisher locked", "Network deal signed"],
        "upfront_commitment": ["Major upfront buy announced", "Secured primetime", "${spend}M commitment"],
        "super_bowl_ad": ["Super Bowl spot purchased", "Major event presence", "High-profile placement"],
        "primetime_takeover": ["Primetime roadblock", "Category exclusive", "Heavy rotation secured"],
        "host_endorsement": ["Signed podcast host", "Personal endorsement", "Long-term deal"],
        "exclusive_sponsorship": ["Exclusive show sponsor", "Category lockout", "Season-long deal"],
        "drive_time_blitz": ["Heavy drive time presence", "Morning show takeover", "Frequency increased"],
        "format_takeover": ["Bought out format", "Station exclusive", "Daypart domination"],
        "postage_increase": ["Increased mail frequency", "Larger format pieces", "More personalization"],
        "list_acquisition": ["Acquired new mailing lists", "Database expansion", "New segments targeted"],
        "prime_location_grab": ["Secured prime locations", "Billboard exclusive", "High-traffic spots"],
        "digital_ooh_expansion": ["DOOH campaign launched", "Dynamic creative deployed", "Programmatic OOH"],
        "booth_upgrade": ["Larger booth secured", "Better floor position", "Premium placement"],
        "keynote_sponsorship": ["Keynote sponsor", "Main stage presence", "Executive speaking slot"],
        "networking_event": ["VIP event planned", "Executive dinner", "Private reception"],
    }
    
    for date in DATES:
        for channel, config in competitor_config.items():
            # Determine if there's activity on this day
            if random.random() < config["frequency"]:
                competitor = random.choice(config["competitors"])
                activity = random.choice(config["activity_types"])
                
                # Generate contextual details
                detail_templates = impact_details.get(activity, ["Competitor activity detected"])
                detail = random.choice(detail_templates).format(
                    pct=random.randint(10, 50),
                    spend=random.randint(50, 500),
                    pos=random.randint(2, 4),
                    creator=random.choice(["@TopCreator", "@ViralStar", "@Influencer123"])
                )
                
                impact = random.choice(["high", "medium", "low"])
                
                data.append({
                    "date": date,
                    "competitor": competitor,
                    "channel": channel,
                    "activity_type": activity,
                    "impact_level": impact,
                    "details": detail
                })
    
    return pd.DataFrame(data)


# ============================================================================
# 5. MARKET TRENDS
# ============================================================================

def generate_market_trends():
    """Generate Google Trends style market interest data."""
    data = []
    for i, date in enumerate(DATES):
        year_trend = (i / len(DATES)) * 20
        seasonality = 15 * np.sin(i / 30)  # Monthly cycle
        weekly = 5 * np.sin(i / 7 * 2 * np.pi)  # Weekly cycle
        interest = 45 + year_trend + seasonality + weekly + np.random.normal(0, 3)
        data.append({
            "date": date, 
            "topic": "Donation", 
            "interest_score": round(max(10, min(100, interest)), 1)
        })
    return pd.DataFrame(data)


# ============================================================================
# 6. MMM SATURATION DATA (Now with meaningful variation!)
# ============================================================================

def generate_mmm_guardrails_history():
    """
    Generate daily MMM saturation data with VARIED recommendations per channel.
    
    Channel categories:
    - SCALE: Room to grow (marginal ROAS > 1.5)
    - MAINTAIN: Near saturation (marginal ROAS 0.8-1.5)
    - REDUCE: Over-saturated (marginal ROAS < 0.8)
    """
    data = []
    
    # Configuration with intentional variety
    configs = {
        # SCALE candidates (high marginal ROAS)
        "google_search":   {"base_sat": 8000, "base_roas": 2.2, "trend": "stable", "category": "scale"},
        "meta_ads":        {"base_sat": 10000, "base_roas": 1.8, "trend": "improving", "category": "scale"},
        "podcast":         {"base_sat": 4000, "base_roas": 2.0, "trend": "stable", "category": "scale"},
        "affiliate":       {"base_sat": 5000, "base_roas": 2.8, "trend": "stable", "category": "scale"},
        
        # MAINTAIN candidates (moderate marginal ROAS)
        "google_pmax":     {"base_sat": 6500, "base_roas": 1.3, "trend": "declining", "category": "maintain"},
        "tiktok_ads":      {"base_sat": 3000, "base_roas": 1.2, "trend": "volatile", "category": "maintain"},
        "google_youtube":  {"base_sat": 6000, "base_roas": 1.1, "trend": "stable", "category": "maintain"},
        "tv":              {"base_sat": 15000, "base_roas": 1.0, "trend": "stable", "category": "maintain"},
        "events":          {"base_sat": 10000, "base_roas": 1.1, "trend": "stable", "category": "maintain"},
        "radio":           {"base_sat": 5000, "base_roas": 1.0, "trend": "declining", "category": "maintain"},
        
        # REDUCE/SATURATED candidates (low marginal ROAS)
        "google_display":  {"base_sat": 4000, "base_roas": 0.7, "trend": "declining", "category": "reduce"},
        "linkedin_ads":    {"base_sat": 2000, "base_roas": 0.6, "trend": "stable", "category": "reduce"},
        "ooh":             {"base_sat": 8000, "base_roas": 0.5, "trend": "declining", "category": "reduce"},
        "programmatic":    {"base_sat": 7000, "base_roas": 0.8, "trend": "volatile", "category": "maintain"},
        "direct_mail":     {"base_sat": 6000, "base_roas": 0.9, "trend": "declining", "category": "maintain"},
    }
    
    for i, date in enumerate(DATES):
        for channel, cfg in configs.items():
            # Add channel-specific time variation
            channel_seed = hash(channel) % 100
            
            # Trend effects
            if cfg["trend"] == "improving":
                trend_effect = (i / len(DATES)) * 0.3  # Gets better over time
            elif cfg["trend"] == "declining":
                trend_effect = -(i / len(DATES)) * 0.25  # Gets worse over time
            elif cfg["trend"] == "volatile":
                trend_effect = np.sin(i / 15 + channel_seed) * 0.3
            else:
                trend_effect = np.sin(i / 45 + channel_seed) * 0.1
            
            # Calculate marginal ROAS with variation
            base = cfg["base_roas"]
            noise = np.random.normal(0, 0.08)
            roas = base + trend_effect + noise
            roas = max(0.2, min(3.5, roas))  # Clamp to reasonable range
            
            # Determine recommendation based on actual marginal ROAS
            if roas >= 1.5:
                rec = "scale"
            elif roas >= 0.9:
                rec = "maintain"
            else:
                rec = "reduce"
            
            # Saturation point also varies slightly
            sat_variation = np.sin(i / 60 + channel_seed) * 0.15
            sat_point = int(cfg["base_sat"] * (1 + sat_variation))
            
            data.append({
                "date": date,
                "channel": channel,
                "saturation_point_daily": sat_point,
                "current_marginal_roas": round(roas, 2),
                "recommendation": rec
            })
    
    return pd.DataFrame(data)


# ============================================================================
# 7. MTA ATTRIBUTION DATA (Already varied, but enhanced)
# ============================================================================

def generate_mta_attribution_history():
    """
    Generate daily MTA vs Last Click comparison with meaningful channel differences.
    
    Patterns:
    - Search/Brand: Last-click overstates (mult < 1)
    - Display/Social/Video: MTA shows higher value (mult > 1)
    - Offline: Very undervalued by last-click (mult >> 1)
    """
    data = []
    
    channel_configs = {
        # Last-click OVERSTATES (conversion closers)
        "google_search":   {"base_lc": 3.8, "mult": 0.85, "pattern": "overvalued"},
        "affiliate":       {"base_lc": 4.5, "mult": 0.65, "pattern": "overvalued"},
        
        # Roughly ACCURATE
        "google_pmax":     {"base_lc": 2.8, "mult": 1.05, "pattern": "accurate"},
        "direct_mail":     {"base_lc": 1.6, "mult": 1.15, "pattern": "accurate"},
        
        # Last-click UNDERSTATES (awareness/assist channels)
        "google_display":  {"base_lc": 1.0, "mult": 1.8, "pattern": "undervalued"},
        "google_youtube":  {"base_lc": 0.5, "mult": 3.5, "pattern": "undervalued"},
        "meta_ads":        {"base_lc": 2.2, "mult": 1.4, "pattern": "undervalued"},
        "tiktok_ads":      {"base_lc": 1.5, "mult": 1.8, "pattern": "undervalued"},
        "linkedin_ads":    {"base_lc": 1.2, "mult": 1.5, "pattern": "undervalued"},
        "programmatic":    {"base_lc": 0.8, "mult": 2.2, "pattern": "undervalued"},
        
        # Offline - VERY undervalued by last-click
        "tv":              {"base_lc": 0.25, "mult": 5.0, "pattern": "undervalued"},
        "podcast":         {"base_lc": 0.6, "mult": 3.2, "pattern": "undervalued"},
        "radio":           {"base_lc": 0.35, "mult": 4.0, "pattern": "undervalued"},
        "ooh":             {"base_lc": 0.15, "mult": 6.0, "pattern": "undervalued"},
        "events":          {"base_lc": 0.8, "mult": 2.8, "pattern": "undervalued"},
    }
    
    for i, date in enumerate(DATES):
        for channel, cfg in channel_configs.items():
            # Add daily variation
            lc_noise = np.random.normal(0, cfg["base_lc"] * 0.12)
            last_click = max(0.1, cfg["base_lc"] + lc_noise)
            
            # MTA has its own variation
            mult_noise = np.random.normal(0, 0.1)
            actual_mult = cfg["mult"] + mult_noise
            mta_roas = max(0.1, last_click * actual_mult)
            
            # Assist ratio: portion of value from assists
            if actual_mult > 1:
                assist_ratio = round(1 - (1 / actual_mult), 2)
            else:
                assist_ratio = 0  # Overstated channels don't have assist ratio
            
            data.append({
                "date": date,
                "channel": channel,
                "last_click_roas": round(last_click, 2),
                "data_driven_roas": round(mta_roas, 2),
                "assist_ratio": max(0, assist_ratio)
            })
    
    return pd.DataFrame(data)


# ============================================================================
# GENERATE ALL TIER 3 & 4 DATA
# ============================================================================

print("\n🧠 Generating Market & Strategy Data...")

comp_df = generate_competitor_intel()
comp_df.to_csv(MOCK_CSV_DIR / "competitors.csv", index=False)
print(f"  ✓ competitors.csv: {len(comp_df)} rows across {comp_df['channel'].nunique()} channels")

trends_df = generate_market_trends()
trends_df.to_csv(MOCK_CSV_DIR / "market_trends.csv", index=False)
print(f"  ✓ market_trends.csv: {len(trends_df)} rows")

mmm_df = generate_mmm_guardrails_history()
mmm_df.to_csv(MOCK_CSV_DIR / "mmm_saturation.csv", index=False)
rec_counts = mmm_df.groupby('recommendation').size().to_dict()
print(f"  ✓ mmm_saturation.csv: {len(mmm_df)} rows")
print(f"    Recommendations: {rec_counts}")

mta_df = generate_mta_attribution_history()
mta_df.to_csv(MOCK_CSV_DIR / "mta_attribution.csv", index=False)
print(f"  ✓ mta_attribution.csv: {len(mta_df)} rows")

print("\n" + "="*60)
print("✅ Mock Data Generation Complete")
print(f"   Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
print(f"   Channels: {len(ALL_CHANNELS)}")
print("   Run 'make init-rag' to load post-mortems into Vector Store.")
print("="*60)


# ============================================================================
# CLI SUPPORT
# ============================================================================

def main():
    """Main entry point with CLI support."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate mock marketing data for Project Expedition"
    )
    parser.add_argument(
        "--end-date", 
        type=str, 
        help="End date for data generation (YYYY-MM-DD). Default: today"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days of data to generate. Default: 90"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility. Default: 42"
    )
    
    args = parser.parse_args()
    
    np.random.seed(args.seed)
    random.seed(args.seed)
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            print(f"📅 Using custom end date: {args.end_date}")
        except ValueError:
            print(f"⚠️ Invalid date format: {args.end_date}. Using today's date.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        main()