# 🗺️ Expedition Flow

**How the agent works, node by node.**

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
                                     │         ├── ✅ Pass ──→ Proposer ──→ END
                                     │         ├── ⚠️ Retry ──→ Prepare Feedback ──┘
                                     │         └── 🛑 High Risk ──→ END (escalate)
                                     │
                                     └── Retry Loop (max 2x)
```

## How It Works (User Flow)

1. `make run` → Starts Streamlit on localhost:8501
2. Dashboard loads → Shows detected anomalies across all channels
3. User clicks **Investigate** on an anomaly
4. LangGraph executes the full pipeline:
   - **preflight** → Validates data freshness
   - **detect** → Finds anomalies, selects highest severity, correlates across channels
   - **router** → Routes to paid_media, influencer, or offline investigator
   - **investigator** → Gathers evidence, calls LLM for analysis
   - **memory** → RAG search for similar historical incidents
   - **explainer** → LLM synthesizes diagnosis with multi-persona explanations
   - **critic** → Triple-Lock validation (if fails, loops back to explainer with feedback)
   - **proposer** → LLM maps diagnosis to executable action payloads
5. Results displayed in Diagnosis / Deep Dive / Actions / Assistant tabs

## Node Reference

### Pre-Flight Check
**File:** `src/nodes/preflight.py` → `preflight_check()`

Validates data freshness before investigation. Prevents diagnosing noise from stale pipelines. In mock mode, always passes. In production, checks BigQuery last-refresh timestamps against `MAX_DATA_LATENCY_HOURS` (1 hour).

**Also runs:** Cross-channel correlation scoring (same metric +0.4, same direction +0.2, similar severity +0.2, efficiency divergence +0.3). Returns top 5 correlated anomalies.

### Detect Anomalies
**File:** `src/nodes/preflight.py` → `detect_anomalies()`

Scans all channels for metric anomalies. If user already selected one from the dashboard, skips auto-detection.

**Detection methods:**
- Windowed Z-Score — Last 3 days vs prior 30 days
- Day-of-Week Seasonality — Compare same weekday historical averages
- Rate-of-Change — 7-day slope detection for gradual trends
- Multi-Metric Correlation — Flags spend↑ + conversions↓ as "efficiency" anomaly

### Router
**File:** `src/nodes/router.py` → `route_to_investigator()`

Classifies the anomaly's channel and routes to the right specialist. Rule-based lookup first (fast), falls back to Tier 1 LLM for unknown channels.

**Channel mapping:**
- `paid_media` → google_search, google_pmax, google_display, google_youtube, meta_ads, tiktok_ads, linkedin_ads, programmatic, affiliate
- `influencer` → influencer_campaigns, influencer
- `offline` → direct_mail, tv, radio, ooh, events, podcast

### Paid Media Investigator
**File:** `src/nodes/investigators/paid_media.py`

Gathers channel performance (90 days), campaign breakdown, cross-channel correlation context. Calls Tier 2 LLM to analyze root causes.

### Influencer Investigator
**File:** `src/nodes/investigators/influencer.py`

Gathers creator performance, campaign metrics, engagement patterns, correlation context. Calls Tier 2 LLM for causal analysis.

### Offline Investigator
**File:** `src/nodes/investigators/offline.py`

Handles TV, radio, OOH, events, podcast, direct mail. Provides channel-specific context (Nielsen delays for TV, daypart analysis for radio, promo code tracking for podcast, matchback for direct mail).

### Memory (RAG)
**File:** `src/nodes/memory/retriever.py` → `retrieve_historical_context()`

Queries ChromaDB for similar past incidents. Falls back to CSV keyword search if embeddings unavailable. Returns top 3 matches with similarity scores.

**Additional functions:**
- `store_resolution()` — Saves approved diagnoses back to incidents.csv + ChromaDB (RAG feedback loop)
- `get_recovery_curve()` — Returns avg recovery time from similar historical incidents (used by Impact Simulator)

### Explainer
**File:** `src/nodes/explainer/synthesizer.py` → `generate_explanation()`

Synthesizes investigation evidence + historical context into a diagnosis. Uses Tier 2 LLM.

**On retry:** Uses `EXPLAINER_RETRY_PROMPT` which includes previous diagnosis + critic's specific feedback. Applies confidence penalty (-5% per retry).

### Critic (Triple-Lock)
**File:** `src/nodes/critic/validator.py` → `validate_diagnosis()`

Three validation checks:
1. **Data Grounding** — Does every claim reference specific data?
2. **Evidence Verification** — Do conclusions follow from evidence?
3. **Hallucination Risk** — Are there claims beyond the provided data?

**Routing after critic:**
- `validation_passed` → Proposer
- Failed + risk ≤ 0.8 + retries left → Retry Explainer (with feedback)
- Failed + risk > 0.8 → END (escalate to human)
- Retries exhausted + risk ≤ 0.8 → Proposer (with warning)

### Proposer
**File:** `src/nodes/proposer/action_mapper.py` → `propose_actions()`

Maps diagnosis to action payloads. Primary: LLM selects 1-3 templates from the action library. Fallback: keyword pattern matching.

**Action templates:** bid_adjustment, budget_change, pause, notification, exclusion, contract, make_good, schedule_adjustment, partner_issue

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
    "detected_at": "2026-03-01T...",
    "_id": "google_search_cpa_spike",
}
```

### Diagnosis

```python
{
    "root_cause": "Competitor aggressive bidding on brand terms",
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

## Issues Resolved During Development

| Issue | Cause | Fix |
|-------|-------|-----|
| Empty credentials path bug | `Path("")` returns True for `.exists()` | Explicit `_has_gcp_credentials()` check |
| Missing `get_llm_safe` | Lost during file edits | Re-added to `models.py` |
| ChromaDB embedding download blocked | Network restriction | Added `SimpleHashEmbedding` fallback |
| Influencer CSV parse error | Column name mismatch | Changed `post_date` to `date` |
| LLM returning None | Missing error handling | Added try/except + MockLLM fallback |
| Critic always proceeding | No retry mechanism | Added critic retry loop (max 2x) |