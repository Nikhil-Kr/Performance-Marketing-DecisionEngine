# <---------- V5 - Chat Box Fix ---------->

"""
Project Expedition - Decision Cockpit
=====================================

Streamlit-based dashboard for the Automated Decision Engine.
Tier 2 Features: Filters, Time-Series Context, User Selection, Chat, Impact Simulator, Feedback.

Run with: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import sys
from pathlib import Path
import time

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
    "default": "https://cdn-icons-png.flaticon.com/512/1055/1055644.png" # Megaphone generic
}

# ============================================================================
# Session State
# ============================================================================

if "anomalies" not in st.session_state:
    st.session_state.anomalies = []
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = None
if "selected_anomaly_id" not in st.session_state:
    st.session_state.selected_anomaly_id = None
if "investigation_result" not in st.session_state:
    st.session_state.investigation_result = None
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "dashboard"  # 'dashboard' or 'investigation'
if "investigation_cache" not in st.session_state:
    st.session_state.investigation_cache = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ============================================================================
# Helper Functions
# ============================================================================

def load_data_sources():
    """Load data sources."""
    try:
        from src.data_layer import get_marketing_data, get_influencer_data
        marketing = get_marketing_data()
        influencer = get_influencer_data()
        return marketing, influencer
    except Exception as e:
        st.error(f"Failed to load data sources: {e}")
        return None, None

def get_severity_color(severity):
    colors = {
        "critical": "#FF4B4B",
        "high": "#FFA500",
        "medium": "#FFD700",
        "low": "#90EE90"
    }
    return colors.get(severity.lower(), "#FFFFFF")

def get_channel_logo(channel_name):
    """Get logo URL for a channel."""
    name = channel_name.lower()
    if "google" in name: return CHANNEL_LOGOS["google"]
    if "youtube" in name: return CHANNEL_LOGOS["youtube"]
    if "meta" in name or "facebook" in name or "instagram" in name: return CHANNEL_LOGOS["meta"]
    if "tiktok" in name: return CHANNEL_LOGOS["tiktok"]
    if "linkedin" in name: return CHANNEL_LOGOS["linkedin"]
    return CHANNEL_LOGOS["default"]

def render_trend_chart(df, metric, date_range=None, severity="low"):
    """Render a detailed trend chart using Altair."""
    if df.empty or metric not in df.columns:
        return None
    
    # Filter by date if provided
    chart_df = df.copy()
    if date_range and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        chart_df = chart_df[
            (pd.to_datetime(chart_df['date']) >= start_date) & 
            (pd.to_datetime(chart_df['date']) <= end_date)
        ]

    if chart_df.empty:
        return None

    # Colors
    color = get_severity_color(severity)
    
    # Chart
    chart = alt.Chart(chart_df).mark_area(
        line={'color': color, 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color=color, offset=0),
                   alt.GradientStop(color='rgba(255, 255, 255, 0.1)', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('date:T', title='Date', axis=alt.Axis(format='%b %d', grid=False, domain=False)),
        y=alt.Y(f'{metric}:Q', title=metric.replace('_', ' ').title(), axis=alt.Axis(grid=True, domain=False)),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip(f'{metric}:Q', title=metric.replace('_', ' ').title(), format=',.2f')
        ]
    ).properties(
        height=150,  # Taller than sparkline
        width='container'
    ).interactive()

    return chart

def render_impact_simulation(metric, current_value, direction):
    """
    Render a simulation chart showing 'Do Nothing' vs 'Action Taken'.
    """
    dates = [datetime.now() + timedelta(days=i) for i in range(7)]
    
    # Convert string value to float if needed
    try:
        start_val = float(current_value)
    except:
        start_val = 100.0 # Fallback
        
    # Logic: 
    # If Spike (Bad) -> Do Nothing = Up, Action = Down
    # If Drop (Bad) -> Do Nothing = Down, Action = Up
    
    if direction == "spike":
        # Bad path (up)
        baseline = [start_val * (1 + 0.05 * i) for i in range(7)]
        # Good path (stabilize/down)
        action_path = [start_val * (1 - 0.1 * i) for i in range(7)]
    else: # drop
        # Bad path (down)
        baseline = [start_val * (1 - 0.05 * i) for i in range(7)]
        # Good path (recover)
        action_path = [start_val * (1 + 0.08 * i) for i in range(7)]
        
    df_base = pd.DataFrame({"date": dates, "value": baseline, "scenario": "Do Nothing (Baseline)"})
    df_act = pd.DataFrame({"date": dates, "value": action_path, "scenario": "With Action (Projected)"})
    
    df_sim = pd.concat([df_base, df_act])
    
    # Chart
    chart = alt.Chart(df_sim).mark_line(point=True).encode(
        x=alt.X('date:T', title='Forecast Date', axis=alt.Axis(format='%b %d')),
        y=alt.Y('value:Q', title=f"Projected {metric}", scale=alt.Scale(zero=False)),
        color=alt.Color('scenario:N', scale=alt.Scale(domain=['Do Nothing (Baseline)', 'With Action (Projected)'], range=['#FF4B4B', '#00D26A'])),
        tooltip=['date', 'value', 'scenario']
    ).properties(
        height=200,
        width='container',
        title="Impact Simulator: 7-Day Forecast"
    )
    
    return chart


# ============================================================================
# Main Content
# ============================================================================

# HEADER
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🧭 Expedition Decision Cockpit")
with col2:
    if st.session_state.view_mode == "investigation":
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.view_mode = "dashboard"
            st.rerun()

st.divider()

# VIEW ROUTING
if st.session_state.view_mode == "dashboard":
    
    # --- DASHBOARD VIEW ---
    
    # 1. CONTROLS SECTION (Main View)
    with st.expander("🎛️ Filters & Controls", expanded=True):
        c_scan, c_date, c_sev, c_chan = st.columns([1, 2, 2, 2])
        
        with c_scan:
            st.write("") # Spacer
            st.write("") 
            if st.button("📡 Scan Now", type="primary"):
                with st.spinner("Scanning all channels..."):
                    marketing, influencer = load_data_sources()
                    if marketing and influencer:
                        anomalies = marketing.get_anomalies() + influencer.get_anomalies()
                        # Add unique IDs for selection
                        for i, a in enumerate(anomalies):
                            a['_id'] = i
                        
                        st.session_state.anomalies = anomalies
                        st.session_state.last_scan_time = datetime.now()
                        st.session_state.investigation_result = None
                        # Clear cache on new scan? Optional. Keeping cache is usually better for history.
                        st.rerun()
        
        with c_date:
            date_range = st.date_input(
                "Date Range",
                value=(datetime.now() - timedelta(days=30), datetime.now()),
                format="MM/DD/YYYY"
            )
            
        with c_sev:
            severity_filter = st.multiselect(
                "Severity",
                ["critical", "high", "medium", "low"],
                default=["critical", "high", "medium", "low"]
            )
            
        with c_chan:
            # Dynamic channel list
            available_channels = sorted(list(set(a['channel'] for a in st.session_state.anomalies))) if st.session_state.anomalies else []
            channel_filter = st.multiselect(
                "Channel",
                available_channels,
                default=available_channels
            )

    if not st.session_state.anomalies:
        st.info("👋 Welcome! Click 'Scan Now' to detect anomalies.")
        
    else:
        # FILTER LOGIC
        filtered_anomalies = [
            a for a in st.session_state.anomalies
            if a['severity'] in severity_filter
            and (not channel_filter or a['channel'] in channel_filter)
        ]
        
        st.divider()
        
        # Summary Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Anomalies Detected", len(st.session_state.anomalies))
        c2.metric("Critical", len([a for a in st.session_state.anomalies if a['severity'] == 'critical']))
        c3.metric("High", len([a for a in st.session_state.anomalies if a['severity'] == 'high']))
        c4.metric("Showing", len(filtered_anomalies))
        
        st.markdown("### 🚨 Detected Anomalies")
        
        # LIST VIEW (Cards)
        for i, anomaly in enumerate(filtered_anomalies):
            
            # Card Container
            with st.container():
                # Grid layout: Status | Logo | Text | Chart | Button
                c_status, c_logo, c_detail, c_chart, c_action = st.columns([0.15, 0.5, 2, 3, 1])
                
                # 1. Status Indicator
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
                
                # 2. Logo
                with c_logo:
                    logo_url = get_channel_logo(anomaly['channel'])
                    st.image(logo_url, width=50)
                
                # 3. Details
                with c_detail:
                    st.markdown(f"**{anomaly['channel'].replace('_', ' ').title()}**")
                    st.markdown(f"Metric: **{anomaly['metric'].replace('_', ' ').title()}**")
                    
                    st.caption("Deviation (vs Expected)")
                    delta_color = "inverse" if anomaly['direction'] == "spike" else "normal" 
                    st.metric(
                        "Deviation", 
                        f"{anomaly['current_value']}", 
                        f"{anomaly['deviation_pct']}%",
                        delta_color=delta_color,
                        label_visibility="collapsed"
                    )
                    
                    st.markdown(f"Severity: <span style='color:{color}; font-weight:bold'>{anomaly['severity'].upper()}</span>", unsafe_allow_html=True)

                # 4. Main Chart (Context)
                with c_chart:
                    marketing, influencer = load_data_sources()
                    # Determine chart data source
                    if "influencer" in anomaly['channel']:
                        df_hist = pd.DataFrame() 
                    else:
                        df_hist = marketing.get_channel_performance(anomaly['channel'], days=90)
                    
                    chart = render_trend_chart(df_hist, anomaly['metric'], date_range, anomaly['severity'])
                    if chart:
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.caption("No trend data available for visualization")

                # 5. Action Button (With Caching Logic)
                with c_action:
                    st.write("") # Spacer
                    st.write("")
                    
                    # Check cache
                    is_cached = anomaly['_id'] in st.session_state.investigation_cache
                    btn_label = "📂 View Report" if is_cached else "🕵️‍♂️ Investigate"
                    btn_type = "secondary" if is_cached else "primary"
                    
                    if st.button(btn_label, key=f"inv_{i}", type=btn_type):
                        
                        # PRESERVE CHAT HISTORY LOGIC
                        # Only reset chat if we are selecting a NEW anomaly
                        if st.session_state.selected_anomaly_id != anomaly['_id']:
                            st.session_state.chat_history = [
                                {"role": "assistant", "content": f"I'm analyzing the {anomaly['channel']} anomaly. Ask me anything about the root cause or next steps!"}
                            ]
                        
                        st.session_state.selected_anomaly_id = anomaly['_id']
                        
                        if is_cached:
                            # Load from cache
                            st.session_state.investigation_result = st.session_state.investigation_cache[anomaly['_id']]
                            st.session_state.view_mode = "investigation"
                            st.rerun()
                        else:
                            # TRIGGER AGENT
                            with st.spinner(f"🔍 Investigating {anomaly['channel']}..."):
                                from src.graph import run_expedition
                                
                                # Note: If the backend graph is configured to strictly auto-detect 
                                # highest priority issues in the 'detect' node, it might override this.
                                # Ideally, the graph should check if 'selected_anomaly' is present in initial_state.
                                initial_state = {
                                    "selected_anomaly": anomaly,
                                    "anomalies": [anomaly] # Focus list to prevent re-scanning everything
                                }
                                
                                result = run_expedition(initial_state)
                                # Save to cache
                                st.session_state.investigation_cache[anomaly['_id']] = result
                                st.session_state.investigation_result = result
                                st.session_state.view_mode = "investigation"
                                st.rerun()
                
                st.divider()

elif st.session_state.view_mode == "investigation":
    
    # --- INVESTIGATION VIEW (The Agent) ---
    
    result = st.session_state.investigation_result
    anomaly = result.get("selected_anomaly", {})
    
    if not result:
        st.error("Investigation failed to load.")
        st.stop()

    # Title Context
    c_back_logo, c_back_title, c_rerun = st.columns([0.5, 8, 2])
    with c_back_logo:
        st.image(get_channel_logo(anomaly.get('channel', '')), width=50)
    with c_back_title:
        st.header(f"Investigation: {anomaly.get('channel', 'Unknown').replace('_', ' ').title()}")
    with c_rerun:
        st.write("")
        if st.button("🔄 Re-analyze", help="Force a fresh investigation (clears cache)"):
            # Clear cache and re-run
            if anomaly.get('_id') in st.session_state.investigation_cache:
                del st.session_state.investigation_cache[anomaly['_id']]
            
            with st.spinner("Re-running analysis..."):
                from src.graph import run_expedition
                initial_state = {
                    "selected_anomaly": anomaly,
                    "anomalies": [anomaly]
                }
                result = run_expedition(initial_state)
                st.session_state.investigation_cache[anomaly['_id']] = result
                st.session_state.investigation_result = result
                st.rerun()
    
    st.markdown(f"**Issue:** {anomaly.get('metric')} {anomaly.get('direction')} by {anomaly.get('deviation_pct')}%")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Diagnosis", "🔍 Deep Dive", "⚡ Actions", "💬 Assistant"])
    
    # TAB 1: DIAGNOSIS (Explainer & Critic)
    with tab1:
        diagnosis = result.get("diagnosis", {})
        validation = result.get("critic_validation", {})
        
        # Validation Badge
        if result.get("validation_passed"):
            st.success(f"✅ Verified Analysis (Risk: {validation.get('hallucination_risk', 0):.0%})")
        else:
            st.warning(f"⚠️ Low Confidence (Risk: {validation.get('hallucination_risk', 0):.0%})")
            with st.expander("Validation Issues"):
                for issue in validation.get("issues", []):
                    st.markdown(f"- {issue}")

        # Diagnosis Content
        col_main, col_summary = st.columns([2, 1])
        
        with col_main:
            st.subheader("🎯 Root Cause")
            st.info(diagnosis.get("root_cause", "Analysis pending..."))
            
            st.subheader("📊 Evidence")
            for item in diagnosis.get("supporting_evidence", []):
                st.markdown(f"- {item}")

        with col_summary:
            st.subheader("Executive Summary")
            st.markdown(f"_{diagnosis.get('executive_summary', 'No summary available')}_")
            
            st.divider()
            
            # Persona Toggle
            persona = st.selectbox("View Explanation For:", ["Director", "Marketer", "Data Scientist"])
            key_map = {
                "Director": "director_summary",
                "Marketer": "marketer_summary",
                "Data Scientist": "technical_details"
            }
            st.write(diagnosis.get(key_map[persona], ""))
            
            # Feedback Loop (Tier 2)
            st.divider()
            st.caption("Was this analysis helpful?")
            fb_col1, fb_col2 = st.columns(2)
            with fb_col1:
                if st.button("👍", key="thumbs_up", use_container_width=True):
                    st.toast("Feedback recorded: Helpful", icon="📝")
            with fb_col2:
                if st.button("👎", key="thumbs_down", use_container_width=True):
                    st.toast("Feedback recorded: Not helpful", icon="📝")

    # TAB 2: DEEP DIVE (RAG & Data)
    with tab2:
        st.subheader("📚 Similar Historical Incidents")
        incidents = result.get("historical_incidents", [])
        
        if incidents:
            for inc in incidents:
                with st.expander(f"{inc.get('date')} - {inc.get('anomaly_type')} ({inc.get('similarity_score', 0):.0%} Match)"):
                    st.markdown(f"**Root Cause:** {inc.get('root_cause')}")
                    st.markdown(f"**Resolution:** {inc.get('resolution')}")
        else:
            st.info("No similar historical incidents found.")
            
        st.divider()
        st.subheader("🔎 Investigation Log")
        st.text_area("Agent Notes", value=result.get("investigation_summary", ""), height=200)

    # TAB 3: ACTIONS (Proposer)
    with tab3:
        # Tier 2: Impact Simulator
        st.subheader("🔮 Impact Projection")
        with st.expander("Show Simulation", expanded=True):
            sim_chart = render_impact_simulation(
                anomaly.get('metric', 'Metric'), 
                anomaly.get('current_value', 100), 
                anomaly.get('direction', 'spike')
            )
            st.altair_chart(sim_chart, use_container_width=True)
        
        st.divider()
        st.subheader("💡 Recommended Actions")
        
        actions = result.get("proposed_actions", [])
        
        if not actions:
            st.info("No actions proposed.")
        
        for i, action in enumerate(actions):
            with st.container():
                st.markdown(f"#### {i+1}. {action.get('action_type').replace('_', ' ').title()}")
                
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
                    if st.button("✅ Approve", key=f"btn_approve_{i}", type="primary"):
                        from src.notifications.slack import send_diagnosis_alert
                        
                        # Send notification
                        success = send_diagnosis_alert(
                            anomaly=anomaly,
                            diagnosis=diagnosis,
                            actions=[action]
                        )
                        if success:
                            st.toast("Action Approved & Slack Sent!", icon="🚀")
                        else:
                            st.toast("Approved (Slack Failed)", icon="⚠️")
                            
                    if st.button("❌ Reject", key=f"btn_reject_{i}"):
                        st.toast("Action Rejected", icon="🚫")
                
                st.divider()

    # TAB 4: CHAT (Assistant)
    with tab4:
        st.subheader("💬 Analyst Assistant")
        
        # Use a container for messages to keep them organized
        messages_container = st.container()
        
        with messages_container:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
            
        if prompt := st.chat_input("Ask about this anomaly..."):
            # User message
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with messages_container:
                st.chat_message("user").write(prompt)
            
            with st.spinner("Analyzing..."):
                try:
                    # 1. Build Context
                    context = f"""
                    CONTEXT:
                    Anomaly: {anomaly.get('channel')} {anomaly.get('metric')} {anomaly.get('direction')}
                    Root Cause: {diagnosis.get('root_cause', 'N/A')}
                    Evidence: {str(diagnosis.get('supporting_evidence', []))}
                    Proposed Actions: {[a.get('action_type') for a in actions]}
                    
                    User Question: {prompt}
                    """
                    
                    # 2. Call LLM
                    if get_llm_safe:
                        llm = get_llm_safe("tier1")
                        msg = [{"role": "user", "content": context}]
                        response_obj = llm.invoke(msg)
                        response = response_obj.content
                    else:
                        response = "AI Service unavailable."
                    
                except Exception as e:
                    response = f"Sorry, I encountered an error: {str(e)}"
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with messages_container:
                st.chat_message("assistant").write(response)

# Footer
st.divider()
# Safely check if mock data module is loaded
is_mock = "src.data_layer.mock.marketing" in sys.modules
st.caption(f"Expedition v1.0 | Data Mode: {'Mock' if is_mock else 'Production'}")  
