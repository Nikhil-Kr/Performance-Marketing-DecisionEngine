# Expedition Flow

**How the agent works, node by node — from "user clicks Investigate" to "action proposed".**

---

## Agent Flow

```
START
  │
  ▼
Pre-Flight ──→ [fail] ──→ ABORT ──→ END
  │
  │ pass
  ▼
Detect ──→ [no anomalies] ──→ COMPLETE ──→ END
  │
  │ anomalies found
  ▼
Router
  │
  ├── paid_media ──→ Paid Media Investigator ──┐
  ├── influencer ──→ Influencer Investigator ──┤
  └── offline ────→ Offline Investigator ──────┘
                                               │
                                               ▼
                                           Memory (RAG)
                                               │
                                               ▼
                                     ┌──→ Explainer
                                     │         │
                                     │         ▼
                                     │      Critic
                                     │         │
                                     │         ├── Pass ──→ Proposer ──→ END
                                     │         ├── Retry ──→ Prepare Feedback ──┘
                                     │         └── High Risk ──→ END (escalate)
                                     │
                                     └── Retry Loop (max 2x)
```

---

## How It Works (User Flow)

1. `make run` → Starts Streamlit on localhost:8501
2. Dashboard loads → Shows detected anomalies across all channels
3. User (optionally) selects a historical date range in the sidebar → stored as `analysis_start_date` / `analysis_end_date` in state
4. User clicks **Investigate** on an anomaly
5. LangGraph executes the full pipeline:
   - **preflight** → Validates data freshness; cross-channel correlation scoring
   - **detect** → Finds anomalies, selects highest severity
   - **router** → Routes to paid_media, influencer, or offline investigator
   - **investigator** → Gathers performance + market + strategy evidence; calls Tier 1 LLM
   - **memory** → Temporally-filtered RAG search for similar historical incidents
   - **explainer** → Tier 2 LLM synthesizes diagnosis; infers `root_cause_category`; sets `allowed_action_keys`
   - **critic** → Triple-Lock validation (if fails, loops back to explainer with feedback)
   - **proposer** → LLM maps diagnosis to action templates; MMM guardrail blocks budget increases on saturated channels
6. Results displayed across 5 dashboard tabs (see Dashboard Tab Map below)

---

## Node Reference

### Pre-Flight Check
**File:** `src/nodes/preflight.py` → `preflight_check()`

Validates data freshness before investigation. Prevents diagnosing noise from stale pipelines. In mock mode, always passes. In production, checks BigQuery last-refresh timestamps against `MAX_DATA_LATENCY_HOURS` (1 hour).

**Also runs:** Cross-channel correlation scoring on all detected anomalies (same metric +0.4, same direction +0.2, similar severity +0.2, efficiency divergence +0.3). Returns top 5 correlated anomalies into `state["correlated_anomalies"]`.

---

### Detect Anomalies
**File:** `src/nodes/preflight.py` → `detect_anomalies()`

Scans all channels for metric anomalies. If user already selected one from the dashboard, skips auto-detection.

**Detection methods:**
- Windowed Z-Score — Last 3 days vs prior 30 days
- Day-of-Week Seasonality — Compare same weekday historical averages
- Rate-of-Change — 7-day slope detection for gradual trends
- Multi-Metric Correlation — Flags spend↑ + conversions↓ as "efficiency" anomaly

---

### Router
**File:** `src/nodes/router.py` → `route_to_investigator()`

Classifies the anomaly's channel and routes to the right specialist. Rule-based lookup first (fast), falls back to Tier 1 LLM for unknown channels.

**Channel mapping:**
- `paid_media` → google_search, google_pmax, google_display, google_youtube, meta_ads, tiktok_ads, linkedin_ads, programmatic, affiliate
- `influencer` → influencer_campaigns, influencer
- `offline` → direct_mail, tv, radio, ooh, events, podcast

---

### Paid Media Investigator
**File:** `src/nodes/investigators/paid_media.py` → `investigate_paid_media()`
**Model:** Tier 1 (Flash)

Investigates anomalies in Google, Meta, TikTok, LinkedIn, Programmatic, and Affiliate channels. Respects the UI date range for time-travel analysis (lookback capped at 14 days).

**Data fetch sequence:**

| Step | Call | What it returns |
|------|------|-----------------|
| 1 | `marketing.get_channel_performance(channel, days=lookback_days, end_date=analysis_end)` | Daily spend/CPA/ROAS/conversions time-series |
| 2 | `marketing.get_campaign_breakdown(channel, days=lookback_days, end_date=analysis_end)` | Per-campaign spend + conversions |
| 3 | `_get_quality_signals(df, channel)` | IVT/fraud signals for programmatic; coupon/AOV signals for affiliate |
| 4 | `market.get_competitor_signals(channel, reference_date=analysis_end)` | Competitor activity events up to analysis date |
| 5 | `market.get_market_interest(days=analysis_days, end_date=analysis_end)` | Market interest/Google Trends scores |
| 6 | `strategy.get_mmm_guardrails(channel, reference_date=analysis_end)` | MMM saturation point, marginal ROAS, recommendation |
| 7 | `strategy.get_mta_comparison(channel, reference_date=analysis_end)` | Last-click ROAS vs data-driven ROAS |
| 8 | `format_paid_media_prompt(...)` → Tier 1 LLM | Investigation summary string |

**Quality signals (step 3):**
- `programmatic` → IVT rate, suspicious click %, geo anomaly score, new domain % — flags bot traffic if IVT > 20%
- `affiliate` → avg order value, coupon usage rate, unique referral domains — flags coupon leakage if AOV collapses and coupon rate > 70%

**Output:** `investigation_evidence` (dict with all raw data) + `investigation_summary` (LLM text)

---

### Influencer Investigator
**File:** `src/nodes/investigators/influencer.py` → `investigate_influencer()`
**Model:** Tier 1 (Flash)

Investigates anomalies in creator/influencer campaigns. Filters creator posts to the analysis window; uses pandas DataFrame date filtering (not a `days=` API parameter).

**Data fetch sequence:**

| Step | Call | What it returns |
|------|------|-----------------|
| 1 | `influencer.get_campaign_performance()` | All creator posts — then filtered to `analysis_start ≤ post_date ≤ analysis_end` |
| 2 | History slice | Posts strictly before `analysis_start` — used as baseline for comparison |
| 3 | `influencer.get_creator_performance()` | Creator-level engagement/reach metrics |
| 4 | `influencer.get_attribution_analysis(campaign_id)` | MTA lift multiplier, incremental conversion rate, statistical significance |
| 5 | `format_influencer_prompt(...)` → Tier 1 LLM | Investigation summary string |

**Output:** `investigation_evidence` (dict) + `investigation_summary` (LLM text)

---

### Offline Investigator
**File:** `src/nodes/investigators/offline.py` → `investigate_offline()`
**Model:** Tier 1 (Flash)

Handles TV, radio, OOH, events, podcast, direct mail. Same market/strategy data pattern as paid media. Provides channel-specific operational context via `_get_channel_context(channel)`.

**Data fetch sequence:**

| Step | Call | What it returns |
|------|------|-----------------|
| 1 | `marketing.get_channel_performance(channel, days=lookback_days, end_date=analysis_end)` | Channel performance time-series |
| 2 | `market.get_competitor_signals(channel, reference_date=analysis_end)` | Competitor activity |
| 3 | `market.get_market_interest(days=analysis_days, end_date=analysis_end)` | Market trend signals |
| 4 | `strategy.get_mmm_guardrails(channel, reference_date=analysis_end)` | MMM saturation + recommendation |
| 5 | `strategy.get_mta_comparison(channel, reference_date=analysis_end)` | Attribution comparison |
| 6 | `_get_channel_context(channel)` | Channel-specific guidance (Nielsen delays for TV, daypart analysis for radio, promo code tracking for podcast, matchback for direct mail) |
| 7 | `format_offline_prompt(...)` → Tier 1 LLM | Investigation summary string |

**Output:** `investigation_evidence` (dict) + `investigation_summary` (LLM text)

---

### Memory (RAG)
**File:** `src/nodes/memory/retriever.py` → `retrieve_historical_context()`

Queries ChromaDB for similar past incidents. **Temporally filtered** — only returns incidents dated on or before the analysis cutoff, preventing future-data contamination in time-travel mode.

**Cutoff logic:**
```python
cutoff_date_str = (
    state.get("analysis_end_date")          # UI date picker (preferred)
    or anomaly.get("detected_at")           # Anomaly's own date
    or datetime.now().strftime("%Y-%m-%d")  # Fallback: today
)
cutoff_date_int = int(cutoff_date_str.replace("-", ""))  # e.g. 20240315
where_filter = {"date_int": {"$lte": cutoff_date_int}}
```

Falls back to CSV keyword search if embeddings unavailable. CSV fallback also applies the date filter. Returns top 3 matches with similarity scores into `state["historical_incidents"]`.

**Additional functions:**
- `store_resolution()` — Called on action approval. Saves the diagnosis + resolution back to `data/post_mortems/incidents.csv` and ChromaDB (RAG feedback loop). Writes `date_int` field so future queries can filter it.
- `get_recovery_curve()` — Returns avg recovery time from similar historical incidents (`fast` / `medium` / `slow` pattern + `avg_days_to_resolve`). Used by the Impact Simulator in Tab 3.

---

### Explainer
**File:** `src/nodes/explainer/synthesizer.py` → `generate_explanation()`
**Model:** Tier 2 (Pro)

Synthesizes investigation evidence + historical context into a structured diagnosis. Uses `ROOT_CAUSE_ACTION_MAP` to constrain which actions are valid for the diagnosed root cause.

**ROOT_CAUSE_ACTION_MAP:** Maps `root_cause_category` → allowed action keys. The Explainer infers the category from the diagnosis text and sets `diagnosis["allowed_action_keys"]`.

```
auction_pressure    → bid_adjustment, budget_change, notification
tracking_break      → pause, notification, exclusion
creative_fatigue    → creative_refresh, pause, notification
budget_exhaustion   → budget_change, notification
partner_issue       → contract, exclusion, make_good, notification
audience_saturation → exclusion, bid_adjustment, budget_change
seasonal_shift      → schedule_adjustment, bid_adjustment, notification
competitor_action   → bid_adjustment, budget_change, notification
fraud_ivt           → pause, exclusion, partner_issue
unknown             → notification (safe default)
```

**On retry:** Uses `EXPLAINER_RETRY_PROMPT` which includes previous diagnosis + critic's specific feedback. Applies confidence penalty (-5% per retry).

**Output:** `diagnosis` dict including `root_cause_category` and `allowed_action_keys`

---

### Critic (Triple-Lock)
**File:** `src/nodes/critic/validator.py` → `validate_diagnosis()`
**Model:** Tier 2 (Pro)

Three validation checks:
1. **Data Grounding** — Does every claim reference specific data?
2. **Evidence Verification** — Do conclusions follow from evidence?
3. **Hallucination Risk** — Are there claims beyond the provided data?

**Routing after critic:**
- `validation_passed` → Proposer
- Failed + risk ≤ 0.8 + retries left → Retry Explainer (with feedback)
- Failed + risk > 0.8 → END (escalate to human)
- Retries exhausted + risk ≤ 0.8 → Proposer (with warning flag)

---

### Proposer
**File:** `src/nodes/proposer/action_mapper.py` → `propose_actions()`
**Model:** Tier 1 (Flash)

Maps diagnosis to action payloads. Primary: Tier 1 LLM selects 1–3 templates from the action library, filtered to `allowed_action_keys` from the diagnosis. Fallback: keyword pattern matching.

**MMM Guardrail (`_apply_guardrails()`):** After actions are selected, checks MMM data. If `marginal_roas < 1.0` or `recommendation == "maintain"`, any `budget_increase` action is replaced with a `manual_review` action. This prevents recommending increased spend on a channel already losing money per dollar spent.

**Action templates:** bid_adjustment, budget_change, pause, notification, exclusion, contract, make_good, schedule_adjustment, partner_issue

---

## Time-Travel Analysis

The UI has a date range picker in the sidebar. Here's how it flows through the system:

```
User selects dates in Streamlit sidebar
  ↓
state["analysis_start_date"] = "2024-01-15"
state["analysis_end_date"]   = "2024-02-14"
  ↓
All 3 investigators:
  - Extract these from state
  - Compute lookback_days = min((end - start).days, 14)
  - Pass end_date=analysis_end to every data fetch call
  - Filter creator posts by date for influencer
  ↓
Memory (RAG):
  - cutoff_date_int = int("20240214")
  - ChromaDB where={"date_int": {"$lte": 20240214}}
  - Incidents after Feb 14 are invisible to this query
  ↓
Strategy layer:
  - get_mmm_guardrails(channel, reference_date=analysis_end)
  - get_mta_comparison(channel, reference_date=analysis_end)
  - Returns data as it looked on that date
```

This means you can analyze any historical anomaly and get exactly the data, context, and incidents that were available at that time — no future leakage.

---

## Feedback & Audit System
**File:** `src/feedback/__init__.py`

Two persistent logging functions, called from `app.py` Tab 3 (Actions):

| Function | When called | Output |
|----------|-------------|--------|
| `log_feedback(anomaly, diagnosis, sentiment)` | Thumbs 👍/👎 on diagnosis | `data/feedback/feedback_log.csv` |
| `log_action_decision(anomaly, diagnosis, action, decision)` | Approve ✅ or Reject ❌ on action | `data/audit/action_decisions.csv` |

On **Approve**: also calls `store_resolution()` (RAG feedback loop) and sends a Slack notification via `src/notifications/slack.py`.

On **Reject**: calls `log_action_decision()` locally and sends a Slack rejection notification.

---

## Dashboard Tab → Code Map

| Tab | Label | What it does |
|-----|-------|-------------|
| Tab 1 | Diagnosis | Renders `diagnosis` dict in 4 persona views (Executive / Director / Marketer / Data Scientist). Shows confidence score, supporting evidence, critic retry count, and thumbs 👍/👎 feedback buttons. |
| Tab 2 | Market & Strategy | Calls `load_data_sources()` once → renders competitor signals table, MTA attribution comparison, MMM saturation chart, market interest trend. All data bounded to the analysis date range. |
| Tab 3 | Actions | Renders each proposed action card. Calls `render_impact_simulation()` → `get_recovery_curve()` for historical-data-based projections → Approve/Reject buttons → `store_resolution()` + `log_action_decision()` + Slack. |
| Tab 4 | Deep Dive | Shows RAG historical incidents (filtered to cutoff), cross-channel correlation context, raw investigation evidence. |
| Tab 5 | Assistant | Chat interface using `get_llm_safe("tier2")`, `MAX_CHAT_TURNS=10`, maintains multi-turn system context including diagnosis and anomaly. |

---

## State Schema

```python
class ExpeditionState(TypedDict):
    messages: Annotated[list, add_messages]

    # Pre-Flight
    data_freshness: dict | None
    preflight_passed: bool
    preflight_error: str | None

    # Detection
    anomalies: list[dict]
    selected_anomaly: dict | None
    correlated_anomalies: list[dict]

    # Analysis Date Range (from UI date picker — enables time-travel)
    analysis_start_date: str | None    # "YYYY-MM-DD"
    analysis_end_date: str | None      # "YYYY-MM-DD"

    # Investigation
    channel_category: str | None       # "paid_media" | "influencer" | "offline"
    investigation_evidence: dict | None
    investigation_summary: str | None

    # Memory
    historical_incidents: list[dict]
    rag_context: str | None

    # Diagnosis
    diagnosis: dict | None

    # Critic
    critic_validation: dict | None
    validation_passed: bool
    critic_retry_count: int
    critic_feedback: str | None

    # Actions
    proposed_actions: list[dict]
    selected_action: dict | None
    human_approved: bool
    execution_result: dict | None

    # Meta
    current_node: str
    error: str | None
    run_id: str | None
```

---

## Data Contracts

### Anomaly

```python
{
    "channel": "google_search",
    "metric": "cpa",
    "current_value": 85.50,
    "expected_value": 45.00,
    "deviation_pct": 90.0,
    "z_score": 3.2,
    "severity": "high",           # low | medium | high | critical
    "direction": "spike",         # spike | drop
    "detection_method": "windowed_zscore",
    "detected_at": "2026-03-01",
    "_id": "google_search_cpa_spike",
}
```

### Diagnosis

```python
{
    "root_cause": "Competitor aggressive bidding on brand terms",
    "root_cause_category": "auction_pressure",       # used by Proposer to filter actions
    "allowed_action_keys": ["bid_adjustment", "budget_change", "notification"],
    "confidence": 0.82,
    "supporting_evidence": ["CPC increased 40%", "Impression share dropped to 62%"],
    "recommended_actions": ["Increase brand bids by 20%", "File trademark complaint"],
    "executive_summary": "A competitor is bidding on our brand...",
    "technical_details": "Z-score analysis shows CPA deviation of 3.2σ...",
}
```

### Action Payload

```python
{
    "action_id": "ACT-2026-abc123",
    "action_type": "bid_adjustment",
    "platform": "google_ads",
    "operation": "increase",
    "parameters": {"adjustment_pct": 20},
    "estimated_impact": "Regain impression share within 24-48 hours",
    "risk_level": "medium",        # low | medium | high
    "requires_approval": True,
}
```

---

## Issues Resolved During Development

| Issue | Cause | Fix |
|-------|-------|-----|
| Empty credentials path bug | `Path("")` returns True for `.exists()` | Explicit `_has_gcp_credentials()` check |
| Missing `get_llm_safe` | Lost during file edits | Re-added to `models.py` |
| ChromaDB embedding download blocked | Network restriction | Added `SimpleHashEmbedding` fallback |
| Influencer CSV parse error | Column name mismatch | Changed `post_date` to `date` |
| LLM returning None | Missing error handling | Added try/except + MockLLM fallback |
| Critic always proceeding | No retry mechanism | Added critic retry loop (max 2x) |
| Budget increase on saturated channel | No MMM check in Proposer | Restored `_apply_guardrails()` in `action_mapper.py` |
| Wrong actions for root cause (e.g. budget change for tracking break) | No action type constraint | Restored `ROOT_CAUSE_ACTION_MAP` in Explainer + Proposer filter |
| Time-travel date picker had no effect | Investigators fetched current data | Restored date range extraction + `end_date=` param in all 3 investigators |
| RAG returning future incidents | No temporal filter in ChromaDB query | Restored `where={"date_int": {"$lte": cutoff}}` in `retriever.py` |
| Impact simulator ignored historical recovery data | `get_recovery_curve()` not called | Restored call in `render_impact_simulation()` in `app.py` |
| Slack not notified on action reject | Regression in V7 | Restored Slack reject notification in `app.py` Tab 3 |
