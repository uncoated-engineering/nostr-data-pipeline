"""Network Activity - Real-time charts and timelines."""

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
from nostr_pipeline.models import NetworkStats

st.set_page_config(page_title="Network Activity", page_icon="📡", layout="wide")

@st.cache_resource
def get_db_manager():
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

st.title("📡 Network Activity")
st.markdown("Real-time activity monitoring and historical trends")

st.divider()

# Time range selector
time_range = st.selectbox(
    "Time Range",
    options=[6, 12, 24, 48, 72, 168],
    index=2,
    format_func=lambda x: f"Last {x} hours" if x < 168 else "Last 7 days"
)

try:
    with get_db_manager().get_session() as session:
        query = AnalyticsQuery()

        # Activity Timeline
        st.subheader("📈 Event Activity Timeline")

        timeline = query.get_activity_timeline(session, hours=time_range, interval_minutes=60)

        if timeline:
            timeline_df = pd.DataFrame([
                {
                    'Time': pd.to_datetime(entry['timestamp']),
                    'Notes': entry['metrics']['notes'],
                    'Reactions': entry['metrics']['reactions'],
                    'Zaps': entry['metrics']['zaps'],
                    'Other': entry['metrics']['other']
                }
                for entry in timeline
            ])

            # Calculate totals
            timeline_df['Total'] = timeline_df[['Notes', 'Reactions', 'Zaps', 'Other']].sum(axis=1)

            col1, col2 = st.columns([3, 1])

            with col1:
                # Stacked area chart
                fig_timeline = go.Figure()

                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df['Time'], y=timeline_df['Notes'],
                    name='Notes',
                    mode='lines',
                    stackgroup='one',
                    fillcolor='rgba(139, 92, 246, 0.6)',
                    line=dict(color='rgb(139, 92, 246)', width=2)
                ))

                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df['Time'], y=timeline_df['Reactions'],
                    name='Reactions',
                    mode='lines',
                    stackgroup='one',
                    fillcolor='rgba(236, 72, 153, 0.6)',
                    line=dict(color='rgb(236, 72, 153)', width=2)
                ))

                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df['Time'], y=timeline_df['Zaps'],
                    name='Zaps',
                    mode='lines',
                    stackgroup='one',
                    fillcolor='rgba(245, 158, 11, 0.6)',
                    line=dict(color='rgb(245, 158, 11)', width=2)
                ))

                fig_timeline.add_trace(go.Scatter(
                    x=timeline_df['Time'], y=timeline_df['Other'],
                    name='Other',
                    mode='lines',
                    stackgroup='one',
                    fillcolor='rgba(16, 185, 129, 0.6)',
                    line=dict(color='rgb(16, 185, 129)', width=2)
                ))

                fig_timeline.update_layout(
                    title='Event Distribution Over Time',
                    xaxis_title='Time',
                    yaxis_title='Event Count',
                    hovermode='x unified',
                    height=400
                )

                st.plotly_chart(fig_timeline, width="stretch")

            with col2:
                # Summary stats
                total_events = timeline_df['Total'].sum()
                avg_events_per_hour = timeline_df['Total'].mean()
                peak_hour = timeline_df.loc[timeline_df['Total'].idxmax()]['Time']

                st.metric("Total Events", f"{total_events:,}")
                st.metric("Avg Events/Hour", f"{avg_events_per_hour:,.0f}")
                st.metric("Peak Hour", peak_hour.strftime("%Y-%m-%d %H:%M"))

                # Event type breakdown
                type_totals = {
                    'Notes': timeline_df['Notes'].sum(),
                    'Reactions': timeline_df['Reactions'].sum(),
                    'Zaps': timeline_df['Zaps'].sum(),
                    'Other': timeline_df['Other'].sum()
                }

                fig_pie = px.pie(
                    values=list(type_totals.values()),
                    names=list(type_totals.keys()),
                    color_discrete_sequence=['#8B5CF6', '#EC4899', '#F59E0B', '#10B981']
                )
                fig_pie.update_layout(height=200, showlegend=True, margin=dict(t=30, b=0))
                st.plotly_chart(fig_pie, width="stretch")

            # Individual event type trends
            col1, col2 = st.columns(2)

            with col1:
                fig_notes = px.line(
                    timeline_df,
                    x='Time',
                    y='Notes',
                    title='Notes Activity',
                    markers=True
                )
                fig_notes.update_traces(line_color='#8B5CF6', line_width=3)
                fig_notes.update_layout(height=250, yaxis_title='Count')
                st.plotly_chart(fig_notes, width="stretch")

            with col2:
                fig_zaps = px.line(
                    timeline_df,
                    x='Time',
                    y='Zaps',
                    title='Zaps Activity',
                    markers=True
                )
                fig_zaps.update_traces(line_color='#F59E0B', line_width=3)
                fig_zaps.update_layout(height=250, yaxis_title='Count')
                st.plotly_chart(fig_zaps, width="stretch")

        else:
            st.info("No activity data available for this time range.")

        st.divider()

        # Network Stats History
        st.subheader("📊 Historical Network Statistics")

        # Get historical network stats
        cutoff = datetime.utcnow() - timedelta(hours=time_range)
        stats_history = (
            session.query(NetworkStats)
            .filter(NetworkStats.timestamp >= cutoff)
            .order_by(NetworkStats.timestamp)
            .all()
        )

        if stats_history:
            stats_df = pd.DataFrame([
                {
                    'Time': stat.timestamp,
                    'Total Users': stat.total_users,
                    'Active Users (24h)': stat.active_users_24h,
                    'Events (24h)': stat.events_24h,
                    'Zaps (24h)': stat.zaps_24h,
                    'Sats (24h)': stat.sats_zapped_24h,
                }
                for stat in stats_history
            ])

            # User growth chart
            fig_users = px.line(
                stats_df,
                x='Time',
                y=['Total Users', 'Active Users (24h)'],
                title='User Growth Over Time',
                labels={'value': 'User Count', 'variable': 'Metric'},
                color_discrete_sequence=['#8B5CF6', '#EC4899']
            )
            fig_users.update_layout(height=350, hovermode='x unified')
            st.plotly_chart(fig_users, width="stretch")

            col1, col2 = st.columns(2)

            with col1:
                # Events trend
                fig_events = px.area(
                    stats_df,
                    x='Time',
                    y='Events (24h)',
                    title='Daily Events Trend',
                    color_discrete_sequence=['#8B5CF6']
                )
                fig_events.update_layout(height=300, yaxis_title='Events (24h)')
                st.plotly_chart(fig_events, width="stretch")

            with col2:
                # Sats trend
                fig_sats = px.area(
                    stats_df,
                    x='Time',
                    y='Sats (24h)',
                    title='Daily Sats Zapped Trend',
                    color_discrete_sequence=['#F59E0B']
                )
                fig_sats.update_layout(height=300, yaxis_title='Sats (24h)')
                st.plotly_chart(fig_sats, width="stretch")

        else:
            st.info("No historical network stats available.")

        st.divider()

        # Real-time Stats
        st.subheader("⚡ Real-Time Network Status")

        overview = query.get_network_overview(session)

        if overview:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Active Now (1h)",
                    f"{overview['users']['active_1h']:,}",
                    delta=f"{overview['users']['active_24h']:,} in 24h"
                )

            with col2:
                events_per_sec = overview['events']['events_1h'] / 3600
                st.metric(
                    "Events/Second",
                    f"{events_per_sec:.2f}",
                    delta=f"{overview['events']['events_1h']:,} last hour"
                )

            with col3:
                zaps_per_hour = overview['zaps']['zaps_24h'] // 24
                st.metric(
                    "Zaps/Hour",
                    f"{zaps_per_hour:,}",
                    delta=f"{overview['zaps']['zaps_24h']:,} in 24h"
                )

            with col4:
                avg_zap = overview['zaps']['sats_24h'] / max(overview['zaps']['zaps_24h'], 1)
                st.metric(
                    "Avg Zap Size",
                    f"{avg_zap:,.0f} sats"
                )

            # Velocity indicators
            col1, col2, col3 = st.columns(3)

            with col1:
                growth_rate = (overview['users']['new_24h'] / max(overview['users']['total'], 1)) * 100
                fig_growth = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=growth_rate,
                    title={'text': "User Growth Rate (%)"},
                    delta={'reference': 1.0},
                    gauge={
                        'axis': {'range': [0, 10]},
                        'bar': {'color': "#8B5CF6"},
                        'steps': [
                            {'range': [0, 3], 'color': "#F3F4F6"},
                            {'range': [3, 7], 'color': "#E5E7EB"}
                        ],
                        'threshold': {
                            'line': {'color': "#EC4899", 'width': 4},
                            'thickness': 0.75,
                            'value': 5
                        }
                    }
                ))
                fig_growth.update_layout(height=250)
                st.plotly_chart(fig_growth, width="stretch")

            with col2:
                activity_rate = (overview['events']['events_1h'] / max(overview['users']['active_1h'], 1))
                fig_activity = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=activity_rate,
                    title={'text': "Events per Active User"},
                    gauge={
                        'axis': {'range': [0, 50]},
                        'bar': {'color': "#EC4899"},
                        'steps': [
                            {'range': [0, 15], 'color': "#F3F4F6"},
                            {'range': [15, 30], 'color': "#E5E7EB"}
                        ]
                    }
                ))
                fig_activity.update_layout(height=250)
                st.plotly_chart(fig_activity, width="stretch")

            with col3:
                engagement = (overview['zaps']['zaps_24h'] / max(overview['events']['notes_24h'], 1)) * 100
                fig_engagement = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=engagement,
                    title={'text': "Zap Engagement (%)"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#F59E0B"},
                        'steps': [
                            {'range': [0, 30], 'color': "#F3F4F6"},
                            {'range': [30, 60], 'color': "#E5E7EB"}
                        ]
                    }
                ))
                fig_engagement.update_layout(height=250)
                st.plotly_chart(fig_engagement, width="stretch")

except Exception as e:
    st.error(f"Error loading network data: {str(e)}")
    st.exception(e)

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh", value=True, key="network_refresh"):
    import time
    refresh_interval = st.sidebar.slider("Interval (seconds)", 5, 60, 15)
    st.sidebar.info(f"Refreshing every {refresh_interval}s")
    time.sleep(refresh_interval)
    st.rerun()
