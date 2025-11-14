"""Nostr Data Pipeline - Interactive Dashboard.

Main entry point for the Streamlit dashboard.
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery
from nostr_pipeline import __version__

# Page config
st.set_page_config(
    page_title="Nostr Analytics Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #8B5CF6 0%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #8B5CF6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database connection
@st.cache_resource
def get_db_manager():
    """Get database manager instance."""
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

# Title and header
st.markdown('<h1 class="main-header">⚡ Nostr Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown(f"**Real-time insights from the Nostr protocol** • v{__version__}")

st.divider()

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nostr-protocol/nostr/master/nostr.png", width=100)
    st.title("Navigation")
    st.info("👈 Select a page from the sidebar to explore different analytics views")

    st.divider()

    # Connection status
    st.subheader("🔌 Connection Status")
    db_manager = get_db_manager()
    if db_manager.health_check():
        st.success("✓ Database Connected")
    else:
        st.error("✗ Database Disconnected")

    st.divider()

    # Auto-refresh
    st.subheader("⏱️ Auto Refresh")
    auto_refresh = st.checkbox("Enable auto-refresh", value=True)
    if auto_refresh:
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 30)
        st.info(f"Refreshing every {refresh_interval}s")

    st.divider()

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Welcome to Nostr Analytics")
    st.markdown("""
    This dashboard provides real-time analytics and insights from the **Nostr protocol**,
    a decentralized social networking protocol.

    ### 📊 Available Views

    - **📈 Overview** - Network statistics and key metrics
    - **🔥 Trending** - Trending hashtags and viral content
    - **📡 Network** - Real-time activity and timelines
    - **👥 Users** - Top users and leaderboards
    - **🌐 Relays** - Relay health and performance
    - **⚡ Zaps** - Lightning Network analytics

    ### 🚀 Getting Started

    Select a page from the sidebar to explore different analytics views. Each page
    provides interactive visualizations and real-time data from the Nostr network.
    """)

with col2:
    st.header("Quick Stats")

    try:
        with get_db_manager().get_session() as session:
            query = AnalyticsQuery()
            overview = query.get_network_overview(session)

            if overview:
                st.metric(
                    "👥 Total Users",
                    f"{overview['users']['total']:,}",
                    delta=f"+{overview['users']['new_24h']:,} today"
                )

                st.metric(
                    "📝 Events (24h)",
                    f"{overview['events']['events_24h']:,}",
                    delta=f"{overview['events']['events_1h']:,} last hour"
                )

                st.metric(
                    "⚡ Zaps (24h)",
                    f"{overview['zaps']['zaps_24h']:,}",
                    delta=f"{overview['zaps']['sats_24h']:,} sats"
                )
            else:
                st.warning("No data available yet. Start the pipeline to collect data.")

    except Exception as e:
        st.error(f"Error loading stats: {str(e)}")

st.divider()

# Footer
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📖 About Nostr")
    st.markdown("""
    Nostr (Notes and Other Stuff Transmitted by Relays) is a simple, open protocol
    for decentralized social networking.
    """)

with col2:
    st.markdown("### 🔗 Quick Links")
    st.markdown("""
    - [Nostr Protocol](https://github.com/nostr-protocol/nostr)
    - [Project GitHub](#)
    - [Documentation](#)
    """)

with col3:
    st.markdown("### ℹ️ Pipeline Info")
    st.markdown(f"""
    - Version: {__version__}
    - Database: Connected
    - Status: Active
    """)

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(refresh_interval)
    st.rerun()
