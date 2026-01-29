#!/usr/bin/env python3
"""
Generate high-fidelity mock marketing data for Project Expedition.
Includes "Needle in a Haystack" anomalies and a rich RAG history.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import random

# Configuration
np.random.seed(42)  # For reproducibility
MOCK_CSV_DIR = Path("data/mock_csv")
POST_MORTEMS_DIR = Path("data/post_mortems")
MOCK_CSV_DIR.mkdir(parents=True, exist_ok=True)
POST_MORTEMS_DIR.mkdir(parents=True, exist_ok=True)

# 90 Days of Data
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=90)
DATES = pd.date_range(start=START_DATE, end=END_DATE, freq="D")


def add_noise(base: float, volatility: float = 0.1) -> float:
    """Add realistic gaussian noise."""
    return max(0, base * (1 + np.random.normal(0, volatility)))


def generate_channel_data(
    channel: str,
    config: dict,
    anomalies: list = None
) -> pd.DataFrame:
    """Generate daily performance data with injected anomalies."""
    data = []
    
    base_spend = config["base_spend"]
    base_cpa = config["base_cpa"]
    base_roas = config["base_roas"]
    trend = config.get("trend", 0.0)
    weekend_factor = config.get("weekend_effect", 0.8)
    
    total_days = len(DATES)

    for i, date in enumerate(DATES):
        # 1. Base Metrics
        daily_trend = (1 + trend) ** i
        is_weekend = date.weekday() >= 5
        seasonality = weekend_factor if is_weekend else 1.0
        
        spend = add_noise(base_spend * daily_trend * seasonality, 0.15)
        cpa = add_noise(base_cpa, 0.1)
        roas = add_noise(base_roas, 0.1)
        
        # 2. Inject Anomalies (The "Needles")
        # We calculate "days from end" using the index, which is safer than date math
        days_from_end = total_days - 1 - i
        
        if anomalies:
            for anomaly in anomalies:
                # FIX: Ensure we check the range correctly (0 <= days <= 3)
                if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
                    spend *= anomaly.get("spend_mult", 1.0)
                    cpa *= anomaly.get("cpa_mult", 1.0)
                    roas *= anomaly.get("roas_mult", 1.0)

        # 3. Derive Dependent Metrics
        conversions = int(spend / cpa) if cpa > 0 else 0
        
        # Apply conversion anomaly (e.g., Pixel Death)
        if anomalies:
            for anomaly in anomalies:
                if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
                    conversions = int(conversions * anomaly.get("conv_mult", 1.0))

        revenue = spend * roas
        cpm = add_noise(15, 0.2)
        impressions = int(spend / cpm * 1000)
        ctr = add_noise(0.015, 0.1)
        clicks = int(impressions * ctr)
        
        # Recalculate realized metrics
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

# ============================================================================
# 1. DEFINING THE SCENARIOS
# ============================================================================

ANOMALIES = [
    {
        # SCENARIO 1: The "Obvious" Spike
        # Google PMax goes crazy spending budget on low-quality YouTube placements
        # Last 3 days (Days 3, 2, 1, 0 from end)
        "channel": "google_pmax",
        "start_day": 3, "end_day": 0,  
        "spend_mult": 3.0,  # CRITICAL: 3x Spend
        "roas_mult": 0.3,   # CRITICAL: 70% Drop in ROAS
        "description": "PMax Spend Spike"
    },
    {
        # SCENARIO 2: The "Silent Killer" (Broken Pixel)
        # Meta Ads spend is normal, but Conversions drop to near zero.
        # Last 2 days
        "channel": "meta_ads",
        "start_day": 2, "end_day": 0,
        "spend_mult": 1.0,  # Normal spend
        "conv_mult": 0.05,  # CRITICAL: 95% Drop in Conversions
        "description": "Pixel Tracking Failure"
    }
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

print("📊 Generating Paid Media & Offline Mock Data...")
for channel, config in CHANNELS_CONFIG.items():
    df = generate_channel_data(channel, config, ANOMALIES)
    output_path = MOCK_CSV_DIR / f"{channel}.csv"
    df.to_csv(output_path, index=False)
    print(f"  ✓ {channel}: {len(df)} rows")


# ============================================================================
# 2. INFLUENCER DATA (With Fraud Scenario)
# ============================================================================

def generate_influencer_data():
    creators = [
        # The Fraudster
        {"id": "INF_999", "name": "ViralViper", "platform": "tiktok", "real": False},
        # The Good Ones
        {"id": "INF_001", "name": "TechGuru", "platform": "youtube", "real": True},
        {"id": "INF_002", "name": "FitLife", "platform": "instagram", "real": True},
        {"id": "INF_003", "name": "MomHacks", "platform": "instagram", "real": True},
        {"id": "INF_004", "name": "GamerX", "platform": "twitch", "real": True},
    ]
    
    data = []
    for creator in creators:
        # Create 3-4 posts per creator
        for i in range(4):
            # FIX: Ensure the Fraudster has a post TODAY (0 days ago) so it's a "Current" anomaly
            if not creator["real"] and i == 0:
                date = END_DATE
            else:
                date = END_DATE - timedelta(days=random.randint(1, 30))
            
            if creator["real"]:
                # Healthy metrics
                spend = random.randint(2000, 8000)
                impressions = spend * random.randint(20, 50)
                eng_rate = random.uniform(0.03, 0.08)
                conv_rate = random.uniform(0.01, 0.03)
            else:
                # SCENARIO 3: Fraud (High Vol, Low Eng/Conv)
                spend = 15000  # High fees
                impressions = 500000  # Massive reach (bots)
                eng_rate = 0.001  # Tiny engagement
                conv_rate = 0.0001 # Zero sales
            
            engagements = int(impressions * eng_rate)
            clicks = int(engagements * 0.2)
            conversions = int(clicks * conv_rate)
            
            data.append({
                "campaign_id": f"CAMP_{random.randint(100,999)}",
                "creator_id": creator["id"],
                "creator_name": creator["name"],
                "platform": creator["platform"],
                "post_date": date,
                "contract_value": spend,
                "impressions": impressions,
                "engagements": engagements,
                "clicks": clicks,
                "conversions": conversions,
                "engagement_rate": round(eng_rate, 4),
                "earned_media_value": spend * (0.2 if not creator["real"] else 2.5)
            })
            
    return pd.DataFrame(data)

print("\n👥 Generating Influencer Data...")
inf_df = generate_influencer_data()
inf_df.to_csv(MOCK_CSV_DIR / "influencer_campaigns.csv", index=False)
print(f"  ✓ influencer_campaigns: {len(inf_df)} rows")


# ============================================================================
# 3. RAG HISTORY (Expanded to 30 incidents)
# ============================================================================

def generate_rag_history():
    # Templates with variations to ensure unique embeddings
    templates = [
        # --- ORIGINAL DIGITAL CHANNELS ---
        {
            "type": "CPA Spike", 
            "channel": "google_search",
            "roots": [
                "Competitor 'BrandX' aggressive bidding on brand terms.",
                "New market entrant bidding heavily on our exact match keywords.",
                "Auction insights show 40% overlap increase with top competitor.",
                "Q4 seasonal competition drove up CPCs by 35%."
            ],
            "fixes": [
                "Increased brand CPC bids by 20% and filed trademark complaint.",
                "Launched defensive brand campaign with aggressive Top IS target.",
                "Adjusted target CPA to defend impression share against BrandX.",
                "Temporarily increased budget caps to capture holiday demand."
            ]
        },
        {
            "type": "Zero Conversions", 
            "channel": "meta_ads",
            "roots": [
                "Tracking pixel fell off checkout page after deployment #1204.",
                "GTM container rollback accidentally removed purchase event.",
                "Server-side API token expired, causing event loss.",
                "iOS update caused 48-hour reporting delay on conversions."
            ],
            "fixes": [
                "Re-installed GTM container and added automated pixel monitoring.",
                "Restored previous GTM version and verified checkout firing.",
                "Generated new CAPI token and updated server config.",
                "Switched to 7-day click attribution window for reporting."
            ]
        },
        {
            "type": "Spend Surge", 
            "channel": "google_pmax",
            "roots": [
                "PMax auto-expanded to low quality Display inventory.",
                "Algorithm aggressively targeted mobile app placements.",
                "Uncapped budget allowed PMax to spend 300% of daily average.",
                "Bot traffic spike on unknown placements drove up spend."
            ],
            "fixes": [
                "Added placement exclusions and tightened location settings.",
                "Excluded mobile app categories and gaming sites.",
                "Implemented strict daily spend caps and tROAS targets.",
                "Added negative IP lists and enabled click fraud protection."
            ]
        },
        {
            "type": "Low CTR", 
            "channel": "meta_ads",
            "roots": [
                "Creative fatigue. Ad frequency exceeded 8.0.",
                "Audience saturation in 'Lookalike 1%' audience.",
                "Headline 'Free Shipping' no longer resonating with segment.",
                "Broken video asset rendering as black screen."
            ],
            "fixes": [
                "Refreshed creative assets and implemented frequency capping.",
                "Expanded audience to 'Lookalike 5%' and broad interest.",
                "Tested new '20% Off' hooks and headlines.",
                "Re-uploaded video assets and cleared cache."
            ]
        },
        
        # --- NEW CHANNELS (TV, AFFILIATE, PODCAST, LINKEDIN) ---
        {
            "type": "High CPL",
            "channel": "linkedin_ads",
            "roots": [
                "Audience size too small (<50k), leading to high frequency.",
                "Job title targeting too broad, capturing entry-level roles.",
                "LinkedIn Audience Network delivering low-quality clicks.",
            ],
            "fixes": [
                "Expanded audience using lookalikes of customer list.",
                "Added seniority exclusions to target decision makers only.",
                "Disabled Audience Network to focus on feed placements.",
            ]
        },
        {
            "type": "Conversion Drop",
            "channel": "affiliate",
            "roots": [
                "Top affiliate partner removed our link from their homepage.",
                "Coupon code leakage to discount sites lowered AOV.",
                "Fraudulent leads detected from new sub-affiliate network.",
            ],
            "fixes": [
                "Renegotiated placement with top partner.",
                "Invalidated leaked codes and issued exclusive links.",
                "Voided commissions for fraudulent leads and blocked sub-ID.",
            ]
        },
        {
            "type": "Reach Drop",
            "channel": "tv",
            "roots": [
                "Primetime spots preempted by breaking news coverage.",
                "Frequency cap issues on Connected TV (CTV) inventory.",
                "Measurement lag from Nielsen reporting caused data gap.",
            ],
            "fixes": [
                "Received make-goods for preempted spots next week.",
                "Applied strict frequency capping across CTV publishers.",
                "Used spot logs for interim reporting while awaiting Nielsen.",
            ]
        },
        {
            "type": "Low Engagement",
            "channel": "podcast",
            "roots": [
                "Host read script was truncated during recording.",
                "Promo code mentioned on air didn't match backend.",
                "Episode released on holiday weekend with low downloads.",
            ],
            "fixes": [
                "Requested re-read/make-good for next episode.",
                "Created vanity URL redirect to fix promo code error.",
                "Shifted future ad buys to mid-week release schedules.",
            ]
        },
        {
            "type": "Fraud Alert",
            "channel": "influencer",
            "roots": [
                "Creator engagement rate 0.01% despite 1M followers.",
                "Comment section filled with generic bot spam.",
                "Sudden spike in followers from non-target geo (click farm).",
            ],
            "fixes": [
                "Terminated contract for breach of authenticity clause.",
                "Blacklisted creator from future campaigns.",
                "Implemented vetting tool to audit audience quality pre-hire.",
            ]
        }
    ]
    
    incidents = []
    start_hist = datetime.now() - timedelta(days=365)
    
    for i in range(40): # Increased to 40 to cover new channels
        template = random.choice(templates)
        date = start_hist + timedelta(days=random.randint(1, 360))
        
        # Pick random variations
        root = random.choice(template["roots"])
        fix = random.choice(template["fixes"])
        
        incidents.append({
            "incident_id": f"INC-{date.year}-{i+100}",
            "date": date.strftime("%Y-%m-%d"),
            "channel": template["channel"],
            "anomaly_type": template["type"],
            "severity": random.choice(["high", "medium", "critical"]),
            "root_cause": root,
            "resolution": fix,
            "similarity_score": round(random.uniform(0.7, 0.95), 2) # Mock score for raw file
        })
        
    return pd.DataFrame(incidents)

print("\n📜 Generating 40+ RAG Post-Mortems...")
rag_df = generate_rag_history()
rag_df.to_csv(POST_MORTEMS_DIR / "incidents.csv", index=False)
print(f"  ✓ incidents: {len(rag_df)} rows")

print("\n" + "="*60)
print("✅ Mock Data Generation Complete")
print("   Run 'make init-rag' to load this into the Vector Store.")
print("="*60)