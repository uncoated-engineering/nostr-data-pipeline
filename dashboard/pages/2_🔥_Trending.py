"""Trending Content - Viral posts and trending hashtags."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery

st.set_page_config(page_title="Trending", page_icon="🔥", layout="wide")

@st.cache_resource
def get_db_manager():
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

st.title("🔥 Trending Content")
st.markdown("Discover what's hot on Nostr right now")

st.divider()

# Time window selector
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    time_window = st.selectbox(
        "Time Window",
        options=[6, 12, 24, 48, 72],
        index=2,
        format_func=lambda x: f"Last {x} hours"
    )
with col2:
    trending_limit = st.number_input("Top hashtags", min_value=5, max_value=50, value=20)
with col3:
    content_limit = st.number_input("Top content", min_value=5, max_value=50, value=10)

st.divider()

try:
    with get_db_manager().get_session() as session:
        query = AnalyticsQuery()

        # Trending Hashtags
        st.subheader("📊 Trending Hashtags")

        trending = query.get_trending_hashtags(session, hours=time_window, limit=trending_limit)

        if trending:
            # Create trending dataframe
            trending_df = pd.DataFrame(trending)

            col1, col2 = st.columns([3, 2])

            with col1:
                # Bar chart of trending hashtags
                fig_trending = px.bar(
                    trending_df.head(15),
                    x='trend_score',
                    y='hashtag',
                    orientation='h',
                    title=f'Top Trending Hashtags (Last {time_window}h)',
                    labels={'trend_score': 'Trend Score', 'hashtag': 'Hashtag'},
                    color='trend_score',
                    color_continuous_scale='Sunset',
                    hover_data=['mention_count', 'unique_authors', 'total_zaps']
                )
                fig_trending.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    height=500,
                    showlegend=False
                )
                fig_trending.update_traces(
                    hovertemplate='<b>#%{y}</b><br>' +
                                'Trend Score: %{x:.1f}<br>' +
                                'Mentions: %{customdata[0]}<br>' +
                                'Authors: %{customdata[1]}<br>' +
                                'Zaps: %{customdata[2]}<extra></extra>'
                )
                st.plotly_chart(fig_trending, use_container_width=True)

            with col2:
                # Treemap of hashtag mentions
                fig_tree = px.treemap(
                    trending_df.head(20),
                    path=['hashtag'],
                    values='mention_count',
                    title='Hashtag Mention Volume',
                    color='trend_score',
                    color_continuous_scale='Viridis',
                    hover_data=['unique_authors', 'total_zaps']
                )
                fig_tree.update_layout(height=500)
                fig_tree.update_traces(
                    textinfo='label+value',
                    hovertemplate='<b>#%{label}</b><br>' +
                                'Mentions: %{value}<br>' +
                                'Authors: %{customdata[0]}<br>' +
                                'Zaps: %{customdata[1]}<extra></extra>'
                )
                st.plotly_chart(fig_tree, use_container_width=True)

            # Trending hashtags table
            st.subheader("📋 Detailed Trending Hashtags")

            display_df = trending_df[['hashtag', 'mention_count', 'unique_authors', 'total_zaps', 'trend_score']].copy()
            display_df.columns = ['Hashtag', 'Mentions', 'Authors', 'Zaps', 'Trend Score']
            display_df['Hashtag'] = '#' + display_df['Hashtag']

            # Add rank column
            display_df.insert(0, 'Rank', range(1, len(display_df) + 1))

            # Style the dataframe
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rank": st.column_config.NumberColumn(format="%d"),
                    "Mentions": st.column_config.NumberColumn(format="%d"),
                    "Authors": st.column_config.NumberColumn(format="%d"),
                    "Zaps": st.column_config.NumberColumn(format="%d"),
                    "Trend Score": st.column_config.NumberColumn(format="%.2f"),
                }
            )

            # Scatter plot: mentions vs authors
            st.subheader("📈 Hashtag Engagement Analysis")
            fig_scatter = px.scatter(
                trending_df.head(30),
                x='unique_authors',
                y='mention_count',
                size='total_zaps',
                color='trend_score',
                hover_name='hashtag',
                title='Hashtag Reach vs Engagement',
                labels={
                    'unique_authors': 'Unique Authors',
                    'mention_count': 'Total Mentions',
                    'total_zaps': 'Total Zaps',
                    'trend_score': 'Trend Score'
                },
                color_continuous_scale='Plasma'
            )
            fig_scatter.update_traces(
                textposition='top center',
                hovertemplate='<b>#%{hovertext}</b><br>' +
                            'Authors: %{x}<br>' +
                            'Mentions: %{y}<br>' +
                            'Zaps: %{marker.size}<br>' +
                            'Score: %{marker.color:.1f}<extra></extra>'
            )
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)

        else:
            st.info("No trending hashtags found in this time window.")

        st.divider()

        # Top Zapped Content
        st.subheader("⚡ Top Zapped Content")

        top_content = query.get_top_zapped_content(session, hours=time_window, limit=content_limit)

        if top_content:
            # Create content dataframe
            content_df = pd.DataFrame(top_content)

            col1, col2 = st.columns([3, 2])

            with col1:
                # Bar chart of top zapped content
                content_df['event_short'] = content_df['event_id'].str[:12] + '...'
                fig_content = px.bar(
                    content_df,
                    x='zap_total_sats',
                    y='event_short',
                    orientation='h',
                    title=f'Most Zapped Content (Last {time_window}h)',
                    labels={'zap_total_sats': 'Total Sats', 'event_short': 'Event'},
                    color='virality_score',
                    color_continuous_scale='Reds',
                    hover_data=['zap_count', 'reply_count', 'repost_count']
                )
                fig_content.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    height=400,
                    showlegend=False
                )
                fig_content.update_traces(
                    hovertemplate='<b>%{y}</b><br>' +
                                'Sats: %{x:,.0f}<br>' +
                                'Zaps: %{customdata[0]}<br>' +
                                'Replies: %{customdata[1]}<br>' +
                                'Reposts: %{customdata[2]}<extra></extra>'
                )
                st.plotly_chart(fig_content, use_container_width=True)

            with col2:
                # Pie chart of engagement types
                total_engagement = content_df[['zap_count', 'reply_count', 'repost_count']].sum()
                engagement_data = pd.DataFrame({
                    'Type': ['Zaps', 'Replies', 'Reposts'],
                    'Count': [
                        total_engagement['zap_count'],
                        total_engagement['reply_count'],
                        total_engagement['repost_count']
                    ]
                })
                fig_engagement = px.pie(
                    engagement_data,
                    values='Count',
                    names='Type',
                    title='Engagement Distribution',
                    color_discrete_sequence=['#F59E0B', '#8B5CF6', '#EC4899']
                )
                fig_engagement.update_layout(height=400)
                st.plotly_chart(fig_engagement, use_container_width=True)

            # Content details table
            st.subheader("📋 Top Content Details")

            display_content = content_df[['event_id', 'zap_total_sats', 'zap_count', 'reply_count', 'repost_count', 'virality_score']].copy()
            display_content.columns = ['Event ID', 'Total Sats', 'Zaps', 'Replies', 'Reposts', 'Virality Score']
            display_content.insert(0, 'Rank', range(1, len(display_content) + 1))

            st.dataframe(
                display_content,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Event ID": st.column_config.TextColumn(width="medium"),
                    "Total Sats": st.column_config.NumberColumn(format="%d"),
                    "Zaps": st.column_config.NumberColumn(format="%d"),
                    "Replies": st.column_config.NumberColumn(format="%d"),
                    "Reposts": st.column_config.NumberColumn(format="%d"),
                    "Virality Score": st.column_config.ProgressColumn(
                        format="%.2f",
                        min_value=0,
                        max_value=display_content['Virality Score'].max()
                    ),
                }
            )

            # Virality vs Engagement scatter
            st.subheader("📊 Virality Analysis")
            content_df['total_engagement'] = content_df['zap_count'] + content_df['reply_count'] + content_df['repost_count']
            fig_virality = px.scatter(
                content_df,
                x='total_engagement',
                y='virality_score',
                size='zap_total_sats',
                color='zap_total_sats',
                hover_data=['event_id', 'zap_count', 'reply_count', 'repost_count'],
                title='Content Virality vs Total Engagement',
                labels={
                    'total_engagement': 'Total Engagement (zaps + replies + reposts)',
                    'virality_score': 'Virality Score',
                    'zap_total_sats': 'Total Sats'
                },
                color_continuous_scale='Hot'
            )
            fig_virality.update_layout(height=400)
            fig_virality.update_traces(
                hovertemplate='Event: %{customdata[0][:16]}...<br>' +
                            'Engagement: %{x}<br>' +
                            'Virality: %{y:.1f}<br>' +
                            'Sats: %{marker.size:,.0f}<extra></extra>'
            )
            st.plotly_chart(fig_virality, use_container_width=True)

        else:
            st.info("No zapped content found in this time window.")

        st.divider()

        # Summary Stats
        if trending and top_content:
            st.subheader("📈 Summary Statistics")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_hashtags = len(trending_df)
                st.metric("Trending Hashtags", total_hashtags)

            with col2:
                total_mentions = trending_df['mention_count'].sum()
                st.metric("Total Mentions", f"{total_mentions:,}")

            with col3:
                total_zaps_content = content_df['zap_total_sats'].sum()
                st.metric("Total Sats (Top Content)", f"{total_zaps_content:,}")

            with col4:
                avg_virality = content_df['virality_score'].mean()
                st.metric("Avg Virality Score", f"{avg_virality:.2f}")

except Exception as e:
    st.error(f"Error loading trending data: {str(e)}")
    st.exception(e)

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh", value=False):
    import time
    refresh_interval = st.sidebar.slider("Interval (seconds)", 10, 120, 60)
    time.sleep(refresh_interval)
    st.rerun()
