#!/usr/bin/env python3
"""
Generate 6 years (Jan 2020 – Mar 2026) of GoFundMe marketing mock data.

Covers:
  - COVID lockdown: events/OOH collapse + digital donation surge (Mar-Jun 2020)
  - BLM fundraising wave (May-Jul 2020): CPA drops, conversion surge
  - Delta/Omicron waves (Aug-Nov 2021, Jan 2022): events partial shutdown
  - Ukraine war fundraising (Feb-Apr 2022): cross-channel donation surge
  - Turkey earthquake (Feb 2023): short acute spike
  - Maui fires (Aug 2023): regional spike
  - Gaza / humanitarian (Oct 2023): broad donation surge
  - US election cycles (Nov 2020, Nov 2022, Nov 2024): digital spend competition
  - Giving Tuesday every year (biggest single-day fundraising event)
  - Q4 holiday giving season (Oct-Dec each year)
  - Long-term platform growth trend (GoFundMe grew ~2x users 2020-2026)
  - 8 "current fire" anomaly scenarios injected at the end of the time series
  - 200+ RAG post-mortem incidents spanning 2020-2026
  - Full MMM saturation, MTA attribution, competitor intel, market trends
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import random

# ============================================================================
# Configuration
# ============================================================================

np.random.seed(42)
random.seed(42)

MOCK_CSV_DIR = Path("data/mock_csv")
POST_MORTEMS_DIR = Path("data/post_mortems")
MOCK_CSV_DIR.mkdir(parents=True, exist_ok=True)
POST_MORTEMS_DIR.mkdir(parents=True, exist_ok=True)

END_DATE = datetime(2026, 3, 5)
START_DATE = datetime(2020, 1, 1)
DATES = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
TOTAL_DAYS = len(DATES)


def add_noise(base: float, volatility: float = 0.1) -> float:
    return max(0, base * (1 + np.random.normal(0, volatility)))


# ============================================================================
# Macro Event Definitions
# GoFundMe-specific: humanitarian crises, elections, COVID, giving seasons
# Each event overrides channel multipliers for spend/cpa/roas/conv
# ============================================================================

MACRO_EVENTS = [
    # --- COVID lockdown: offline collapses, digital donation surge ---
    {
        "name": "COVID lockdown",
        "start": datetime(2020, 3, 15),
        "end": datetime(2020, 6, 30),
        "channels": {
            "events":        {"spend_mult": 0.02, "conv_mult": 0.01},   # no in-person events
            "ooh":           {"spend_mult": 0.08, "conv_mult": 0.05},   # nobody outside
            "direct_mail":   {"spend_mult": 0.5,  "conv_mult": 0.3},    # postal delays
            "radio":         {"spend_mult": 0.6,  "conv_mult": 0.5},    # commuters gone
            "tv":            {"spend_mult": 1.3,  "cpa_mult": 0.6},     # everyone home watching
            "google_search": {"spend_mult": 1.6,  "cpa_mult": 0.45},    # donation searches surge
            "meta_ads":      {"spend_mult": 1.4,  "cpa_mult": 0.5},
            "podcast":       {"spend_mult": 1.2,  "cpa_mult": 0.7},     # home listening spike
            "programmatic":  {"spend_mult": 0.7,  "cpa_mult": 0.8},
            "google_display":{"spend_mult": 0.8,  "cpa_mult": 0.9},
        },
    },
    # --- Events slowly returning, some caution ---
    {
        "name": "COVID partial recovery",
        "start": datetime(2020, 7, 1),
        "end": datetime(2020, 12, 31),
        "channels": {
            "events": {"spend_mult": 0.2, "conv_mult": 0.15},
            "ooh":    {"spend_mult": 0.4, "conv_mult": 0.35},
        },
    },
    # --- BLM / George Floyd: massive organic donation surge ---
    {
        "name": "BLM fundraising wave",
        "start": datetime(2020, 5, 25),
        "end": datetime(2020, 7, 20),
        "channels": {
            "meta_ads":       {"cpa_mult": 0.35, "roas_mult": 2.2},     # viral sharing
            "google_search":  {"cpa_mult": 0.4,  "roas_mult": 2.0},
            "google_youtube": {"cpa_mult": 0.5,  "roas_mult": 1.7},
            "tiktok_ads":     {"cpa_mult": 0.45, "roas_mult": 1.9},
        },
    },
    # --- US Election Nov 2020: digital CPMs spike due to political ad competition ---
    {
        "name": "US Election 2020",
        "start": datetime(2020, 10, 1),
        "end": datetime(2020, 11, 10),
        "channels": {
            "meta_ads":       {"cpa_mult": 1.6,  "spend_mult": 1.3},
            "google_search":  {"cpa_mult": 1.4,  "spend_mult": 1.2},
            "programmatic":   {"cpa_mult": 1.5,  "spend_mult": 1.25},
            "tv":             {"cpa_mult": 1.7,  "spend_mult": 1.4},
        },
    },
    # --- Delta wave: events and OOH partially closed again ---
    {
        "name": "Delta wave",
        "start": datetime(2021, 8, 1),
        "end": datetime(2021, 11, 30),
        "channels": {
            "events": {"spend_mult": 0.3, "conv_mult": 0.25},
            "ooh":    {"spend_mult": 0.6, "conv_mult": 0.5},
        },
    },
    # --- Omicron wave (milder but still affects gatherings) ---
    {
        "name": "Omicron wave",
        "start": datetime(2021, 12, 15),
        "end": datetime(2022, 2, 28),
        "channels": {
            "events": {"spend_mult": 0.25, "conv_mult": 0.2},
            "ooh":    {"spend_mult": 0.65, "conv_mult": 0.55},
        },
    },
    # --- Ukraine war: massive cross-channel humanitarian donation surge ---
    {
        "name": "Ukraine war fundraising",
        "start": datetime(2022, 2, 24),
        "end": datetime(2022, 5, 31),
        "channels": {
            "google_search":  {"cpa_mult": 0.3,  "roas_mult": 2.8},
            "meta_ads":       {"cpa_mult": 0.35, "roas_mult": 2.5},
            "tv":             {"cpa_mult": 0.5,  "roas_mult": 1.8},
            "google_youtube": {"cpa_mult": 0.45, "roas_mult": 2.0},
            "programmatic":   {"cpa_mult": 0.55, "roas_mult": 1.6},
        },
    },
    # --- US Election 2022 midterms: digital CPM pressure ---
    {
        "name": "US Midterms 2022",
        "start": datetime(2022, 10, 1),
        "end": datetime(2022, 11, 15),
        "channels": {
            "meta_ads":      {"cpa_mult": 1.5, "spend_mult": 1.2},
            "google_search": {"cpa_mult": 1.3, "spend_mult": 1.15},
            "tv":            {"cpa_mult": 1.6, "spend_mult": 1.3},
        },
    },
    # --- Macro: rising interest rates / tighter consumer wallets in 2022 ---
    {
        "name": "Rate hike cycle 2022",
        "start": datetime(2022, 6, 1),
        "end": datetime(2023, 3, 31),
        "channels": {
            "affiliate":     {"cpa_mult": 1.2},
            "direct_mail":   {"cpa_mult": 1.15},
            "linkedin_ads":  {"cpa_mult": 1.1},
        },
    },
    # --- Turkey/Syria earthquake: short acute humanitarian spike ---
    {
        "name": "Turkey earthquake",
        "start": datetime(2023, 2, 6),
        "end": datetime(2023, 3, 15),
        "channels": {
            "google_search":  {"cpa_mult": 0.35, "roas_mult": 2.5},
            "meta_ads":       {"cpa_mult": 0.4,  "roas_mult": 2.2},
            "tv":             {"cpa_mult": 0.55, "roas_mult": 1.7},
        },
    },
    # --- Maui fires Aug 2023 ---
    {
        "name": "Maui fires",
        "start": datetime(2023, 8, 8),
        "end": datetime(2023, 9, 15),
        "channels": {
            "google_search": {"cpa_mult": 0.5, "roas_mult": 1.8},
            "meta_ads":      {"cpa_mult": 0.55, "roas_mult": 1.6},
        },
    },
    # --- Gaza / Middle East humanitarian crisis Oct 2023 ---
    {
        "name": "Gaza humanitarian crisis",
        "start": datetime(2023, 10, 7),
        "end": datetime(2023, 12, 31),
        "channels": {
            "google_search":  {"cpa_mult": 0.4,  "roas_mult": 2.3},
            "meta_ads":       {"cpa_mult": 0.45, "roas_mult": 2.0},
            "google_youtube": {"cpa_mult": 0.55, "roas_mult": 1.6},
            "tv":             {"cpa_mult": 0.6,  "roas_mult": 1.5},
        },
    },
    # --- US Election 2024: CPM pressure peaks ---
    {
        "name": "US Election 2024",
        "start": datetime(2024, 9, 1),
        "end": datetime(2024, 11, 10),
        "channels": {
            "meta_ads":      {"cpa_mult": 1.7, "spend_mult": 1.35},
            "google_search": {"cpa_mult": 1.5, "spend_mult": 1.25},
            "programmatic":  {"cpa_mult": 1.6, "spend_mult": 1.3},
            "tv":            {"cpa_mult": 1.9, "spend_mult": 1.5},
        },
    },
]


def get_giving_tuesday(year: int) -> datetime:
    """Return Giving Tuesday (first Tuesday after US Thanksgiving = 4th Thursday of November)."""
    # Find 4th Thursday of November
    nov1 = datetime(year, 11, 1)
    thursday_offset = (3 - nov1.weekday()) % 7  # Thursday = weekday 3
    first_thursday = nov1 + timedelta(days=thursday_offset)
    thanksgiving = first_thursday + timedelta(weeks=3)
    # Giving Tuesday = following Tuesday
    tuesday_offset = (1 - thanksgiving.weekday()) % 7
    if tuesday_offset == 0:
        tuesday_offset = 7
    return thanksgiving + timedelta(days=tuesday_offset)


GIVING_TUESDAYS = {yr: get_giving_tuesday(yr) for yr in range(2020, 2027)}


def get_day_multipliers(date: datetime, channel: str, day_index: int) -> dict:
    """
    Return (spend_mult, cpa_mult, roas_mult, conv_mult) for a given date.
    Combines: long-term growth trend, Q4 giving season, Giving Tuesday,
    macro events, and weekend effects.
    """
    spend_m = 1.0
    cpa_m   = 1.0
    roas_m  = 1.0

    # --- 1. Long-term platform growth trend (GoFundMe doubled users 2020-2026) ---
    years_in = day_index / 365.0
    growth = 1.0 + 0.12 * years_in  # ~12% per year compounding

    # --- 2. Annual Q4 giving season (Oct = +20%, Nov = +40%, Dec = +60%) ---
    month = date.month
    if month == 10:
        seasonal = 1.20
    elif month == 11:
        seasonal = 1.45
    elif month == 12:
        seasonal = 1.65
    elif month == 1:
        seasonal = 0.80  # post-holiday hangover
    elif month == 2:
        seasonal = 0.85
    else:
        seasonal = 1.0

    # --- 3. Giving Tuesday spike: conversions +300%, CPA drops 70% ---
    gt = GIVING_TUESDAYS.get(date.year)
    if gt and abs((date - gt).days) <= 1:
        cpa_m   *= 0.3
        roas_m  *= 3.5
        spend_m *= 1.6

    # --- 4. Macro events ---
    for event in MACRO_EVENTS:
        if event["start"] <= date <= event["end"]:
            ch_overrides = event["channels"].get(channel, {})
            spend_m *= ch_overrides.get("spend_mult", 1.0)
            cpa_m   *= ch_overrides.get("cpa_mult",   1.0)
            roas_m  *= ch_overrides.get("roas_mult",  1.0)

    # --- 5. Weekend effect (charity giving dips on weekends except crisis) ---
    if date.weekday() >= 5:  # Saturday / Sunday
        if channel in ("events",):
            spend_m *= 1.5  # events are on weekends
        elif channel in ("tv", "podcast", "radio"):
            spend_m *= 0.9
        else:
            spend_m *= 0.75

    return {
        "spend_m": spend_m * growth * seasonal,
        "cpa_m":   cpa_m,
        "roas_m":  roas_m,
    }


# ============================================================================
# 1. CHANNEL PERFORMANCE DATA
# ============================================================================

ANOMALIES = [
    # --- Current "fires" injected at end of time series ---
    {
        "channel": "google_pmax",
        "start_day": 3, "end_day": 0,
        "spend_mult": 3.0, "roas_mult": 0.3,
        "description": "PMax Spend Spike - algorithm expanded to low-quality YouTube placements",
    },
    {
        "channel": "meta_ads",
        "start_day": 2, "end_day": 0,
        "spend_mult": 1.0, "conv_mult": 0.05,
        "description": "Pixel Tracking Failure - 95% conversion drop after deployment",
    },
    {
        "channel": "google_search",
        "start_day": 4, "end_day": 0,
        "cpa_mult": 2.5, "spend_mult": 1.5,
        "description": "Competitor Bidding War - BrandX aggressive bidding on donation keywords",
    },
    {
        "channel": "tiktok_ads",
        "start_day": 5, "end_day": 0,
        "roas_mult": 0.35, "spend_mult": 1.0,
        "description": "Creative Fatigue - 65% ROAS decline, same creatives running 6 weeks",
    },
    {
        "channel": "linkedin_ads",
        "start_day": 3, "end_day": 0,
        "cpa_mult": 3.0, "spend_mult": 1.0,
        "description": "Audience Saturation - audience too narrow, frequency through the roof",
    },
    {
        "channel": "tv",
        "start_day": 2, "end_day": 0,
        "conv_mult": 0.2, "spend_mult": 1.0,
        "description": "TV Spots Preempted - 80% conversion drop, primetime preempted by breaking news",
    },
    {
        "channel": "programmatic",
        "start_day": 3, "end_day": 0,
        "spend_mult": 2.5, "conv_mult": 0.1,
        "description": "Bot Traffic / Click Fraud - DSP serving to non-human traffic",
    },
    {
        "channel": "affiliate",
        "start_day": 4, "end_day": 0,
        "conv_mult": 5.0, "spend_mult": 1.0,
        "description": "Coupon Leakage to Discount Sites - 5x conversion spike, mostly fraudulent",
    },
]

CHANNELS_CONFIG = {
    # Digital - Search & Shopping
    "google_search": {"base_spend": 5000,  "base_cpa": 45,  "base_roas": 3.2},
    "google_pmax":   {"base_spend": 4000,  "base_cpa": 35,  "base_roas": 4.0},
    "google_display":{"base_spend": 2000,  "base_cpa": 40,  "base_roas": 2.5},
    "google_youtube":{"base_spend": 3500,  "base_cpa": 45,  "base_roas": 2.8},
    # Social
    "meta_ads":      {"base_spend": 6000,  "base_cpa": 28,  "base_roas": 2.9},
    "tiktok_ads":    {"base_spend": 2500,  "base_cpa": 22,  "base_roas": 1.8},
    "linkedin_ads":  {"base_spend": 1500,  "base_cpa": 120, "base_roas": 1.2},
    # Programmatic & Affiliate
    "programmatic":  {"base_spend": 3000,  "base_cpa": 50,  "base_roas": 1.5},
    "affiliate":     {"base_spend": 1000,  "base_cpa": 15,  "base_roas": 5.0},
    # Offline
    "direct_mail":   {"base_spend": 5000,  "base_cpa": 60,  "base_roas": 1.5},
    "tv":            {"base_spend": 10000, "base_cpa": 150, "base_roas": 1.2},
    "radio":         {"base_spend": 3000,  "base_cpa": 80,  "base_roas": 1.4},
    "ooh":           {"base_spend": 4000,  "base_cpa": 200, "base_roas": 1.1},
    "events":        {"base_spend": 8000,  "base_cpa": 100, "base_roas": 1.3},
    "podcast":       {"base_spend": 2500,  "base_cpa": 55,  "base_roas": 2.2},
}


def generate_channel_data(channel: str, config: dict) -> pd.DataFrame:
    base_spend = config["base_spend"]
    base_cpa   = config["base_cpa"]
    base_roas  = config["base_roas"]
    data = []

    for i, date in enumerate(DATES):
        mults = get_day_multipliers(date, channel, i)

        spend = add_noise(base_spend * mults["spend_m"], 0.15)
        cpa   = add_noise(base_cpa   * mults["cpa_m"],   0.10)
        roas  = add_noise(base_roas  * mults["roas_m"],  0.10)

        # Inject current anomaly scenarios (last few days)
        days_from_end = TOTAL_DAYS - 1 - i
        conv_multiplier = 1.0
        for anomaly in ANOMALIES:
            if anomaly["channel"] == channel and anomaly["end_day"] <= days_from_end <= anomaly["start_day"]:
                spend *= anomaly.get("spend_mult", 1.0)
                cpa   *= anomaly.get("cpa_mult",   1.0)
                roas  *= anomaly.get("roas_mult",  1.0)
                conv_multiplier = anomaly.get("conv_mult", 1.0)

        conversions = max(0, int((spend / cpa) * conv_multiplier)) if cpa > 0 else 0
        revenue     = spend * roas
        cpm         = add_noise(15, 0.2)
        impressions = max(1, int(spend / cpm * 1000))
        ctr         = add_noise(0.015, 0.1)
        clicks      = max(0, int(impressions * ctr))

        data.append({
            "date":        date,
            "channel":     channel,
            "spend":       round(spend, 2),
            "impressions": impressions,
            "clicks":      clicks,
            "conversions": conversions,
            "revenue":     round(revenue, 2),
            "cpa":         round(spend / max(conversions, 1), 2),
            "roas":        round(revenue / max(spend, 1), 2),
            "ctr":         round(clicks / impressions, 4),
            "cpc":         round(spend / max(clicks, 1), 2),
        })

    return pd.DataFrame(data)


print("Generating channel data (2020-2026, ~2255 days per channel)...")
for channel, config in CHANNELS_CONFIG.items():
    df = generate_channel_data(channel, config)
    df.to_csv(MOCK_CSV_DIR / f"{channel}.csv", index=False)
    print(f"  {channel}: {len(df)} rows")


# ============================================================================
# Programmatic & Affiliate enrichment columns
# ============================================================================

prog_df = pd.read_csv(MOCK_CSV_DIR / "programmatic.csv", parse_dates=["date"])
n = len(prog_df)
prog_df["ivt_rate"]              = np.clip(np.random.normal(0.04, 0.01, n), 0.01, 0.08).round(4)
prog_df["suspicious_click_pct"]  = np.clip(np.random.normal(0.03, 0.01, n), 0.01, 0.06).round(4)
prog_df["geo_anomaly_score"]     = np.clip(np.random.normal(0.10, 0.05, n), 0.00, 0.30).round(3)
prog_df["new_domain_pct"]        = np.clip(np.random.normal(0.05, 0.02, n), 0.01, 0.10).round(4)
# Inject bot fraud signals at end
for i in range(n):
    if (n - 1 - i) <= 3:
        prog_df.loc[i, "ivt_rate"]             = round(np.random.uniform(0.35, 0.55), 4)
        prog_df.loc[i, "suspicious_click_pct"] = round(np.random.uniform(0.40, 0.60), 4)
        prog_df.loc[i, "geo_anomaly_score"]    = round(np.random.uniform(0.70, 0.95), 3)
        prog_df.loc[i, "new_domain_pct"]       = round(np.random.uniform(0.30, 0.50), 4)
prog_df.to_csv(MOCK_CSV_DIR / "programmatic.csv", index=False)

aff_df = pd.read_csv(MOCK_CSV_DIR / "affiliate.csv", parse_dates=["date"])
n = len(aff_df)
aff_df["avg_order_value"]        = np.clip(np.random.normal(50, 5, n), 30, 80).round(2)
aff_df["unique_referral_domains"]= np.random.randint(3, 8, n)
aff_df["coupon_usage_rate"]      = np.clip(np.random.normal(0.10, 0.03, n), 0.03, 0.20).round(4)
aff_df["new_customer_pct"]       = np.clip(np.random.normal(0.60, 0.10, n), 0.30, 0.85).round(4)
for i in range(n):
    if (n - 1 - i) <= 4:
        aff_df.loc[i, "avg_order_value"]         = round(np.random.uniform(12, 22), 2)
        aff_df.loc[i, "unique_referral_domains"]  = np.random.randint(15, 30)
        aff_df.loc[i, "coupon_usage_rate"]        = round(np.random.uniform(0.85, 0.98), 4)
        aff_df.loc[i, "new_customer_pct"]         = round(np.random.uniform(0.10, 0.25), 4)
aff_df.to_csv(MOCK_CSV_DIR / "affiliate.csv", index=False)
print("  Enriched programmatic (fraud signals) and affiliate (coupon signals)")


# ============================================================================
# 2. INFLUENCER DATA (2020-2026, bi-monthly posts per creator)
# ============================================================================

def generate_influencer_data() -> pd.DataFrame:
    creators = {
        "INF_001": {"name": "TechGuru",    "platform": "youtube",   "base_eng": 0.040, "spend": 5000, "base_imp": 200000},
        "INF_002": {"name": "FitLife",     "platform": "instagram", "base_eng": 0.050, "spend": 6000, "base_imp": 250000},
        "INF_003": {"name": "MomHacks",    "platform": "instagram", "base_eng": 0.060, "spend": 3500, "base_imp": 120000},
        "INF_004": {"name": "GamerX",      "platform": "twitch",    "base_eng": 0.055, "spend": 5000, "base_imp": 180000},
        "INF_005": {"name": "StyleIcon",   "platform": "instagram", "base_eng": 0.045, "spend": 7000, "base_imp": 300000},
        "INF_006": {"name": "CharityChamp","platform": "youtube",   "base_eng": 0.070, "spend": 4000, "base_imp": 150000},
        "INF_999": {"name": "ViralViper",  "platform": "tiktok",    "base_eng": 0.001, "spend": 15000,"base_imp": 500000},  # Fraud
    }

    data = []
    # Posts roughly every 2 weeks per creator over the full 6-year range
    post_dates_range = pd.date_range(start=START_DATE, end=END_DATE, freq="14D")

    for date in post_dates_range:
        # Apply GoFundMe crisis multiplier to authentic creators
        crisis_boost = 1.0
        for event in MACRO_EVENTS:
            if event["start"] <= date <= event["end"]:
                ch = event["channels"].get("meta_ads", {})
                crisis_boost *= (1.0 / ch.get("cpa_mult", 1.0)) if ch.get("cpa_mult", 1.0) < 1 else 1.0
        crisis_boost = min(crisis_boost, 3.5)  # cap boost

        for creator_id, info in creators.items():
            # Skip fraud creator for older history, only show up in recent 30 days
            if creator_id == "INF_999" and (END_DATE - date).days > 30:
                continue

            is_fraud = creator_id == "INF_999"
            impressions  = int(add_noise(info["base_imp"], 0.3))
            eng_rate     = add_noise(info["base_eng"], 0.15)

            if not is_fraud:
                eng_rate *= min(crisis_boost, 1.5)  # authentic creators benefit during crises

            engagements  = int(impressions * eng_rate)
            clicks       = int(engagements * add_noise(0.2, 0.1))
            conversions  = int(clicks * add_noise(0.05, 0.2)) if not is_fraud else 0

            data.append({
                "campaign_id":        f"CAMP_{random.randint(100, 999)}",
                "creator_id":         creator_id,
                "creator_name":       info["name"],
                "platform":           info["platform"],
                "post_date":          date,
                "contract_value":     int(add_noise(info["spend"], 0.2)),
                "impressions":        impressions,
                "engagements":        engagements,
                "clicks":             clicks,
                "conversions":        conversions,
                "engagement_rate":    round(eng_rate, 4),
                "earned_media_value": round(engagements * 2.5, 2),
            })

    return pd.DataFrame(data)


print("\nGenerating influencer data (2020-2026, bi-monthly posts)...")
influencer_df = generate_influencer_data()
influencer_df.to_csv(MOCK_CSV_DIR / "influencer_campaigns.csv", index=False)
print(f"  influencer_campaigns: {len(influencer_df)} rows")


# ============================================================================
# 3. MARKET & STRATEGY DATA (Tier 3/4)
# ============================================================================

# --- Competitor intel ---
def generate_competitor_intel() -> pd.DataFrame:
    data = []
    competitors = ["BrandX", "CrowdFund+", "MegaRaise", "GiveNow"]
    channels_covered = ["google_search", "meta_ads", "tv", "programmatic"]

    for i, date in enumerate(DATES):
        # BrandX always active on search
        if random.random() < 0.25:
            # Q4 and election periods: competitors also ramp up
            mults = get_day_multipliers(date, "google_search", i)
            impact = "high" if mults["spend_m"] > 1.3 else "medium"
            data.append({
                "date":          date,
                "competitor":    "BrandX",
                "channel":       "google_search",
                "activity_type": "aggressive_bidding",
                "impact_level":  impact,
                "details":       f"Impression share lost {random.randint(8, 25)}% vs prior week",
            })

        # Periodic competitor TV bursts
        if random.random() < 0.05:
            data.append({
                "date":          date,
                "competitor":    random.choice(["CrowdFund+", "MegaRaise"]),
                "channel":       "tv",
                "activity_type": "brand_campaign",
                "impact_level":  "low",
                "details":       "Competitor national TV spot airing",
            })

        # Election periods: political ad competition on programmatic
        for event in MACRO_EVENTS:
            if "Election" in event.get("name", "") and event["start"] <= date <= event["end"]:
                if random.random() < 0.6:
                    data.append({
                        "date":          date,
                        "competitor":    "Political PACs",
                        "channel":       "programmatic",
                        "activity_type": "political_ad_competition",
                        "impact_level":  "high",
                        "details":       "Political ad spend elevating CPMs 30-50%",
                    })

    return pd.DataFrame(data)


# --- Market trends (donation/fundraising search interest) ---
def generate_market_trends() -> pd.DataFrame:
    data = []
    topics = ["Donation", "Fundraising", "Charity", "Online Giving"]

    for i, date in enumerate(DATES):
        for topic in topics:
            # Base interest grows ~8% per year
            base = 40 + (i / 365.0) * 8.0
            # Q4 seasonal
            month = date.month
            if month in (11, 12):
                seasonal = 1.5
            elif month == 1:
                seasonal = 0.7
            else:
                seasonal = 1.0
            # Crisis spikes
            crisis_mult = 1.0
            for event in MACRO_EVENTS:
                if event["start"] <= date <= event["end"]:
                    # Events that cause donation surges boost market interest
                    ch_data = event["channels"].get("google_search", {})
                    if ch_data.get("cpa_mult", 1.0) < 0.7:  # major donation surge
                        crisis_mult = max(crisis_mult, 2.5)

            interest = base * seasonal * crisis_mult + np.random.normal(0, 2)
            data.append({
                "date":           date,
                "topic":          topic,
                "interest_score": round(max(5, interest), 1),
            })

    return pd.DataFrame(data)


# --- MMM Saturation (multi-channel, time-series) ---
def generate_mmm_saturation() -> pd.DataFrame:
    data = []
    mmm_channels = {
        "google_search":  {"base_sat": 8000,  "base_roas": 2.1},
        "google_pmax":    {"base_sat": 5000,  "base_roas": 1.8},
        "meta_ads":       {"base_sat": 10000, "base_roas": 1.4},
        "tiktok_ads":     {"base_sat": 4000,  "base_roas": 1.2},
        "linkedin_ads":   {"base_sat": 2000,  "base_roas": 0.9},
        "tv":             {"base_sat": 15000, "base_roas": 0.8},
        "programmatic":   {"base_sat": 6000,  "base_roas": 1.0},
        "affiliate":      {"base_sat": 3000,  "base_roas": 3.5},
        "direct_mail":    {"base_sat": 7000,  "base_roas": 1.1},
        "podcast":        {"base_sat": 4500,  "base_roas": 1.6},
    }

    for i, date in enumerate(DATES):
        for channel, cfg in mmm_channels.items():
            # Slow drift in saturation point over years
            drift = np.sin(i / 180) * 0.15  # ~6-month cycle
            growth_adj = 1.0 + 0.08 * (i / 365.0)  # channels can absorb more spend as platform grows

            # Google PMax becomes saturated in the last 30 days (demo scenario)
            if channel == "google_pmax" and (TOTAL_DAYS - 1 - i) <= 30:
                roas = 0.7 + np.random.normal(0, 0.05)
                rec = "maintain"
            else:
                roas = cfg["base_roas"] * (1 + drift) + np.random.normal(0, 0.05)
                rec = "scale" if roas >= 1.2 else ("maintain" if roas >= 0.9 else "reduce")

            data.append({
                "date":                    date,
                "channel":                 channel,
                "saturation_point_daily":  int(cfg["base_sat"] * growth_adj * (1 + drift * 0.5)),
                "current_marginal_roas":   round(max(0.3, roas), 2),
                "recommendation":          rec,
            })

    return pd.DataFrame(data)


# --- MTA Attribution (multi-channel, time-series) ---
def generate_mta_attribution() -> pd.DataFrame:
    data = []
    mta_channels = {
        # (last_click_base, mta_multiplier)
        # High multiplier = MTA gives much more credit than last-click (assist channel)
        "google_youtube":  (0.5,  5.6),
        "google_search":   (4.0,  0.8),   # Search gets less MTA credit (last touch but not assist)
        "meta_ads":        (2.5,  1.16),
        "tiktok_ads":      (1.2,  1.8),
        "google_display":  (0.8,  2.1),
        "programmatic":    (0.9,  1.9),
        "podcast":         (0.4,  3.2),   # Podcast is strong upper funnel
        "tv":              (0.3,  4.0),   # TV: almost no last-click but high MTA credit
        "direct_mail":     (1.1,  1.5),
        "affiliate":       (3.0,  0.9),   # Affiliate is mostly last-click
    }

    for i, date in enumerate(DATES):
        for channel, (lc_base, mult) in mta_channels.items():
            last_click = lc_base + np.random.normal(0, lc_base * 0.08)
            mta_roas   = max(0.1, last_click * mult + np.random.normal(0, 0.1))
            assist     = round(1.0 - min(1.0, 1.0 / max(mult, 0.1)), 2)

            data.append({
                "date":              date,
                "channel":           channel,
                "last_click_roas":   round(max(0.1, last_click), 2),
                "data_driven_roas":  round(max(0.1, mta_roas),   2),
                "assist_ratio":      assist,
            })

    return pd.DataFrame(data)


print("\nGenerating market & strategy data (2020-2026)...")

comp_df = generate_competitor_intel()
comp_df.to_csv(MOCK_CSV_DIR / "competitors.csv", index=False)
print(f"  competitors: {len(comp_df)} rows")

trends_df = generate_market_trends()
trends_df.to_csv(MOCK_CSV_DIR / "market_trends.csv", index=False)
print(f"  market_trends: {len(trends_df)} rows")

mmm_df = generate_mmm_saturation()
mmm_df.to_csv(MOCK_CSV_DIR / "mmm_saturation.csv", index=False)
print(f"  mmm_saturation: {len(mmm_df)} rows")

mta_df = generate_mta_attribution()
mta_df.to_csv(MOCK_CSV_DIR / "mta_attribution.csv", index=False)
print(f"  mta_attribution: {len(mta_df)} rows")


# ============================================================================
# 4. RAG POST-MORTEM INCIDENTS (200+ spanning 2020-2026)
# ============================================================================

def generate_rag_history() -> pd.DataFrame:
    templates = [
        # --- DIGITAL ---
        {
            "type": "CPA Spike", "channel": "google_search",
            "roots": [
                "Competitor 'BrandX' aggressive bidding on donation/fundraising keywords.",
                "New entrant bidding heavily on our exact match keywords.",
                "Auction insights show 40% overlap increase with top competitor.",
                "Q4 seasonal competition drove up CPCs by 35%.",
                "Election cycle political ad spending inflated CPMs across search.",
                "Smart bidding algorithm overcorrected after iOS privacy changes.",
            ],
            "fixes": [
                "Increased brand CPC bids by 20% and filed trademark complaint.",
                "Launched defensive brand campaign with aggressive Top IS target.",
                "Adjusted target CPA to defend impression share against BrandX.",
                "Temporarily increased budget caps to capture holiday demand.",
                "Paused broad match and switched to exact/phrase during election.",
            ],
        },
        {
            "type": "Zero Conversions", "channel": "meta_ads",
            "roots": [
                "Tracking pixel fell off checkout page after deployment #1204.",
                "GTM container rollback accidentally removed purchase event.",
                "Server-side API token expired, causing event loss.",
                "iOS 14.5 ATT rollout caused 48-hour reporting gap on conversions.",
                "Facebook CAPI misconfiguration after server migration.",
            ],
            "fixes": [
                "Re-installed GTM container and added automated pixel monitoring.",
                "Restored previous GTM version and verified checkout firing.",
                "Generated new CAPI token and updated server config.",
                "Switched to 7-day click attribution window for reporting.",
                "Implemented server-side event deduplication layer.",
            ],
        },
        {
            "type": "Spend Surge", "channel": "google_pmax",
            "roots": [
                "PMax auto-expanded to low-quality Display inventory.",
                "Algorithm aggressively targeted mobile app placements.",
                "Uncapped budget allowed PMax to spend 300% of daily average.",
                "Bot traffic spike on unknown placements drove up spend.",
                "Asset group rotation optimized for volume over value during crisis period.",
            ],
            "fixes": [
                "Added placement exclusions and tightened location settings.",
                "Excluded mobile app categories and gaming sites.",
                "Implemented strict daily spend caps and tROAS targets.",
                "Added negative IP lists and enabled click fraud protection.",
            ],
        },
        {
            "type": "Low CTR", "channel": "meta_ads",
            "roots": [
                "Creative fatigue: ad frequency exceeded 8.0.",
                "Audience saturation in 'Lookalike 1%' audience.",
                "Headline 'Free Shipping' no longer resonating post-COVID.",
                "Broken video asset rendering as black screen in feed.",
                "iOS 17 link tracking stripping UTMs, inflating CPC in reporting.",
            ],
            "fixes": [
                "Refreshed creative assets and implemented frequency capping.",
                "Expanded audience to 'Lookalike 5%' and broad interest.",
                "Tested new emotional hook messaging aligned to active crisis.",
                "Re-uploaded video assets and cleared cache.",
            ],
        },
        {
            "type": "High CPL", "channel": "linkedin_ads",
            "roots": [
                "Audience size too small (<50k), leading to high frequency.",
                "Job title targeting too broad, capturing entry-level roles.",
                "LinkedIn Audience Network delivering low-quality clicks.",
                "Corporate giving budgets frozen during Q1 budget cycles.",
            ],
            "fixes": [
                "Expanded audience using lookalikes of corporate donor list.",
                "Added seniority exclusions to target decision makers only.",
                "Disabled Audience Network to focus on feed placements.",
                "Shifted budget to Q3/Q4 when corporate giving peaks.",
            ],
        },
        {
            "type": "Conversion Drop", "channel": "affiliate",
            "roots": [
                "Top affiliate partner removed our link from their homepage.",
                "Coupon code leakage to discount aggregator sites lowered AOV.",
                "Fraudulent leads detected from new sub-affiliate network.",
                "Sub-affiliate network injecting cookie stuffing on checkout.",
            ],
            "fixes": [
                "Renegotiated placement fee with top partner.",
                "Invalidated leaked codes and issued exclusive partner links.",
                "Voided commissions for fraudulent leads and blocked sub-ID.",
                "Implemented last-touch validation on all affiliate conversions.",
            ],
        },
        {
            "type": "Reach Drop", "channel": "tv",
            "roots": [
                "Primetime spots preempted by breaking news / crisis coverage.",
                "Frequency cap issues on Connected TV (CTV) inventory.",
                "Measurement lag from Nielsen reporting caused data gap.",
                "CTV DSP serving to incorrect geo during national campaign.",
            ],
            "fixes": [
                "Received make-goods for preempted spots next week.",
                "Applied strict frequency capping across CTV publishers.",
                "Used spot logs for interim reporting while awaiting Nielsen.",
                "Added geo verification layer to CTV buys.",
            ],
        },
        {
            "type": "Low Engagement", "channel": "podcast",
            "roots": [
                "Host read script was truncated during recording.",
                "Promo code mentioned on air didn't match backend system.",
                "Episode released on holiday weekend with low downloads.",
                "Podcast audience overlap too high with existing donors; no new reach.",
            ],
            "fixes": [
                "Requested re-read/make-good for next episode.",
                "Created vanity URL redirect to fix promo code error.",
                "Shifted future ad buys to mid-week release schedules.",
                "Rotated to new podcast network with fresher audience.",
            ],
        },
        {
            "type": "Fraud Alert", "channel": "influencer_campaigns",
            "roots": [
                "Creator engagement rate 0.01% despite 1M followers.",
                "Comment section filled with generic bot spam.",
                "Sudden spike in followers from non-target geo (click farm).",
                "Creator's audience audit revealed 60% fake followers.",
                "Influencer disclosed paid partnership but not to platform's charity audience.",
            ],
            "fixes": [
                "Terminated contract for breach of authenticity clause.",
                "Blacklisted creator from future campaigns.",
                "Implemented Modash/HypeAuditor vetting before next hire.",
                "Required audience demographics report before contract signing.",
            ],
        },
        {
            "type": "Response Rate Drop", "channel": "direct_mail",
            "roots": [
                "Mailing list had high percentage of outdated addresses.",
                "Postal delays during holiday peak caused late delivery.",
                "Creative execution (envelope design) performed poorly vs control.",
                "Mail arriving after crisis resolved; donor motivation had faded.",
            ],
            "fixes": [
                "Ran NCOA update on mailing list before next drop.",
                "Shifted future mailings to avoid peak postal periods.",
                "A/B tested new envelope designs with stronger urgency hook.",
                "Added real-time crisis messaging insert to in-flight mail pieces.",
            ],
        },
        {
            "type": "Low Impressions", "channel": "ooh",
            "roots": [
                "Construction blocked visibility of 3 billboard locations.",
                "Digital OOH screen malfunctioned for 4 days.",
                "Geofencing radius set too small for attribution.",
                "COVID lockdown: zero foot traffic at all OOH locations.",
            ],
            "fixes": [
                "Negotiated replacement locations with vendor.",
                "Received credit for non-functional screen days.",
                "Expanded geofence radius from 100m to 500m.",
                "Shifted OOH budget to digital for duration of lockdown.",
            ],
        },
        # --- CRISIS-SPECIFIC INCIDENTS ---
        {
            "type": "Donation Surge Mis-Attribution", "channel": "google_search",
            "roots": [
                "Ukraine crisis donation spike misattributed to new brand campaign.",
                "Turkey earthquake search surge conflated with paid campaign performance.",
                "BLM fundraising wave caused organic/paid bleed in attribution.",
                "Crisis-driven direct traffic inflating conversion rates vs actual ad performance.",
            ],
            "fixes": [
                "Separated branded vs non-branded search segmentation in reporting.",
                "Added 'crisis_period' annotation flag to all reports during surge.",
                "Paused paid search bidding during organic surge to reduce wasted spend.",
                "Created separate campaign for crisis keywords to isolate performance.",
            ],
        },
        {
            "type": "Budget Misallocation During Crisis", "channel": "meta_ads",
            "roots": [
                "Budget auto-reallocation shifted funds away from best-performing crisis campaign.",
                "MMM model recommended reducing Meta spend during Ukraine period (model hadn't seen crisis data).",
                "Crisis donation audience excluded by mistake from campaign targeting.",
                "Ad account flagged as 'fundraising' and temporarily restricted during political period.",
            ],
            "fixes": [
                "Overrode automated budget rules and manually allocated to crisis campaign.",
                "Submitted MMM model retraining request with crisis period data.",
                "Removed audience exclusions and added crisis-specific interest segments.",
                "Submitted account verification for fundraising allowlist.",
            ],
        },
        {
            "type": "Tracking Break During COVID", "channel": "google_pmax",
            "roots": [
                "Server migration during COVID lockdown caused 3-day tag firing failure.",
                "iOS 14.5 release coincided with peak COVID donation period; masked conversions.",
                "GA4 migration during Q4 2021 caused 10-day data gap.",
            ],
            "fixes": [
                "Re-deployed tags via server-side GTM with 24h monitoring.",
                "Backfilled conversions using order database export.",
                "Ran parallel UA/GA4 for 60 days to validate data parity.",
            ],
        },
        {
            "type": "Events Channel Collapse", "channel": "events",
            "roots": [
                "COVID lockdown: all in-person fundraising events cancelled.",
                "Delta variant surge caused last-minute cancellations of 12 events.",
                "Venue capacity restrictions limited event ROI by 60%.",
                "Virtual event platform technical failure caused 80% drop-off.",
            ],
            "fixes": [
                "Pivoted to virtual events (Zoom/Teams fundraising webinars).",
                "Reallocated events budget to digital channels for Q2 2020.",
                "Renegotiated venue contracts for partial refunds.",
                "Switched virtual platform from Zoom to Hopin with backup stream.",
            ],
        },
        {
            "type": "IVT / Bot Traffic", "channel": "programmatic",
            "roots": [
                "DSP algorithm expanded to new low-quality SSP partners.",
                "Bot traffic spike: IVT rate jumped from 4% to 48% in 72 hours.",
                "Invalid traffic from data center IPs in non-target geos.",
            ],
            "fixes": [
                "Enabled IAS/MOAT pre-bid filtering across all DSP buys.",
                "Added IP exclusion lists for known data center ranges.",
                "Implemented post-bid IVT scoring with automatic credit back.",
            ],
        },
    ]

    incidents = []
    hist_start = datetime(2020, 1, 1)
    hist_end   = datetime(2026, 3, 5)
    total_hist_days = (hist_end - hist_start).days

    for i in range(220):
        template = random.choice(templates)
        days_offset = random.randint(0, total_hist_days)
        date = hist_start + timedelta(days=days_offset)
        root = random.choice(template["roots"])
        fix  = random.choice(template["fixes"])

        incidents.append({
            "incident_id":     f"INC-{date.year}-{i + 100}",
            "date":            date.strftime("%Y-%m-%d"),
            "channel":         template["channel"],
            "anomaly_type":    template["type"],
            "severity":        random.choice(["high", "medium", "critical"]),
            "root_cause":      root,
            "resolution":      fix,
            "similarity_score": round(random.uniform(0.70, 0.95), 2),
        })

    # Sort by date for cleanliness
    incidents.sort(key=lambda x: x["date"])
    return pd.DataFrame(incidents)


print("\nGenerating 220 RAG post-mortem incidents (2020-2026)...")
rag_df = generate_rag_history()
rag_df.to_csv(POST_MORTEMS_DIR / "incidents.csv", index=False)
print(f"  incidents: {len(rag_df)} rows  ({rag_df['date'].min()} to {rag_df['date'].max()})")

print("\n" + "=" * 60)
print("Mock Data Generation Complete")
print(f"  Date Range: {START_DATE.date()} to {END_DATE.date()} ({TOTAL_DAYS} days)")
print("  Run 'make mock-data && make init-rag' to regenerate + re-embed.")
print("=" * 60)
