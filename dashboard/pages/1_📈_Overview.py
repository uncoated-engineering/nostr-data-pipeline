"""Network Overview - Key metrics and statistics."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery

st.set_page_config(page_title="Overview", page_icon="📈", layout="wide")

# Initialize
@st.cache_resource
def get_db_manager():
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

st.title("📈 Network Overview")
st.markdown("Real-time statistics and key metrics from the Nostr network")

st.divider()

try:
    with get_db_manager().get_session() as session:
        query = AnalyticsQuery()
        overview = query.get_network_overview(session)

        if not overview:
            st.warning("⚠️ No data available yet. Start the pipeline to collect data.")
            st.stop()

        # Key Metrics Row
        st.subheader("📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Users",
                f"{overview['users']['total']:,}",
                delta=f"+{overview['users']['new_24h']:,} today",
                delta_color="normal"
            )

        with col2:
            st.metric(
                "Active Users (24h)",
                f"{overview['users']['active_24h']:,}",
                delta=f"{overview['users']['active_1h']:,} in last hour",
                delta_color="normal"
            )

        with col3:
            st.metric(
                "Total Events",
                f"{overview['events']['total']:,}",
                delta=f"+{overview['events']['events_24h']:,} today",
                delta_color="normal"
            )

        with col4:
            st.metric(
                "Events/Hour",
                f"{overview['events']['events_1h']:,}",
                delta=f"{overview['events']['notes_24h']:,} notes today",
                delta_color="normal"
            )

        st.divider()

        # User Activity Row
        st.subheader("👥 User Activity")
        col1, col2 = st.columns(2)

        with col1:
            # User activity gauge
            fig_users = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=overview['users']['active_24h'],
                delta={'reference': overview['users']['total'] * 0.1},
                title={'text': "Active Users (24h)"},
                gauge={
                    'axis': {'range': [None, overview['users']['total']]},
                    'bar': {'color': "#8B5CF6"},
                    'steps': [
                        {'range': [0, overview['users']['total'] * 0.3], 'color': "#F3F4F6"},
                        {'range': [overview['users']['total'] * 0.3, overview['users']['total'] * 0.6], 'color': "#E5E7EB"},
                        {'range': [overview['users']['total'] * 0.6, overview['users']['total']], 'color': "#D1D5DB"}
                    ],
                    'threshold': {
                        'line': {'color': "#EC4899", 'width': 4},
                        'thickness': 0.75,
                        'value': overview['users']['active_1h'] * 24
                    }
                }
            ))
            fig_users.update_layout(height=300)
            st.plotly_chart(fig_users, use_container_width=True)

        with col2:
            # User growth pie chart
            user_data = pd.DataFrame({
                'Category': ['Active (1h)', 'Active (24h)', 'Inactive'],
                'Count': [
                    overview['users']['active_1h'],
                    overview['users']['active_24h'] - overview['users']['active_1h'],
                    overview['users']['total'] - overview['users']['active_24h']
                ]
            })
            fig_user_pie = px.pie(
                user_data,
                values='Count',
                names='Category',
                title='User Activity Distribution',
                color_discrete_sequence=['#8B5CF6', '#EC4899', '#E5E7EB']
            )
            fig_user_pie.update_layout(height=300)
            st.plotly_chart(fig_user_pie, use_container_width=True)

        st.divider()

        # Zap Statistics Row
        st.subheader("⚡ Lightning Network Activity")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Zaps",
                f"{overview['zaps']['total']:,}",
                delta=f"+{overview['zaps']['zaps_24h']:,} today"
            )

        with col2:
            st.metric(
                "Total Sats",
                f"{overview['zaps']['total_sats']:,}",
                delta=f"+{overview['zaps']['sats_24h']:,} today"
            )

        with col3:
            avg_zap = overview['zaps']['sats_24h'] / overview['zaps']['zaps_24h'] if overview['zaps']['zaps_24h'] > 0 else 0
            st.metric(
                "Avg Zap (24h)",
                f"{avg_zap:,.0f} sats"
            )

        with col4:
            st.metric(
                "Zaps/Hour",
                f"{overview['zaps']['zaps_24h'] // 24:,}"
            )

        # Zap distribution chart
        zap_dist = query.get_zap_distribution(session, hours=24)
        if zap_dist['count'] > 0:
            col1, col2 = st.columns(2)

            with col1:
                # Zap statistics
                stats_data = pd.DataFrame({
                    'Metric': ['Mean', 'Median', 'P25', 'P75', 'P95', 'Max'],
                    'Sats': [
                        zap_dist['mean'],
                        zap_dist['median'],
                        zap_dist.get('p25', 0),
                        zap_dist.get('p75', 0),
                        zap_dist.get('p95', 0),
                        zap_dist['max']
                    ]
                })
                fig_stats = px.bar(
                    stats_data,
                    x='Metric',
                    y='Sats',
                    title='Zap Amount Distribution (24h)',
                    color='Sats',
                    color_continuous_scale='Purples'
                )
                fig_stats.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig_stats, use_container_width=True)

            with col2:
                # Zap volume indicator
                fig_zap_volume = go.Figure(go.Indicator(
                    mode="number+delta",
                    value=overview['zaps']['sats_24h'],
                    title={'text': "Sats Zapped (24h)"},
                    delta={'reference': overview['zaps']['sats_24h'] * 0.8, 'relative': True},
                    number={'suffix': " sats", 'font': {'size': 40}},
                ))
                fig_zap_volume.update_layout(height=300)
                st.plotly_chart(fig_zap_volume, use_container_width=True)

        st.divider()

        # Event Statistics
        st.subheader("📝 Event Statistics")
        col1, col2, col3 = st.columns(3)

        with col1:
            # Events gauge
            fig_events = go.Figure(go.Indicator(
                mode="number+delta",
                value=overview['events']['events_24h'],
                title={'text': "Events (24h)"},
                delta={'reference': overview['events']['events_1h'] * 24, 'relative': True},
                number={'font': {'size': 50}},
            ))
            fig_events.update_layout(height=250)
            st.plotly_chart(fig_events, use_container_width=True)

        with col2:
            # Notes specific
            fig_notes = go.Figure(go.Indicator(
                mode="number+delta",
                value=overview['events']['notes_24h'],
                title={'text': "Notes (24h)"},
                delta={'reference': overview['events']['events_24h'] * 0.5, 'relative': True},
                number={'font': {'size': 50}},
            ))
            fig_notes.update_layout(height=250)
            st.plotly_chart(fig_notes, use_container_width=True)

        with col3:
            # Event rate
            events_per_second = overview['events']['events_1h'] / 3600
            fig_rate = go.Figure(go.Indicator(
                mode="number",
                value=events_per_second,
                title={'text': "Events/Second"},
                number={'suffix': " eps", 'font': {'size': 50}},
            ))
            fig_rate.update_layout(height=250)
            st.plotly_chart(fig_rate, use_container_width=True)

        st.divider()

        # Activity Timeline
        st.subheader("📈 Recent Activity Timeline")
        timeline = query.get_activity_timeline(session, hours=24, interval_minutes=60)

        if timeline:
            timeline_df = pd.DataFrame([
                {
                    'timestamp': entry['timestamp'],
                    'Notes': entry['metrics']['notes'],
                    'Reactions': entry['metrics']['reactions'],
                    'Zaps': entry['metrics']['zaps'],
                    'Other': entry['metrics']['other']
                }
                for entry in timeline
            ])

            fig_timeline = px.area(
                timeline_df,
                x='timestamp',
                y=['Notes', 'Reactions', 'Zaps', 'Other'],
                title='Event Activity Over Time (Last 24 Hours)',
                labels={'value': 'Event Count', 'timestamp': 'Time'},
                color_discrete_sequence=['#8B5CF6', '#EC4899', '#F59E0B', '#10B981']
            )
            fig_timeline.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig_timeline, use_container_width=True)

        # Network Health Summary
        st.divider()
        st.subheader("💚 Network Health")

        col1, col2, col3 = st.columns(3)

        with col1:
            health_score = min(100, (overview['users']['active_24h'] / max(overview['users']['total'], 1)) * 100 * 10)
            st.metric("Activity Score", f"{health_score:.1f}%")

        with col2:
            growth_rate = (overview['users']['new_24h'] / max(overview['users']['total'], 1)) * 100
            st.metric("Growth Rate (24h)", f"{growth_rate:.2f}%")

        with col3:
            engagement = (overview['zaps']['zaps_24h'] / max(overview['events']['notes_24h'], 1)) * 100
            st.metric("Engagement Rate", f"{engagement:.1f}%")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.exception(e)

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh", value=False):
    import time
    refresh_interval = st.sidebar.slider("Interval (seconds)", 5, 60, 30)
    time.sleep(refresh_interval)
    st.rerun()
