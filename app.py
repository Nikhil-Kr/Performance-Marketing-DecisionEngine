"""
Project Expedition - Decision Cockpit (Tier 4)
Includes: Competitor Intel, Market Trends, MMM/MTA, Impact Simulator, Chat.

FIXES APPLIED:
1. Dynamic date filtering (auto-rescans when dates change)
2. Investigation state retention (proper cache key management)
3. Unique projection charts per anomaly (uses actual data)
4. Improved MMM/MTA data display
"""
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import sys
from pathlib import Path
import hashlib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Intelligence Layer for Chat
try:
    from src.intelligence.models import get_llm_safe
except ImportError:
    get_llm_safe = None

# Page configuration
st.set_page_config(
    page_title="Expedition | Decision Cockpit",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .metric-card {
        background-color: #1A1F2C;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #30363D;
    }
    .severity-critical { color: #FF4B4B; font-weight: bold; }
    .severity-high { color: #FFA500; font-weight: bold; }
    .severity-medium { color: #FFD700; }
    .severity-low { color: #90EE90; }
    
    /* Improve button visibility */
    .stButton button {
        width: 100%;
        border-radius: 5px;
    }
    
    /* Logo styling */
    .channel-logo {
        border-radius: 50%;
        padding: 2px;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Constants & Config
# ============================================================================

CHANNEL_LOGOS = {
    "google": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_%22G%22_logo.svg/120px-Google_%22G%22_logo.svg.png",
    "meta": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Facebook_Logo_%282019%29.png/600px-Facebook_Logo_%282019%29.png",
    "tiktok": "https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/TikTok_logo.svg/120px-TikTok_logo.svg.png",
    "linkedin": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/LinkedIn_logo_initials.png/120px-LinkedIn_logo_initials.png",
    "youtube": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/120px-YouTube_full-color_icon_%282017%29.svg.png",
    "tv": "https://cdn-icons-png.flaticon.com/512/716/716429.png", 
    "podcast": "https://cdn-icons-png.flaticon.com/512/2368/2368447.png",
    "radio": "https://cdn-icons-png.flaticon.com/512/2058/2058142.png", 
    "affiliate": "https://cdn-icons-png.flaticon.com/512/1150/1150626.png", 
    "programmatic": "https://cdn-icons-png.flaticon.com/512/2103/2103601.png",
    "influencer": "https://cdn-icons-png.flaticon.com/512/1458/1458201.png",
    "default": "https://cdn-icons-png.flaticon.com/512/1055/1055644.png"
}

# ============================================================================
# Session State Initialization
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "anomalies": [],
        "last_scan_time": None,
        "selected_anomaly_id": None,
        "investigation_result": None,
        "investigation_cache": {},
        "chat_history": [],
        "action_states": {},
        "view_mode": "dashboard",
        # FIX: Persistent date range - stored as tuple of date objects
        "selected_start_date": (datetime.now() - timedelta(days=30)).date(),
        "selected_end_date": datetime.now().date(),
        # Track if we need to rescan (date changed)
        "needs_rescan": False,
        "last_scanned_dates": None,  # Track what dates were last scanned
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()


# ============================================================================
# Helper Functions
# ============================================================================

def load_data_sources(force_refresh=False):
    """Load all data sources including Tier 3/4 connectors."""
    try:
        from src.data_layer import get_marketing_data, get_influencer_data, get_market_data, get_strategy_data, clear_cache
        if force_refresh:
            clear_cache()
        return get_marketing_data(), get_influencer_data(), get_market_data(), get_strategy_data()
    except Exception as e:
        st.error(f"Failed to load data sources: {e}")
        return None, None, None, None

def get_severity_color(severity):
    colors = {"critical": "#FF4B4B", "high": "#FFA500", "medium": "#FFD700", "low": "#90EE90"}
    return colors.get(severity.lower(), "#FFFFFF")

def get_channel_logo(channel_name):
    name = channel_name.lower()
    for key, url in CHANNEL_LOGOS.items():
        if key in name:
            return url
    return CHANNEL_LOGOS["default"]

def get_cache_key(anomaly_id: str, start_date, end_date) -> str:
    """Generate a stable cache key that includes date range."""
    start_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
    end_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
    return f"{anomaly_id}_{start_str}_{end_str}"

def get_current_date_range():
    """Get the currently selected date range from session state."""
    start = st.session_state.selected_start_date
    end = st.session_state.selected_end_date
    # Convert to datetime if needed
    if hasattr(start, 'strftime') and not hasattr(start, 'hour'):
        start = datetime.combine(start, datetime.min.time())
    if hasattr(end, 'strftime') and not hasattr(end, 'hour'):
        end = datetime.combine(end, datetime.min.time())
    return start, end

def scan_anomalies():
    """Scan for anomalies with current date range. Returns True if successful."""
    start_dt, end_dt = get_current_date_range()
    
    m, i, _, _ = load_data_sources(force_refresh=True)
    if m and i:
        anoms = (
            m.get_anomalies(start_date=start_dt, end_date=end_dt) + 
            i.get_anomalies(start_date=start_dt, end_date=end_dt)
        )
        
        # Create stable ID that includes date context
        for a in anoms:
            a['_id'] = f"{a['channel']}_{a['metric']}_{a.get('detected_at')}"
            
        st.session_state.anomalies = anoms
        st.session_state.last_scan_time = datetime.now()
        st.session_state.last_scanned_dates = (
            st.session_state.selected_start_date,
            st.session_state.selected_end_date
        )
        st.session_state.needs_rescan = False
        # Clear investigation cache when dates change
        st.session_state.investigation_cache = {}
        st.session_state.investigation_result = None
        return True
    return False

def on_date_change():
    """Callback when date range changes."""
    st.session_state.needs_rescan = True

def render_trend_chart(df, metric, date_range=None, severity="low"):
    """Render a detailed trend chart using Altair."""
    if df.empty or metric not in df.columns:
        return None
    
    chart_df = df.copy()
    
    # Filter by date if provided
    if date_range and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        chart_df = chart_df[
            (pd.to_datetime(chart_df['date']) >= start_date) & 
            (pd.to_datetime(chart_df['date']) <= end_date)
        ]

    if chart_df.empty:
        return None

    color = get_severity_color(severity)
    
    chart = alt.Chart(chart_df).mark_area(
        line={'color': color, 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color=color, offset=0),
                   alt.GradientStop(color='rgba(255, 255, 255, 0.1)', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('date:T', title='Date', axis=alt.Axis(format='%b %d, %Y', grid=False, domain=False)),
        y=alt.Y(f'{metric}:Q', title=metric.replace('_', ' ').title(), axis=alt.Axis(grid=True, domain=False)),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip(f'{metric}:Q', title=metric.replace('_', ' ').title(), format=',.2f')
        ]
    ).properties(height=150, width='container').interactive()

    return chart

def render_market_trends_overlay(df_channel, df_trends, metric):
    """Render channel performance overlaid with market interest (Google Trends)."""
    if df_channel.empty or df_trends.empty:
        return None
    
    # Channel performance line (blue solid)
    line1 = alt.Chart(df_channel).mark_line(color='#4A90E2', strokeWidth=2).encode(
        x=alt.X('date:T', title='Date', axis=alt.Axis(format='%b %d, %Y')),
        y=alt.Y(f'{metric}:Q', axis=alt.Axis(title=f'Channel {metric.upper()}', titleColor='#4A90E2')),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip(f'{metric}:Q', title=metric.upper(), format=',.2f')
        ]
    )
    
    # Market interest line (gray dashed)
    line2 = alt.Chart(df_trends).mark_line(color='#888888', strokeDash=[5, 5], strokeWidth=1.5).encode(
        x=alt.X('date:T'),
        y=alt.Y('interest_score:Q', axis=alt.Axis(title='Google Trends Index (0-100)', titleColor='#888888')),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('interest_score:Q', title='Search Interest', format='.0f')
        ]
    )
    
    chart = alt.layer(line1, line2).resolve_scale(y='independent').properties(
        height=220, 
        width='container', 
        title=alt.TitleParams(
            text=f"Channel Performance vs. Market Demand",
            subtitle=f"Blue = {metric.upper()} performance | Gray dashed = Google Trends search interest"
        )
    )
    
    return chart

def render_mta_chart(mta_data):
    """Render comparison between Last Click and Multi-Touch Attribution ROAS."""
    if not mta_data or mta_data.get("last_click_roas", 0) == 0:
        return None
    
    lc_roas = mta_data.get("last_click_roas", 0)
    mta_roas = mta_data.get("data_driven_roas", 0)
    
    data = pd.DataFrame([
        {"Model": "Last-Click", "ROAS": lc_roas, "Description": "Credits only the final touchpoint"},
        {"Model": "Multi-Touch (MTA)", "ROAS": mta_roas, "Description": "Credits all touchpoints in journey"}
    ])
    
    # Determine which bar should be highlighted
    colors = ['#5c5c5c', '#00D26A'] if mta_roas >= lc_roas else ['#00D26A', '#5c5c5c']
    
    chart = alt.Chart(data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X('Model:N', axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y('ROAS:Q', title='Return on Ad Spend (ROAS)'),
        color=alt.Color('Model:N', scale=alt.Scale(range=colors), legend=None),
        tooltip=[
            alt.Tooltip('Model:N', title='Attribution Model'),
            alt.Tooltip('ROAS:Q', title='ROAS', format='.2f'),
            alt.Tooltip('Description:N', title='How it works')
        ]
    ).properties(
        height=200,
        width='container',
        title=alt.TitleParams(
            text="Attribution Model Comparison",
            subtitle="How much credit does this channel deserve? Last-Click often under/over-values channels."
        )
    )
    return chart

def render_impact_simulation(anomaly: dict, historical_df: pd.DataFrame, reference_date: datetime):
    """
    Render Impact Simulator with nonlinear recovery dynamics + reliable hover tooltips.

    Fixes included:
    - Flat-line projections (handled by dynamics + severity scaling)
    - Nonlinear action recovery (exponential)
    - Reliable tooltip hover (explicit point layer + nearest selection + rule)
    - Pan/zoom interactivity retained (.interactive())

    NOTE: This function expects hashlib, numpy as np, pandas as pd, altair as alt to be imported.
    """

    metric = anomaly.get('metric', 'cpa').lower()
    channel = anomaly.get('channel', 'unknown')
    direction = anomaly.get('direction', 'spike')
    severity = anomaly.get('severity', 'medium')

    current_value = anomaly.get('current_value')
    expected_value = anomaly.get('expected_value')

    # -----------------------------
    # 1) Establish baseline anchor
    # -----------------------------
    try:
        start_val = float(current_value)
    except Exception:
        start_val = None

    if (start_val is None or start_val <= 0) and not historical_df.empty and metric in historical_df.columns:
        try:
            start_val = float(historical_df[metric].iloc[-1])
        except Exception:
            start_val = None

    if start_val is None or start_val <= 0:
        defaults = {
            "cpa": 50,
            "cpc": 2,
            "roas": 3,
            "ctr": 0.02,
            "spend": 1000,
            "conversions": 100,
        }
        start_val = defaults.get(metric, 100)

    try:
        expected_val = float(expected_value)
    except Exception:
        expected_val = start_val * (0.9 if direction == "spike" else 1.1)

    # --------------------------------
    # 2) Severity-based recovery speed
    # --------------------------------
    severity_map = {
        "critical": 0.55,
        "high": 0.40,
        "medium": 0.25,
        "low": 0.15,
    }
    recovery_strength = severity_map.get(severity, 0.25)

    # --------------------------------
    # 3) Define target (anchored)
    # --------------------------------
    target_val = expected_val

    # --------------------------------
    # 4) Time axis
    # --------------------------------
    base_date = reference_date if reference_date else datetime.now()
    days = 7
    dates = [base_date + timedelta(days=i) for i in range(days + 1)]

    # --------------------------------
    # 5) Nonlinear dynamics
    # --------------------------------
    baseline_vals = []
    action_vals = []

    # deterministic but unique per anomaly
    seed = int(hashlib.md5(f"{channel}_{metric}_{severity}_{direction}".encode()).hexdigest()[:8], 16) % (2**31)
    np.random.seed(seed)

    for t in range(days + 1):
        # Baseline: drift away (worse)
        drift_factor = 1 + (0.02 * t) if direction == "spike" else 1 - (0.02 * t)
        baseline_val = start_val * drift_factor

        # Action: exponential recovery to target
        decay = np.exp(-recovery_strength * t)
        action_val = target_val + (start_val - target_val) * decay

        # Directional noise scaled to "problem size"
        noise_scale = abs(start_val - target_val) * 0.05
        noise = np.random.randn() * noise_scale

        baseline_vals.append(max(0.01, baseline_val + noise * 0.3))
        action_vals.append(max(0.01, action_val + noise))

    np.random.seed(None)

    # --------------------------------
    # 6) Build dataframe (tooltip-friendly types)
    # --------------------------------
    df_sim = pd.concat(
        [
            pd.DataFrame({"date": pd.to_datetime(dates), "value": baseline_vals, "scenario": "Do Nothing (Baseline)"}),
            pd.DataFrame({"date": pd.to_datetime(dates), "value": action_vals, "scenario": "With Action (Projected)"}),
        ],
        ignore_index=True,
    )

    # --------------------------------
    # 7) Hover selection + layered chart
    # --------------------------------

    # Nearest-point selection on hover (reliable tooltip trigger)
    hover = alt.selection_point(
        fields=["date", "scenario"],
        nearest=True,
        on="mouseover",
        empty=False,
        clear="mouseout",
    )

    color_scale = alt.Scale(
        domain=["Do Nothing (Baseline)", "With Action (Projected)"],
        range=["#FF4B4B", "#00D26A"],
    )

    base = alt.Chart(df_sim).encode(
        x=alt.X("date:T", title="Forecast Date", axis=alt.Axis(format="%b %d, %Y")),
        y=alt.Y("value:Q", title=f"Projected {metric.upper()}", scale=alt.Scale(zero=False)),
        color=alt.Color("scenario:N", scale=color_scale, legend=alt.Legend(title="Scenario", orient="bottom")),
    )

    # Line layer (main)
    lines = base.mark_line(strokeWidth=2).encode(
        strokeDash=alt.condition(
            alt.datum.scenario == "Do Nothing (Baseline)",
            alt.value([6, 4]),
            alt.value([0]),
        )
    )

    # Points layer (tooltip reliably binds here)
    points = base.mark_point(size=70, filled=True).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0.15)),
        tooltip=[
            alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("scenario:N", title="Scenario"),
            alt.Tooltip("value:Q", title=metric.upper(), format=",.2f"),
        ],
    ).add_params(hover)

    # Vertical rule at hovered date (nice UX)
    rule = alt.Chart(df_sim).mark_rule(opacity=0.35).encode(
        x="date:T",
    ).transform_filter(hover)

    chart = (lines + points + rule).properties(
        height=240,
        width="container",
        title=alt.TitleParams(
            text=f"7-Day Impact Forecast — {channel.replace('_', ' ').title()}",
            subtitle=f"Severity: {severity.upper()} | Nonlinear recovery with intervention",
        ),
    ).interactive()

    return chart



# ============================================================================
# Main Content
# ============================================================================

col1, col2 = st.columns([3, 1])
with col1:
    st.title("🧭 Expedition Decision Cockpit")
with col2:
    if st.session_state.view_mode == "investigation":
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.view_mode = "dashboard"
            st.rerun()

st.divider()

# --- DASHBOARD VIEW ---
if st.session_state.view_mode == "dashboard":
    
    with st.expander("🎛️ Filters & Controls", expanded=True):
        c_scan, c_date, c_sev, c_chan = st.columns([1, 2, 2, 2])
        
        # FIX: Use session state for date persistence
        with c_date:
            date_range = st.date_input(
                "Analysis Period",
                value=(
                    st.session_state.selected_start_date,
                    st.session_state.selected_end_date
                ),
                format="MM/DD/YYYY",
                key="date_picker"
            )
            
            # Update session state when date changes
            if isinstance(date_range, tuple) and len(date_range) == 2:
                new_start, new_end = date_range
                if (new_start != st.session_state.selected_start_date or 
                    new_end != st.session_state.selected_end_date):
                    st.session_state.selected_start_date = new_start
                    st.session_state.selected_end_date = new_end
                    st.session_state.needs_rescan = True
            
        with c_sev:
            severity_filter = st.multiselect(
                "Severity",
                ["critical", "high", "medium", "low"],
                default=["critical", "high", "medium", "low"]
            )
            
        with c_chan:
            available = sorted(list(set(a['channel'] for a in st.session_state.anomalies))) if st.session_state.anomalies else []
            channel_filter = st.multiselect("Channel", available, default=available)

        with c_scan:
            st.write("") 
            st.write("") 
            
            # Show different button states
            if st.session_state.needs_rescan and st.session_state.anomalies:
                btn_label = "🔄 Rescan (Dates Changed)"
                btn_help = "Date range changed - click to rescan"
            else:
                btn_label = "📡 Scan Now"
                btn_help = "Scan for anomalies in selected date range"
            
            if st.button(btn_label, type="primary", help=btn_help):
                start_dt, end_dt = get_current_date_range()
                with st.spinner(f"Scanning {st.session_state.selected_start_date} to {st.session_state.selected_end_date}..."):
                    if scan_anomalies():
                        st.rerun()
                    else:
                        st.error("Failed to scan. Check data sources.")

    # FIX: Show warning if dates changed but not rescanned
    if st.session_state.needs_rescan and st.session_state.anomalies:
        st.warning("⚠️ Date range changed. Click 'Rescan' to update anomalies.")

    if not st.session_state.anomalies:
        st.info("👋 Welcome! Click 'Scan Now' to detect anomalies in the selected date range.")
    else:
        # Filter anomalies by severity and channel
        filtered = [
            a for a in st.session_state.anomalies 
            if a['severity'] in severity_filter and (not channel_filter or a['channel'] in channel_filter)
        ]
        
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Anomalies", len(st.session_state.anomalies))
        c2.metric("Critical", len([a for a in st.session_state.anomalies if a['severity'] == 'critical']))
        c3.metric("High", len([a for a in st.session_state.anomalies if a['severity'] == 'high']))
        c4.metric("Showing", len(filtered))
        
        # Show current analysis period (from last scan, not current picker)
        if st.session_state.last_scanned_dates:
            start_d, end_d = st.session_state.last_scanned_dates
            st.caption(f"📅 Scanned Period: {start_d} to {end_d}")
        
        st.markdown("### 🚨 Detected Anomalies")
        
        for i, anomaly in enumerate(filtered):
            with st.container():
                c_status, c_logo, c_detail, c_chart, c_action = st.columns([0.15, 0.5, 2, 3, 1])
                
                with c_status:
                    color = get_severity_color(anomaly['severity'])
                    st.markdown(f"""
                    <div style="
                        height: 140px; 
                        width: 6px; 
                        background-color: {color}; 
                        border-radius: 5px;">
                    </div>
                    """, unsafe_allow_html=True)
                
                with c_logo:
                    st.image(get_channel_logo(anomaly['channel']), width=50)
                
                with c_detail:
                    st.markdown(f"**{anomaly['channel'].replace('_', ' ').title()}**")
                    st.markdown(f"Metric: **{anomaly['metric'].replace('_', ' ').title()}**")
                    
                    delta_color = "inverse" if anomaly['direction'] == "spike" else "normal" 
                    st.metric(
                        "Deviation", 
                        f"{anomaly['current_value']}", 
                        f"{anomaly['deviation_pct']}%",
                        delta_color=delta_color
                    )
                    
                    st.markdown(f"Severity: <span style='color:{color}; font-weight:bold'>{anomaly['severity'].upper()}</span>", unsafe_allow_html=True)

                with c_chart:
                    marketing, influencer, _, _ = load_data_sources()
                    if "influencer" in anomaly['channel']:
                        df_hist = pd.DataFrame() 
                    else:
                        # FIX: Use stored date range from session state
                        start_dt, end_dt = get_current_date_range()
                        df_hist = marketing.get_channel_performance(
                            anomaly['channel'], 
                            days=90,
                            end_date=end_dt
                        )
                    
                    # Use session state dates for chart filtering
                    chart_date_range = (
                        st.session_state.selected_start_date,
                        st.session_state.selected_end_date
                    )
                    chart = render_trend_chart(df_hist, anomaly['metric'], chart_date_range, anomaly['severity'])
                    if chart:
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.caption("No trend data available for this period")

                with c_action:
                    st.write("") 
                    st.write("")
                    
                    # FIX: Use stored session state dates for cache key (consistent)
                    cache_key = get_cache_key(
                        anomaly['_id'], 
                        st.session_state.selected_start_date,
                        st.session_state.selected_end_date
                    )
                    
                    is_cached = cache_key in st.session_state.investigation_cache
                    btn_label = "📂 View Report" if is_cached else "🕵️‍♂️ Investigate"
                    btn_type = "secondary" if is_cached else "primary"
                    
                    if st.button(btn_label, key=f"inv_{i}", type=btn_type):
                        if st.session_state.selected_anomaly_id != anomaly['_id']:
                            st.session_state.chat_history = [{"role": "assistant", "content": f"I'm analyzing {anomaly['channel']}. Ask me anything!"}]
                        
                        st.session_state.selected_anomaly_id = anomaly['_id']
                        
                        if is_cached:
                            st.session_state.investigation_result = st.session_state.investigation_cache[cache_key]
                            st.session_state.view_mode = "investigation"
                            st.rerun()
                        else:
                            with st.spinner(f"🔍 Investigating {anomaly['channel']}..."):
                                from src.graph import run_expedition
                                
                                start_dt, end_dt = get_current_date_range()
                                
                                initial_state = {
                                    "selected_anomaly": anomaly, 
                                    "anomalies": [anomaly],
                                    "analysis_start_date": start_dt.strftime("%Y-%m-%d"),
                                    "analysis_end_date": end_dt.strftime("%Y-%m-%d"),
                                }
                                
                                result = run_expedition(initial_state)
                                st.session_state.investigation_cache[cache_key] = result
                                st.session_state.investigation_result = result
                                st.session_state.view_mode = "investigation"
                                st.rerun()
                st.divider()

# --- INVESTIGATION VIEW ---
elif st.session_state.view_mode == "investigation":
    
    result = st.session_state.investigation_result
    if not result:
        st.error("Investigation failed to load.")
        st.stop()
        
    anomaly = result.get("selected_anomaly", {})

    c_back_logo, c_back_title, c_rerun = st.columns([0.5, 8, 2])
    with c_back_logo: st.image(get_channel_logo(anomaly.get('channel', '')), width=50)
    with c_back_title: st.header(f"Investigation: {anomaly.get('channel', 'Unknown').replace('_', ' ').title()}")
    with c_rerun:
        st.write("")
        if st.button("🔄 Re-analyze", help="Force a fresh investigation (clears cache)"):
            cache_key = get_cache_key(
                anomaly.get('_id', ''),
                st.session_state.selected_start_date,
                st.session_state.selected_end_date
            )
            
            if cache_key in st.session_state.investigation_cache:
                del st.session_state.investigation_cache[cache_key]
            
            with st.spinner("Re-running analysis..."):
                from src.graph import run_expedition
                
                start_dt, end_dt = get_current_date_range()
                
                initial_state = {
                    "selected_anomaly": anomaly, 
                    "anomalies": [anomaly],
                    "analysis_start_date": start_dt.strftime("%Y-%m-%d"),
                    "analysis_end_date": end_dt.strftime("%Y-%m-%d"),
                }
                
                result = run_expedition(initial_state)
                st.session_state.investigation_cache[cache_key] = result
                st.session_state.investigation_result = result
                st.rerun()
    
    st.markdown(f"**Issue:** {anomaly.get('metric')} {anomaly.get('direction')} by {anomaly.get('deviation_pct')}%")
    
    # Show analysis period context
    st.caption(f"📅 Analysis Period: {st.session_state.selected_start_date} to {st.session_state.selected_end_date}")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Diagnosis", "🌐 Market & Strategy", "⚡ Actions", "💬 Assistant"])
    
    # TAB 1: DIAGNOSIS
    with tab1:
        diagnosis = result.get("diagnosis", {})
        validation = result.get("critic_validation", {})
        
        if result.get("validation_passed"):
            st.success(f"✅ Verified Analysis (Risk: {validation.get('hallucination_risk', 0):.0%})")
        else:
            st.warning(f"⚠️ Low Confidence (Risk: {validation.get('hallucination_risk', 0):.0%})")
            with st.expander("Validation Issues"):
                for issue in validation.get("issues", []): st.markdown(f"- {issue}")

        col_main, col_summary = st.columns([2, 1])
        with col_main:
            st.subheader("🎯 Root Cause")
            st.info(diagnosis.get("root_cause", "Analysis pending..."))
            st.subheader("📊 Evidence")
            for item in diagnosis.get("supporting_evidence", []): st.markdown(f"- {item}")

        with col_summary:
            st.subheader("Executive Summary")
            st.markdown(f"_{diagnosis.get('executive_summary', 'No summary available')}_")
            st.divider()
            persona = st.selectbox("View Explanation For:", ["Director", "Marketer", "Data Scientist"])
            key_map = {"Director": "director_summary", "Marketer": "marketer_summary", "Data Scientist": "technical_details"}
            st.write(diagnosis.get(key_map[persona], ""))
            
            st.divider()
            st.caption("Was this analysis helpful?")
            fb1, fb2 = st.columns(2)
            if fb1.button("👍", use_container_width=True): st.toast("Helpful", icon="📝")
            if fb2.button("👎", use_container_width=True): st.toast("Not helpful", icon="📝")

    # TAB 2: MARKET INTEL & STRATEGY
    with tab2:
        st.subheader("🌐 Market & Strategic Intelligence")
        col_mkt_1, col_mkt_2 = st.columns(2)
        
        marketing, influencer, market, strategy = load_data_sources()
        
        # FIX: Use stored session state date
        _, reference_date = get_current_date_range()
        
        with col_mkt_1:
            st.markdown("**📉 Market Demand (Google Trends)**")
            if market:
                raw_trends = market.get_market_interest(days=90, end_date=reference_date)
                df_trends = pd.DataFrame(raw_trends)
                
                df_channel = marketing.get_channel_performance(anomaly['channel'], days=90, end_date=reference_date)
                
                trend_chart = render_market_trends_overlay(df_channel, df_trends, anomaly['metric'])
                if trend_chart: st.altair_chart(trend_chart, use_container_width=True)
                else: st.caption("Insufficient data for trend overlay.")
            else: st.caption("Market data source offline.")
            
            # MTA Visualization
            st.divider()
            st.markdown("**⚖️ Attribution Comparison (MTA)**")
            if strategy:
                mta_data = strategy.get_mta_comparison(anomaly['channel'], reference_date=reference_date)
                if mta_data and mta_data.get('last_click_roas', 0) > 0:
                    mta_chart = render_mta_chart(mta_data)
                    if mta_chart: 
                        st.altair_chart(mta_chart, use_container_width=True)
                        
                        # Show insight
                        assist = mta_data.get('assist_ratio', 0)
                        mta_roas = mta_data.get('data_driven_roas', 0)
                        lc_roas = mta_data.get('last_click_roas', 0)
                        
                        if mta_roas > lc_roas * 1.2:
                            st.info(f"💡 **Insight:** MTA ROAS ({mta_roas:.2f}) is {((mta_roas/lc_roas)-1)*100:.0f}% higher than Last-Click ({lc_roas:.2f}). This channel is undervalued by simple attribution.")
                        elif lc_roas > mta_roas * 1.2:
                            st.warning(f"⚠️ **Insight:** Last-Click ({lc_roas:.2f}) overstates this channel vs MTA ({mta_roas:.2f}). Consider reducing budget.")
                else:
                    st.caption(f"No MTA data available for {anomaly['channel']}.")
                
        with col_mkt_2:
            st.markdown("**🕵️‍♀️ Competitor Moves**")
            if market:
                comp_signals = market.get_competitor_signals(anomaly['channel'], reference_date=reference_date)
                if comp_signals:
                    for sig in comp_signals[:3]:
                        st.info(f"**{sig['competitor']}**: {sig['activity_type']} ({sig['date']})\n_{sig['details']}_")
                else: st.success("No aggressive competitor moves detected recently.")
                
            # MMM Guardrails
            st.divider()
            st.markdown("**🛡️ MMM Guardrails**")
            if strategy:
                mmm = strategy.get_mmm_guardrails(anomaly['channel'], reference_date=reference_date)
                if mmm and mmm.get('saturation_point_daily', 0) > 0:
                    sat_point = mmm.get('saturation_point_daily', 0)
                    marginal_roas = mmm.get('current_marginal_roas', 0)
                    rec = mmm.get('recommendation', 'maintain')
                    
                    st.metric("Saturation Point (Daily Spend)", f"${sat_point:,}")
                    st.metric("Marginal ROAS", f"{marginal_roas:.2f}")
                    
                    if rec == "maintain":
                        st.warning(f"⚠️ Recommendation: **MAINTAIN**. Channel is nearing saturation.")
                    elif rec == "scale":
                        st.success(f"✅ Recommendation: **SCALE**. Room for efficient growth.")
                    else:
                        st.info(f"ℹ️ Recommendation: **{rec.upper()}**")
                else:
                    st.caption(f"No MMM model available for {anomaly['channel']}.")
        
        st.divider()
        st.subheader("📚 Similar Historical Incidents")
        incidents = result.get("historical_incidents", [])
        if incidents:
            for inc in incidents:
                with st.expander(f"{inc.get('date')} - {inc.get('anomaly_type')} ({inc.get('similarity_score', 0):.0%} Match)"):
                    st.markdown(f"**Root Cause:** {inc.get('root_cause')}")
                    st.markdown(f"**Resolution:** {inc.get('resolution')}")
        else: st.info("No similar historical incidents found.")
            
        st.divider()
        st.subheader("🔎 Investigation Log")
        st.text_area("Agent Notes", value=result.get("investigation_summary", ""), height=200)

    # TAB 3: ACTIONS
    with tab3:
        st.subheader("🔮 Impact Projection")
        with st.expander("Show Simulation", expanded=True):
            # FIX: Get historical data and reference date for unique projections
            marketing, _, _, _ = load_data_sources()
            _, ref_date = get_current_date_range()
            
            if "influencer" not in anomaly.get('channel', ''):
                hist_df = marketing.get_channel_performance(anomaly['channel'], days=30, end_date=ref_date)
            else:
                hist_df = pd.DataFrame()
            
            sim_chart = render_impact_simulation(anomaly, hist_df, ref_date)
            st.altair_chart(sim_chart, use_container_width=True)
        
        st.divider()
        st.subheader("💡 Recommended Actions")
        actions = result.get("proposed_actions", [])
        if not actions: st.info("No actions proposed.")
        
        for i, action in enumerate(actions):
            with st.container():
                st.markdown(f"#### {i+1}. {(action.get('action_type') or 'Unknown').replace('_', ' ').title()}")
                c_desc, c_impact, c_btn = st.columns([2, 1, 1])
                
                with c_desc:
                    st.markdown(f"**Operation:** `{action.get('operation')}`")
                    st.markdown(f"**Parameters:** {action.get('parameters')}")
                
                with c_impact:
                    st.caption("Estimated Impact")
                    st.write(action.get("estimated_impact", "Unknown"))
                    risk = action.get("risk_level", "medium")
                    risk_color = "red" if risk == "high" else "orange" if risk == "medium" else "green"
                    st.markdown(f"Risk: :{risk_color}[{risk.upper()}]")

                with c_btn:
                    st.write("")
                    
                    act_id = action.get('action_id')
                    state = st.session_state.action_states.get(act_id)
                    
                    if state:
                        if state['status'] == 'approved':
                            st.success(f"✅ Approved on {state['timestamp'].strftime('%H:%M:%S')}")
                        else:
                            st.error(f"❌ Rejected on {state['timestamp'].strftime('%H:%M:%S')}")
                    else:
                        c_a, c_b = st.columns([1, 1])
                        if c_a.button("✅ Approve", key=f"app_{i}", type="primary"):
                            try:
                                from src.notifications.slack import send_diagnosis_alert
                                success = send_diagnosis_alert(anomaly, diagnosis, [action])
                                if success: st.toast("Action Approved & Slack Sent!", icon="🚀")
                                else: st.toast("Approved (Slack Failed)", icon="⚠️")
                            except Exception as e:
                                st.error(f"Error sending alert: {e}")
                            
                            st.session_state.action_states[act_id] = {"status": "approved", "timestamp": datetime.now()}
                            st.rerun()
                                
                        if c_b.button("❌ Reject", key=f"rej_{i}"):
                            try:
                                from src.notifications.slack import SLACK_WEBHOOK_URL
                                import httpx
                                if SLACK_WEBHOOK_URL:
                                    msg = f"🚫 *Action Rejected*: User rejected proposal to *{action.get('action_type')}* for {anomaly.get('channel')}."
                                    httpx.post(SLACK_WEBHOOK_URL, json={"text": msg})
                                    st.toast("Rejection logged to Slack", icon="ℹ️")
                            except Exception: pass
                            
                            st.session_state.action_states[act_id] = {"status": "rejected", "timestamp": datetime.now()}
                            st.rerun()
                st.divider()

    # TAB 4: CHAT ASSISTANT
    with tab4:
        st.subheader("💬 Analyst Assistant")
        messages_container = st.container()
        
        with messages_container:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
            
        if prompt := st.chat_input("Ask about this anomaly..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with messages_container:
                st.chat_message("user").write(prompt)
            
            with st.spinner("Analyzing..."):
                try:
                    period_context = f"Analysis Period: {st.session_state.selected_start_date} to {st.session_state.selected_end_date}"
                    
                    context = f"""
                    CONTEXT:
                    {period_context}
                    Anomaly: {anomaly.get('channel')} {anomaly.get('metric')} {anomaly.get('direction')}
                    Root Cause: {diagnosis.get('root_cause', 'N/A')}
                    Evidence: {str(diagnosis.get('supporting_evidence', []))}
                    Proposed Actions: {[a.get('action_type') for a in actions]}
                    User Question: {prompt}
                    """
                    if get_llm_safe:
                        llm = get_llm_safe("tier1")
                        response = llm.invoke([{"role": "user", "content": context}]).content
                    else: response = "AI Service unavailable."
                except Exception as e: response = f"Error: {str(e)}"
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with messages_container:
                st.chat_message("assistant").write(response)

# Footer
st.divider()
is_mock = "src.data_layer.mock.marketing" in sys.modules
st.caption(f"Expedition v1.0 | Data Mode: {'Mock' if is_mock else 'Production'}")
