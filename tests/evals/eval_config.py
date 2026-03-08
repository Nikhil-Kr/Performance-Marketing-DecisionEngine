"""
Ground Truth Configuration for Expedition Evals.

Each scenario maps a known injected anomaly (from generate_mock_data.py)
to the expected correct outputs at every pipeline stage. This is the
single source of truth for all eval levels.

Scoring convention:
  - Deterministic checks return pass/fail (1.0 or 0.0)
  - LLM-graded checks return 1-5 scale (normalized to 0.0-1.0)
  - Composite scores are weighted averages
"""

# ============================================================================
# GROUND TRUTH SCENARIOS
# ============================================================================
# These come directly from ANOMALIES in scripts/generate_mock_data.py.
# Each defines what Expedition SHOULD conclude if working correctly.

SCENARIOS = [
    {
        "id": "pmax_spend_spike",
        "description": "Google PMax 3x spend spike with 70% ROAS drop",
        "injected_anomaly": {
            "channel": "google_pmax",
            "metric": "spend",          # or roas — both should fire
            "direction": "spike",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 12000.0,
            "expected_value": 4000.0,
            "deviation_pct": 200.0,
        },
        # --- Level 1: Router ---
        "expected_route": "paid_media",
        # --- Level 2: Diagnosis ---
        "ground_truth_cause": (
            "Google PMax overspent budget on low-quality YouTube/Display "
            "placements, causing a ~3x spend increase and ~70% ROAS collapse. "
            "This is a Performance Max asset group or bidding strategy issue, "
            "not an external market shift."
        ),
        "required_themes": [
            "pmax",             # must mention PMax or Performance Max
            "spend",            # must mention spend increase
            "roas",             # must mention ROAS decline
        ],
        "forbidden_themes": [
            "pixel",            # this is NOT a tracking issue
            "meta",             # wrong channel
        ],
        # --- Level 3: Critic ---
        "should_pass_critic": True,   # a correct diagnosis should validate
        "max_hallucination_risk": 0.5,
        # --- Level 4: Actions ---
        "expected_action_types": ["bid_adjustment", "budget_change"],
        "inappropriate_actions": ["contract", "negotiation"],  # not influencer/offline
        "expected_platform": "google_ads",
    },
    {
        "id": "meta_pixel_death",
        "description": "Meta Ads pixel broken — normal spend but 95% conversion drop",
        "injected_anomaly": {
            "channel": "meta_ads",
            "metric": "conversions",
            "direction": "drop",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 11.0,
            "expected_value": 214.0,
            "deviation_pct": -95.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Meta Ads conversion tracking pixel is broken or misconfigured. "
            "Spend is normal but reported conversions dropped ~95%, indicating "
            "a measurement/tracking failure rather than actual performance decline."
        ),
        "required_themes": [
            "pixel",           # or tracking/measurement
            "conversion",      # must mention conversion drop
        ],
        "forbidden_themes": [
            "competitor",      # not a bidding war
            "creative",        # not ad fatigue
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification"],  # alert engineering
        "inappropriate_actions": ["bid_adjustment", "pause"],  # don't change bids for a pixel issue
        "expected_platform": "meta_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 3: Google Search — Competitor Bidding War
    # CPA jumps 2.5x because a competitor is aggressively bidding on our
    # brand and category terms. Spend also rises ~50% as the algorithm
    # chases the same volume at higher prices.
    # ------------------------------------------------------------------
    {
        "id": "search_competitor_bidding",
        "description": "Google Search CPA 2.5x spike from competitor bidding war",
        "injected_anomaly": {
            "channel": "google_search",
            "metric": "cpa",
            "direction": "spike",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 112.0,
            "expected_value": 45.0,
            "deviation_pct": 149.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "A competitor launched aggressive bidding on brand and category "
            "keywords in Google Search, driving CPA up ~2.5x. Spend increased "
            "~50% as automated bidding chased the same conversion volume at "
            "higher auction prices. This is a competitive dynamics issue "
            "requiring bid strategy adjustment, not a tracking or creative problem."
        ),
        "required_themes": [
            "competitor",       # or bidding/auction
            "cpa",              # must mention CPA increase
            "bid",              # bidding strategy context
        ],
        "forbidden_themes": [
            "pixel",            # not a tracking issue
            "creative",         # not ad fatigue
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["bid_adjustment"],
        "inappropriate_actions": ["contract", "negotiation"],
        "expected_platform": "google_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 4: TikTok — Creative Fatigue / ROAS Collapse
    # ROAS drops 65% while spend stays normal. The ads are running but
    # nobody's engaging — frequency is too high and the creative is stale.
    # ------------------------------------------------------------------
    {
        "id": "tiktok_creative_fatigue",
        "description": "TikTok ROAS drops 65% from creative fatigue",
        "injected_anomaly": {
            "channel": "tiktok_ads",
            "metric": "roas",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 0.63,
            "expected_value": 1.8,
            "deviation_pct": -65.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "TikTok ad creative has fatigued — the same assets have been "
            "running too long, frequency is high, and engagement has dropped. "
            "ROAS collapsed ~65% while spend remained normal, indicating the "
            "issue is ad performance (creative/audience), not budget or tracking."
        ),
        "required_themes": [
            "creative",         # or fatigue/engagement
            "roas",             # must mention ROAS decline
        ],
        "forbidden_themes": [
            "pixel",            # not tracking
            "competitor",       # not bidding war
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "pause"],  # alert creative team or pause to refresh
        "inappropriate_actions": ["contract", "negotiation"],
        "expected_platform": "tiktok_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 5: LinkedIn — Audience Saturation / CPA Explosion
    # CPA triples because the audience is too narrow and frequency is
    # through the roof. Spend stays flat but efficiency craters.
    # ------------------------------------------------------------------
    {
        "id": "linkedin_audience_saturation",
        "description": "LinkedIn CPA 3x spike from audience saturation",
        "injected_anomaly": {
            "channel": "linkedin_ads",
            "metric": "cpa",
            "direction": "spike",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 360.0,
            "expected_value": 120.0,
            "deviation_pct": 200.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "LinkedIn audience is saturated — the target audience is too "
            "narrow (<50k), causing high frequency and declining engagement. "
            "CPA tripled while spend stayed flat, indicating the issue is "
            "audience exhaustion rather than budget, tracking, or competition."
        ),
        "required_themes": [
            "saturation",       # or audience/frequency
            "cpa",              # must mention CPA increase
        ],
        "forbidden_themes": [
            "pixel",            # not tracking
            "competitor",       # not bidding war (LinkedIn doesn't have the same auction dynamics)
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["pause", "notification"],  # pause to let audience refresh
        "inappropriate_actions": ["contract", "negotiation"],
        "expected_platform": "linkedin_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 6: TV — Preempted Spots / Reach Collapse (Offline)
    # Conversions drop 80% because primetime spots were preempted by
    # breaking news. This tests the offline investigator pathway.
    # ------------------------------------------------------------------
    {
        "id": "tv_preempted_spots",
        "description": "TV conversions drop 80% from preempted ad spots",
        "injected_anomaly": {
            "channel": "tv",
            "metric": "conversions",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 13.0,
            "expected_value": 67.0,
            "deviation_pct": -80.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "TV ad spots were preempted by breaking news coverage, causing "
            "an ~80% drop in attributed conversions. Spend continued as "
            "contracted but ads did not air in their scheduled slots. This "
            "is an inventory delivery issue requiring make-goods from the "
            "network, not a creative or targeting problem."
        ),
        "required_themes": [
            "preempt",          # or spots/inventory/schedule
            "conversion",       # must mention conversion drop
        ],
        "forbidden_themes": [
            "pixel",            # not a digital tracking issue
            "bidding",          # TV doesn't have real-time bidding
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "make_good"],  # alert media buyer + request make-goods from network
        "inappropriate_actions": ["bid_adjustment", "exclusion"],  # not digital actions
        "expected_platform": "tv",
    },
    # ------------------------------------------------------------------
    # SCENARIO 7: Programmatic — Bot Traffic / Invalid Clicks
    # Spend spikes 2.5x but conversions drop to near zero. The money
    # is being eaten by bot/fraud traffic on low-quality inventory.
    # ------------------------------------------------------------------
    {
        "id": "programmatic_bot_traffic",
        "description": "Programmatic spend 2.5x spike with near-zero conversions (bot traffic)",
        "injected_anomaly": {
            "channel": "programmatic",
            "metric": "spend",
            "direction": "spike",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 7500.0,
            "expected_value": 3000.0,
            "deviation_pct": 150.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Programmatic spend spiked ~2.5x while conversions dropped to "
            "near zero, indicating bot or fraudulent traffic on low-quality "
            "inventory. The DSP is serving impressions to non-human traffic "
            "that generates clicks but no conversions. This requires IP "
            "exclusions and inventory source review, not bid adjustments."
        ),
        "required_themes": [
            "bot",              # or fraud/invalid/non-human
            "spend",            # must mention spend spike
        ],
        "forbidden_themes": [
            "creative",         # not ad fatigue
            "pixel",            # not tracking (conversions are genuinely zero)
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["exclusion", "notification"],  # block IPs + alert
        "inappropriate_actions": ["contract"],
        "expected_platform": "programmatic",
    },
    # ------------------------------------------------------------------
    # SCENARIO 8: Affiliate — Suspicious Conversion Spike (Coupon Leak)
    # Conversions spike 5x but revenue doesn't follow — fraudulent or
    # low-quality leads from coupon leakage to discount aggregator sites.
    # ------------------------------------------------------------------
    {
        "id": "affiliate_coupon_fraud",
        "description": "Affiliate conversions spike 5x from coupon leakage/fraud",
        "injected_anomaly": {
            "channel": "affiliate",
            "metric": "conversions",
            "direction": "spike",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 333.0,
            "expected_value": 67.0,
            "deviation_pct": 400.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Affiliate conversions spiked ~5x due to coupon code leakage to "
            "discount aggregator sites. Users are finding exclusive codes on "
            "third-party sites and converting without genuine affiliate "
            "attribution, inflating conversion counts with low-AOV orders. "
            "This is a partner compliance issue, not genuine performance."
        ),
        "required_themes": [
            "coupon",           # or affiliate/partner/leakage/fraud
            "conversion",       # must mention conversion spike
        ],
        "forbidden_themes": [
            "pixel",            # not a tracking issue
            "creative",         # not ad performance
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "contract"],  # alert + partner contract/compliance action
        "inappropriate_actions": ["bid_adjustment"],  # affiliate doesn't use bidding
        "expected_platform": "affiliate",
    },
    # ------------------------------------------------------------------
    # SCENARIO 9: Influencer — Creator Audience Fatigue
    # Engagement rate drops 70% while posts keep publishing. The creator's
    # audience has seen too much of the same content — wrong fit or burnout.
    # ------------------------------------------------------------------
    {
        "id": "influencer_engagement_drop",
        "description": "Influencer engagement rate drops 70% from creator audience fatigue",
        "injected_anomaly": {
            "channel": "influencer_campaigns",
            "metric": "engagement_rate",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 0.009,
            "expected_value": 0.030,
            "deviation_pct": -70.0,
        },
        "expected_route": "influencer",
        "ground_truth_cause": (
            "Influencer campaign engagement has dropped ~70% due to creator "
            "audience fatigue. The same creator has posted too frequently with "
            "similar content, causing followers to disengage. This is a content "
            "strategy and creator mix issue, not a platform or tracking problem."
        ),
        "required_themes": [
            "engagement",       # or fatigue/creator
            "creator",          # influencer-specific context
        ],
        "forbidden_themes": [
            "pixel",            # not a tracking issue
            "bid",              # influencer doesn't use real-time bidding
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "pause"],
        "inappropriate_actions": ["bid_adjustment", "exclusion"],
        "expected_platform": "influencer",
    },
    # ------------------------------------------------------------------
    # SCENARIO 10: Radio — Conversions Collapse from Station Format Change
    # Station shifted to a different format mid-campaign, losing the
    # audience alignment that was driving conversions.
    # ------------------------------------------------------------------
    {
        "id": "radio_reach_collapse",
        "description": "Radio conversions drop 60% from station format change",
        "injected_anomaly": {
            "channel": "radio",
            "metric": "conversions",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 28.0,
            "expected_value": 70.0,
            "deviation_pct": -60.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "Radio conversions dropped ~60% because the station shifted its "
            "programming format, changing the audience demographic profile. "
            "The GoFundMe donation message is no longer reaching the expected "
            "audience segment. This is a media placement / audience alignment "
            "issue, not a creative or measurement failure."
        ),
        "required_themes": [
            "station",          # or format/radio/audience
            "conversion",       # conversion drop context
        ],
        "forbidden_themes": [
            "pixel",            # radio is not digital tracked
            "bid",              # radio doesn't use auction-based buying
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "make_good"],
        "inappropriate_actions": ["bid_adjustment", "exclusion"],
        "expected_platform": "radio",
    },
    # ------------------------------------------------------------------
    # SCENARIO 11: OOH — Attribution Window Expiry
    # Measured conversions drop 85% not because of real performance decline,
    # but because the attribution window for offline touchpoints expired.
    # ------------------------------------------------------------------
    {
        "id": "ooh_attribution_break",
        "description": "OOH attributed conversions drop 85% from attribution window expiry",
        "injected_anomaly": {
            "channel": "ooh",
            "metric": "conversions",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 9.0,
            "expected_value": 60.0,
            "deviation_pct": -85.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "OOH attributed conversions dropped ~85% because the measurement "
            "attribution window expired or was misconfigured in the analytics "
            "platform. The physical billboards are still running; this is a "
            "measurement methodology issue, not an actual performance decline. "
            "OOH conversions are inherently delayed and require a longer "
            "attribution window than digital channels."
        ),
        "required_themes": [
            "attribution",      # or measurement/window
            "conversion",       # conversion drop context
        ],
        "forbidden_themes": [
            "bid",              # OOH is not auction-based
            "creative",         # not a creative fatigue issue
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification"],
        "inappropriate_actions": ["bid_adjustment", "pause"],
        "expected_platform": "ooh",
    },
    # ------------------------------------------------------------------
    # SCENARIO 12: Events — Event Cancellation / Venue Change
    # Conversions drop 98% because the physical fundraising event was
    # cancelled or moved, with no digital fallback activated.
    # ------------------------------------------------------------------
    {
        "id": "events_cancellation",
        "description": "Events conversions drop 98% from event cancellation",
        "injected_anomaly": {
            "channel": "events",
            "metric": "conversions",
            "direction": "drop",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 2.0,
            "expected_value": 100.0,
            "deviation_pct": -98.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "Events conversions dropped ~98% because the physical fundraising "
            "event was cancelled or significantly venue-changed with no digital "
            "fallback campaign activated. The media buy continued as planned "
            "but there was no event to drive conversions to. This requires "
            "an immediate offline contingency plan."
        ),
        "required_themes": [
            "event",            # cancellation/venue context
            "conversion",       # conversion drop
        ],
        "forbidden_themes": [
            "pixel",            # not a digital tracking issue
            "bid",              # events don't use auction buying
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "make_good"],
        "inappropriate_actions": ["bid_adjustment", "exclusion"],
        "expected_platform": "events",
    },
    # ------------------------------------------------------------------
    # SCENARIO 13: Direct Mail — CPA Spike from Wrong List Segment
    # CPA triples because the mailing went to the wrong prospect list,
    # drastically lowering response rates.
    # ------------------------------------------------------------------
    {
        "id": "direct_mail_cpa_spike",
        "description": "Direct mail CPA spikes 3x from wrong prospect list segment",
        "injected_anomaly": {
            "channel": "direct_mail",
            "metric": "cpa",
            "direction": "spike",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 330.0,
            "expected_value": 110.0,
            "deviation_pct": 200.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "Direct mail CPA tripled because the recent campaign was sent to "
            "a wrong or poorly segmented prospect list. Response rates have "
            "dropped significantly, indicating the recipients are not the "
            "intended donor audience. This is a list quality / segmentation "
            "issue, not a creative or timing problem."
        ),
        "required_themes": [
            "list",             # or segment/prospect
            "cpa",              # CPA spike context
        ],
        "forbidden_themes": [
            "pixel",            # direct mail is not digitally tracked
            "bid",              # no auction in direct mail
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification"],
        "inappropriate_actions": ["bid_adjustment", "exclusion"],
        "expected_platform": "direct_mail",
    },
    # ------------------------------------------------------------------
    # SCENARIO 14: Podcast — CPA Spike from Host Read Change
    # CPA doubles after a host read script was changed without approval,
    # losing the authentic tone that was driving donations.
    # ------------------------------------------------------------------
    {
        "id": "podcast_cpa_spike",
        "description": "Podcast CPA doubles after unauthorized host read change",
        "injected_anomaly": {
            "channel": "podcast",
            "metric": "cpa",
            "direction": "spike",
            "severity": "medium",
        },
        "synthetic_values": {
            "current_value": 160.0,
            "expected_value": 80.0,
            "deviation_pct": 100.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "Podcast CPA doubled after the host read script was changed without "
            "approval, losing the authentic, personalized tone that had been "
            "driving donor conversions. The audience trust dynamic in podcasting "
            "is uniquely dependent on host authenticity. This is a creative / "
            "partnership management issue, not a reach or frequency problem."
        ),
        "required_themes": [
            "host",             # or podcast/read/creative
            "cpa",              # CPA spike context
        ],
        "forbidden_themes": [
            "pixel",            # podcast is not digitally tracked in the same way
            "bid",              # podcast uses fixed CPM buys
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "contract"],
        "inappropriate_actions": ["bid_adjustment", "exclusion"],
        "expected_platform": "podcast",
    },
    # ------------------------------------------------------------------
    # SCENARIO 15: Google Display — Invalid Traffic (IVT / Bot Clicks)
    # Spend spikes 2x but conversions drop to near zero — bot/invalid
    # clicks on low-quality display inventory.
    # ------------------------------------------------------------------
    {
        "id": "google_display_ivt",
        "description": "Google Display spend 2x spike with near-zero conversions from IVT",
        "injected_anomaly": {
            "channel": "google_display",
            "metric": "spend",
            "direction": "spike",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 6000.0,
            "expected_value": 3000.0,
            "deviation_pct": 100.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Google Display spend doubled while conversions dropped to near zero, "
            "indicating invalid traffic (IVT) or bot clicks on low-quality display "
            "inventory placements. The campaign is receiving impressions and clicks "
            "from non-human sources that generate no real donation conversions. "
            "This requires placement exclusions and invalid traffic investigation."
        ),
        "required_themes": [
            "invalid",          # or bot/IVT/fraud
            "spend",            # spend spike context
        ],
        "forbidden_themes": [
            "creative",         # not ad fatigue
            "audience",         # not audience saturation
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["exclusion", "notification"],
        "inappropriate_actions": ["contract", "negotiation"],
        "expected_platform": "google_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 16: Google YouTube — View-Through Attribution Window Shortened
    # ROAS drops 50% not due to real performance decline, but because the
    # view-through attribution window was shortened in campaign settings.
    # ------------------------------------------------------------------
    {
        "id": "google_youtube_viewthrough",
        "description": "Google YouTube ROAS drops 50% from shortened view-through attribution",
        "injected_anomaly": {
            "channel": "google_youtube",
            "metric": "roas",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 1.1,
            "expected_value": 2.2,
            "deviation_pct": -50.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Google YouTube ROAS dropped ~50% because the view-through attribution "
            "window was shortened in campaign settings (e.g., from 30 days to 1 day). "
            "The actual donation conversions are still occurring but are no longer "
            "being credited to YouTube in the reporting. This is a measurement "
            "configuration issue, not a real performance decline."
        ),
        "required_themes": [
            "attribution",      # or view-through/window
            "roas",             # ROAS drop context
        ],
        "forbidden_themes": [
            "creative",         # not creative fatigue
            "competitor",       # not a bidding war
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification"],
        "inappropriate_actions": ["bid_adjustment", "pause"],
        "expected_platform": "google_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 17: COVID-Era — Events Channel Collapse (Mar 2020)
    # Events spend drops 95% because all physical fundraising events were
    # cancelled during COVID lockdowns. Classic force-majeure scenario.
    # ------------------------------------------------------------------
    {
        "id": "covid_events_collapse",
        "description": "Events spend drops 95% during COVID lockdown (Mar 2020)",
        "injected_anomaly": {
            "channel": "events",
            "metric": "spend",
            "direction": "drop",
            "severity": "critical",
        },
        "synthetic_values": {
            "current_value": 380.0,
            "expected_value": 7600.0,
            "deviation_pct": -95.0,
        },
        "expected_route": "offline",
        "ground_truth_cause": (
            "Events channel spend collapsed ~95% due to COVID-19 lockdowns "
            "forcing cancellation of all physical fundraising events. This is "
            "a macro force-majeure event, not a campaign execution failure. "
            "Budget should be reallocated to digital donation channels (Meta, "
            "Google Search) which are seeing increased donor activity during "
            "the crisis period."
        ),
        "required_themes": [
            "covid",            # or lockdown/pandemic/crisis
            "event",            # events channel context
        ],
        "forbidden_themes": [
            "bid",              # not a bidding issue
            "creative",         # not a creative failure
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["notification", "make_good"],
        "inappropriate_actions": ["bid_adjustment", "exclusion"],
        "expected_platform": "events",
    },
    # ------------------------------------------------------------------
    # SCENARIO 18: Ukraine War Donation Surge — Search CPA Drop (Feb 2022)
    # Google Search CPA drops 65% because organic demand for Ukraine relief
    # donations spikes dramatically, driving highly efficient conversions.
    # ------------------------------------------------------------------
    {
        "id": "ukraine_search_surge",
        "description": "Google Search CPA drops 65% from Ukraine war donation surge",
        "injected_anomaly": {
            "channel": "google_search",
            "metric": "cpa",
            "direction": "drop",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 15.75,
            "expected_value": 45.0,
            "deviation_pct": -65.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Google Search CPA dropped ~65% due to a massive organic demand "
            "surge driven by the Ukraine humanitarian crisis. Donor intent is "
            "exceptionally high — people are actively searching for ways to help. "
            "This is a positive anomaly driven by external macro events, not a "
            "campaign optimization. Budget should be increased to capture the "
            "full demand surge while it lasts."
        ),
        "required_themes": [
            "ukraine",          # or crisis/humanitarian/surge
            "cpa",              # CPA drop context
        ],
        "forbidden_themes": [
            "pixel",            # not a tracking issue
            "fraud",            # not invalid traffic
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["budget_change", "bid_adjustment"],
        "inappropriate_actions": ["pause", "contract"],
        "expected_platform": "google_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 19: Giving Tuesday — Meta ROAS Spike
    # Meta ROAS spikes 3x on Giving Tuesday from seasonal donation surge.
    # This is expected but must be identified as seasonal, not anomalous.
    # ------------------------------------------------------------------
    {
        "id": "giving_tuesday_spike",
        "description": "Meta Ads ROAS spikes 3x on Giving Tuesday seasonal surge",
        "injected_anomaly": {
            "channel": "meta_ads",
            "metric": "roas",
            "direction": "spike",
            "severity": "medium",
        },
        "synthetic_values": {
            "current_value": 5.4,
            "expected_value": 1.8,
            "deviation_pct": 200.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Meta Ads ROAS spiked ~3x on Giving Tuesday due to the annual "
            "charitable giving surge. This is an expected seasonal pattern — "
            "donor intent spikes dramatically on Giving Tuesday as people "
            "fulfill end-of-year charitable commitments. This is a positive "
            "anomaly that warrants budget increase, not investigation. "
            "Historical data shows the same spike pattern each year."
        ),
        "required_themes": [
            "giving",           # or seasonal/tuesday/donation
            "roas",             # ROAS spike context
        ],
        "forbidden_themes": [
            "pixel",            # not a tracking issue
            "fraud",            # not invalid conversions
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["budget_change"],
        "inappropriate_actions": ["pause", "exclusion"],
        "expected_platform": "meta_ads",
    },
    # ------------------------------------------------------------------
    # SCENARIO 20: US Election CPM Inflation — Meta CPA Spike
    # Meta CPA spikes 80% during US election season as political ad
    # spending floods the auction and inflates CPMs for all advertisers.
    # ------------------------------------------------------------------
    {
        "id": "election_cpm_spike",
        "description": "Meta Ads CPA spikes 80% from US election CPM inflation",
        "injected_anomaly": {
            "channel": "meta_ads",
            "metric": "cpa",
            "direction": "spike",
            "severity": "high",
        },
        "synthetic_values": {
            "current_value": 162.0,
            "expected_value": 90.0,
            "deviation_pct": 80.0,
        },
        "expected_route": "paid_media",
        "ground_truth_cause": (
            "Meta Ads CPA spiked ~80% due to US election season CPM inflation. "
            "Political advertisers are flooding the Meta auction with high-budget "
            "campaigns, driving up CPMs for all advertisers including GoFundMe. "
            "This is an external market condition — the campaign itself is "
            "performing normally at the impression level. Consider reducing "
            "budgets or shifting spend to less affected channels until election "
            "season ends."
        ),
        "required_themes": [
            "election",         # or political/cpm/inflation
            "cpa",              # CPA spike context
        ],
        "forbidden_themes": [
            "pixel",            # not a tracking issue
            "creative",         # not ad fatigue
        ],
        "should_pass_critic": True,
        "max_hallucination_risk": 0.5,
        "expected_action_types": ["budget_change", "bid_adjustment"],
        "inappropriate_actions": ["exclusion", "contract"],
        "expected_platform": "meta_ads",
    },
]


# ============================================================================
# ROUTING GROUND TRUTH
# ============================================================================
# Complete mapping of every channel to its expected investigator.
# Used by Level 1 eval — should be 100% deterministic.

ROUTING_TRUTH = {
    # Paid Media
    "google_search":   "paid_media",
    "google_pmax":     "paid_media",
    "google_display":  "paid_media",
    "google_youtube":  "paid_media",
    "meta_ads":        "paid_media",
    "tiktok_ads":      "paid_media",
    "linkedin_ads":    "paid_media",
    "programmatic":    "paid_media",
    "affiliate":       "paid_media",
    # Influencer
    "influencer_campaigns": "influencer",
    "influencer":           "influencer",
    # Offline
    "direct_mail": "offline",
    "tv":          "offline",
    "radio":       "offline",
    "ooh":         "offline",
    "events":      "offline",
    "podcast":     "offline",
}


# ============================================================================
# CRITIC CALIBRATION CASES
# ============================================================================
# Synthetic diagnosis pairs: one good, one deliberately bad.
# Used by Level 3 eval to test critic sensitivity.

CRITIC_CALIBRATION = {
    "good_diagnosis": {
        "root_cause": "Google PMax auto-allocated budget to low-performing placements via the 'Prospecting' asset group, causing a 3x spend increase and 70% ROAS decline over the last 3 days.",
        "confidence": 0.85,
        "supporting_evidence": [
            "Spend increased from baseline to 3x over the last 3 days",
            "ROAS dropped 70% over the same window",
            "PMax asset group 'Prospecting' responsible for 80% of overspend",
            "Spend deviation of 200% from expected value ($4,000 → $12,000)",
        ],
        "recommended_actions": ["Reduce PMax budget cap", "Pause 'Prospecting' asset group", "Review placement performance"],
        "executive_summary": "PMax overspend driven by the Prospecting asset group. Immediate budget cap adjustment recommended.",
    },
    "bad_diagnosis_hallucinated": {
        "root_cause": "A competitor launched a $50M Super Bowl campaign that disrupted the entire programmatic ecosystem, causing Google's AI to panic-bid across all channels simultaneously.",
        "confidence": 0.95,
        "supporting_evidence": [
            "Industry sources confirm the $50M competitor campaign",   # fabricated
            "Google's internal AI systems experienced unprecedented load",  # fabricated
            "All advertisers in the vertical saw identical 3x spend spikes",  # fabricated
            "PMax algorithm entered 'emergency mode' per Google support",  # fabricated
        ],
        "recommended_actions": ["File complaint with Google", "Request refund for overspend"],
        "executive_summary": "Competitor disruption caused systemic platform failure. Unprecedented event.",
    },
    "bad_diagnosis_ungrounded": {
        "root_cause": "Seasonal trends and general market conditions led to gradual performance shifts.",
        "confidence": 0.72,
        "supporting_evidence": [
            "Performance has been variable this quarter",   # vague, no data
            "Market conditions are challenging",            # no specifics
        ],
        "recommended_actions": ["Continue monitoring"],
        "executive_summary": "Normal market variation. No action needed.",
    },
    "anomaly_for_calibration": {
        "channel": "google_pmax",
        "metric": "spend",
        "direction": "spike",
        "severity": "critical",
        "current_value": 12000.0,
        "expected_value": 4000.0,
        "deviation_pct": 200.0,
    },
}


# ============================================================================
# ACTION SCORING RULES
# ============================================================================
# Scoring rubric for action appropriateness.

ACTION_SCORING = {
    # If the action type is in expected_action_types → full points
    "exact_match": 1.0,
    # If the action type is reasonable but not ideal → partial
    "partial_match": 0.5,
    # If the action type is in inappropriate_actions → penalty
    "inappropriate": 0.0,
    # If the platform is wrong → penalty
    "wrong_platform_penalty": 0.3,
}


# ============================================================================
# LLM-AS-JUDGE PROMPTS
# ============================================================================

DIAGNOSIS_GRADER_SYSTEM = """You are an expert evaluator for a marketing anomaly detection system.
You will be given:
1. A GROUND TRUTH description of what actually caused the anomaly
2. The SYSTEM'S DIAGNOSIS of what it thinks caused the anomaly

Score the diagnosis on three dimensions (1-5 each):

ACCURACY: Does the diagnosis identify the correct root cause?
  5 = Correct cause identified with specific details
  4 = Correct cause identified, minor details wrong
  3 = Partially correct — right direction but vague
  2 = Mostly wrong but touches on relevant factors
  1 = Completely wrong or unrelated cause

GROUNDEDNESS: Is the diagnosis supported by evidence, or does it make unsupported claims?
  5 = Every claim backed by specific data points
  4 = Most claims supported, minor speculation
  3 = Mix of supported and unsupported claims
  2 = Mostly speculative with thin evidence
  1 = Pure speculation or fabricated evidence

COMPLETENESS: Does the diagnosis cover the full picture?
  5 = Root cause + evidence + impact + actionable recommendation
  4 = Root cause + evidence + either impact or recommendation
  3 = Root cause + some evidence
  2 = Root cause only, no supporting analysis
  1 = Incomplete or incoherent

Also check:
- REQUIRED THEMES: Were these concepts mentioned? (list which were missing)
- FORBIDDEN THEMES: Were any incorrect themes present? (list which appeared)

Respond in this exact JSON format:
{
  "accuracy": <1-5>,
  "groundedness": <1-5>,
  "completeness": <1-5>,
  "required_themes_present": [<list of themes found>],
  "required_themes_missing": [<list of themes not found>],
  "forbidden_themes_found": [<list of forbidden themes that appeared>],
  "reasoning": "<1-2 sentence explanation>"
}"""

DIAGNOSIS_GRADER_USER = """GROUND TRUTH:
{ground_truth}

REQUIRED THEMES (must be mentioned): {required_themes}
FORBIDDEN THEMES (must NOT be mentioned): {forbidden_themes}

SYSTEM'S DIAGNOSIS:
Root Cause: {diagnosis_root_cause}
Confidence: {diagnosis_confidence}
Evidence: {diagnosis_evidence}
Executive Summary: {diagnosis_summary}

Score this diagnosis:"""


# ============================================================================
# THRESHOLDS
# ============================================================================

PASS_THRESHOLDS = {
    "router_accuracy": 1.0,           # must be perfect (deterministic)
    "diagnosis_accuracy": 0.75,       # raised from 0.6 — demo-grade confidence
    "diagnosis_groundedness": 0.75,   # raised from 0.6
    "diagnosis_completeness": 0.70,   # raised from 0.6
    "critic_sensitivity": 0.80,       # raised from 0.75 — catch more bad diagnoses
    "critic_specificity": 0.80,       # raised from 0.75
    "action_appropriateness": 0.75,   # raised from 0.6
    "e2e_composite": 0.75,            # raised from 0.6
    # Levels 6-9: Tier A/B/C eval expansion
    "rag_quality": 0.75,              # RAG temporal filtering, relevancy, precision
    "safety_guardrails": 0.90,        # strict — safety-critical (MMM, retry logic)
    "integration": 0.75,              # cross-component (correlation, dates, critic)
    "robustness": 0.80,               # fallbacks, JSON parsing, prompt substitution
    # Levels 10-11: Tier D/E eval expansion
    "finops_performance": 0.75,        # model tiers, parameters, fallbacks
    "business_ux": 0.75,               # feedback, audit, state schema, graph structure
}