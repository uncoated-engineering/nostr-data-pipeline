"""Lightning Zaps - Analyze zap patterns and flows."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery
from nostr_pipeline.models import Zap
from sqlalchemy import func

st.set_page_config(page_title="Zaps", page_icon="⚡", layout="wide")

@st.cache_resource
def get_db_manager():
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

st.title("⚡ Lightning Zap Analytics")
st.markdown("Explore Lightning Network activity on Nostr")

st.divider()

time_window = st.selectbox(
    "Time Window",
    options=[6, 12, 24, 48, 72, 168],
    index=2,
    format_func=lambda x: f"Last {x} hours" if x < 168 else "Last 7 days"
)

try:
    with get_db_manager().get_session() as session:
        query = AnalyticsQuery()

        # Zap distribution stats
        st.subheader("💰 Zap Distribution")

        zap_dist = query.get_zap_distribution(session, hours=time_window)

        if zap_dist['count'] > 0:
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Total Zaps", f"{zap_dist['count']:,}")

            with col2:
                st.metric("Total Sats", f"{zap_dist['total']:,}")

            with col3:
                st.metric("Mean", f"{zap_dist['mean']:.0f} sats")

            with col4:
                st.metric("Median", f"{zap_dist['median']} sats")

            with col5:
                st.metric("Max", f"{zap_dist['max']:,} sats")

            # Distribution visualization
            col1, col2 = st.columns(2)

            with col1:
                # Box plot of distribution
                stats_df = pd.DataFrame({
                    'Percentile': ['Min', 'P25', 'Median', 'P75', 'P95', 'Max'],
                    'Sats': [
                        zap_dist['min'],
                        zap_dist.get('p25', 0),
                        zap_dist['median'],
                        zap_dist.get('p75', 0),
                        zap_dist.get('p95', 0),
                        zap_dist['max']
                    ]
                })

                fig_dist = px.bar(
                    stats_df,
                    x='Percentile',
                    y='Sats',
                    title='Zap Amount Distribution',
                    color='Sats',
                    color_continuous_scale='YlOrRd'
                )
                fig_dist.update_layout(height=350)
                st.plotly_chart(fig_dist, width="stretch")

            with col2:
                # Key stats as indicators
                fig_stats = go.Figure()

                fig_stats.add_trace(go.Indicator(
                    mode="number+delta",
                    value=zap_dist['total'],
                    title={'text': f"Total Sats ({time_window}h)"},
                    delta={'reference': zap_dist['mean'] * zap_dist['count'], 'relative': False},
                    domain={'x': [0, 0.5], 'y': [0.5, 1]}
                ))

                fig_stats.add_trace(go.Indicator(
                    mode="number",
                    value=zap_dist['mean'],
                    title={'text': "Average Zap"},
                    number={'suffix': " sats"},
                    domain={'x': [0.5, 1], 'y': [0.5, 1]}
                ))

                fig_stats.add_trace(go.Indicator(
                    mode="number",
                    value=zap_dist['p95'],
                    title={'text': "95th Percentile"},
                    number={'suffix': " sats"},
                    domain={'x': [0, 0.5], 'y': [0, 0.5]}
                ))

                fig_stats.add_trace(go.Indicator(
                    mode="number",
                    value=zap_dist['count'],
                    title={'text': "Total Zaps"},
                    domain={'x': [0.5, 1], 'y': [0, 0.5]}
                ))

                fig_stats.update_layout(height=350)
                st.plotly_chart(fig_stats, width="stretch")

        st.divider()

        # Zap timeline
        st.subheader("📈 Zap Activity Over Time")

        cutoff = datetime.utcnow() - timedelta(hours=time_window)
        zaps_over_time = (
            session.query(
                func.date_trunc('hour', Zap.created_at).label('hour'),
                func.count(Zap.id).label('zap_count'),
                func.sum(Zap.amount_sats).label('total_sats')
            )
            .filter(Zap.created_at >= cutoff)
            .group_by('hour')
            .order_by('hour')
            .all()
        )

        if zaps_over_time:
            timeline_df = pd.DataFrame([
                {
                    'Time': hour,
                    'Zap Count': count,
                    'Total Sats': sats
                }
                for hour, count, sats in zaps_over_time
            ])

            col1, col2 = st.columns(2)

            with col1:
                fig_count = px.area(
                    timeline_df,
                    x='Time',
                    y='Zap Count',
                    title='Zaps Over Time',
                    color_discrete_sequence=['#F59E0B']
                )
                fig_count.update_layout(height=300)
                st.plotly_chart(fig_count, width="stretch")

            with col2:
                fig_sats = px.area(
                    timeline_df,
                    x='Time',
                    y='Total Sats',
                    title='Sats Zapped Over Time',
                    color_discrete_sequence=['#8B5CF6']
                )
                fig_sats.update_layout(height=300)
                st.plotly_chart(fig_sats, width="stretch")

        st.divider()

        # Top zappers and recipients
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💸 Top Zappers")

            top_zappers = (
                session.query(
                    Zap.sender_pubkey,
                    func.count(Zap.id).label('zap_count'),
                    func.sum(Zap.amount_sats).label('total_sats')
                )
                .filter(Zap.sender_pubkey.isnot(None))
                .filter(Zap.created_at >= cutoff)
                .group_by(Zap.sender_pubkey)
                .order_by(func.sum(Zap.amount_sats).desc())
                .limit(10)
                .all()
            )

            if top_zappers:
                zappers_df = pd.DataFrame([
                    {
                        'Rank': i+1,
                        'Pubkey': pubkey[:16] + '...',
                        'Zaps': count,
                        'Total Sats': sats
                    }
                    for i, (pubkey, count, sats) in enumerate(top_zappers)
                ])

                fig_zappers = px.bar(
                    zappers_df,
                    x='Total Sats',
                    y='Pubkey',
                    orientation='h',
                    title='Most Generous Zappers',
                    color='Total Sats',
                    color_continuous_scale='Oranges'
                )
                fig_zappers.update_layout(yaxis={'categoryorder': 'total ascending'}, height=350)
                st.plotly_chart(fig_zappers, width="stretch")

        with col2:
            st.subheader("🎁 Top Recipients")

            top_recipients = (
                session.query(
                    Zap.target_pubkey,
                    func.count(Zap.id).label('zap_count'),
                    func.sum(Zap.amount_sats).label('total_sats')
                )
                .filter(Zap.created_at >= cutoff)
                .group_by(Zap.target_pubkey)
                .order_by(func.sum(Zap.amount_sats).desc())
                .limit(10)
                .all()
            )

            if top_recipients:
                recipients_df = pd.DataFrame([
                    {
                        'Rank': i+1,
                        'Pubkey': pubkey[:16] + '...',
                        'Zaps': count,
                        'Total Sats': sats
                    }
                    for i, (pubkey, count, sats) in enumerate(top_recipients)
                ])

                fig_recipients = px.bar(
                    recipients_df,
                    x='Total Sats',
                    y='Pubkey',
                    orientation='h',
                    title='Top Zap Recipients',
                    color='Total Sats',
                    color_continuous_scale='Purples'
                )
                fig_recipients.update_layout(yaxis={'categoryorder': 'total ascending'}, height=350)
                st.plotly_chart(fig_recipients, width="stretch")

        st.divider()

        # Zap size categories
        st.subheader("📊 Zap Size Categories")

        # Categorize zaps
        all_zaps = session.query(Zap.amount_sats).filter(Zap.created_at >= cutoff).all()

        if all_zaps:
            amounts = [z[0] for z in all_zaps]
            categories = {
                '🥉 Small (1-100 sats)': sum(1 for a in amounts if 1 <= a <= 100),
                '🥈 Medium (101-1000 sats)': sum(1 for a in amounts if 101 <= a <= 1000),
                '🥇 Large (1001-10000 sats)': sum(1 for a in amounts if 1001 <= a <= 10000),
                '💎 Huge (10000+ sats)': sum(1 for a in amounts if a > 10000),
            }

            fig_categories = px.pie(
                values=list(categories.values()),
                names=list(categories.keys()),
                title=f'Zap Size Distribution ({time_window}h)',
                color_discrete_sequence=['#FDE68A', '#FCD34D', '#FBBF24', '#F59E0B']
            )
            fig_categories.update_layout(height=400)
            st.plotly_chart(fig_categories, width="stretch")

except Exception as e:
    st.error(f"Error loading zap data: {str(e)}")
    st.exception(e)

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh", value=False, key="zap_refresh"):
    import time
    refresh_interval = st.sidebar.slider("Interval (seconds)", 10, 120, 60)
    time.sleep(refresh_interval)
    st.rerun()
