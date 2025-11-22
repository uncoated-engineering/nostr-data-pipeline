"""User Analytics - Top users and leaderboards."""

import streamlit as st
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.models import UserProfile, ContentMetrics, Zap
from sqlalchemy import func, desc

st.set_page_config(page_title="Users", page_icon="👥", layout="wide")

@st.cache_resource
def get_db_manager():
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

st.title("👥 User Analytics")
st.markdown("Top contributors and user leaderboards")

st.divider()

try:
    with get_db_manager().get_session() as session:
        # Top Zap Recipients
        st.subheader("⚡ Top Zap Recipients")

        top_recipients = (
            session.query(
                Zap.target_pubkey,
                func.count(Zap.id).label('zap_count'),
                func.sum(Zap.amount_sats).label('total_sats')
            )
            .group_by(Zap.target_pubkey)
            .order_by(desc('total_sats'))
            .limit(20)
            .all()
        )

        if top_recipients:
            recipients_data = []
            for pubkey, zap_count, total_sats in top_recipients:
                profile = session.query(UserProfile).filter_by(pubkey=pubkey).first()
                recipients_data.append({
                    'Pubkey': pubkey[:16] + '...',
                    'Name': profile.name if profile and profile.name else 'Unknown',
                    'Zap Count': zap_count,
                    'Total Sats': total_sats,
                    'Avg Zap': total_sats // zap_count if zap_count > 0 else 0
                })

            recipients_df = pd.DataFrame(recipients_data)
            recipients_df.insert(0, 'Rank', range(1, len(recipients_df) + 1))

            col1, col2 = st.columns([2, 1])

            with col1:
                fig = px.bar(
                    recipients_df.head(15),
                    x='Total Sats',
                    y='Name',
                    orientation='h',
                    title='Top 15 Zap Recipients by Total Sats',
                    color='Total Sats',
                    color_continuous_scale='Purples',
                    hover_data=['Zap Count', 'Avg Zap']
                )
                fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500)
                st.plotly_chart(fig, width="stretch")

            with col2:
                st.dataframe(
                    recipients_df,
                    width="stretch",
                    hide_index=True,
                    height=500,
                    column_config={
                        "Total Sats": st.column_config.NumberColumn(format="%d"),
                        "Zap Count": st.column_config.NumberColumn(format="%d"),
                        "Avg Zap": st.column_config.NumberColumn(format="%d"),
                    }
                )

        st.divider()

        # Top Content Creators
        st.subheader("📝 Top Content Creators")

        top_creators = (
            session.query(
                ContentMetrics.author_pubkey,
                func.count(ContentMetrics.event_id).label('post_count'),
                func.sum(ContentMetrics.zap_total_sats).label('total_sats'),
                func.avg(ContentMetrics.virality_score).label('avg_virality')
            )
            .group_by(ContentMetrics.author_pubkey)
            .order_by(desc('total_sats'))
            .limit(20)
            .all()
        )

        if top_creators:
            creators_data = []
            for pubkey, post_count, total_sats, avg_virality in top_creators:
                profile = session.query(UserProfile).filter_by(pubkey=pubkey).first()
                creators_data.append({
                    'Pubkey': pubkey[:16] + '...',
                    'Name': profile.name if profile and profile.name else 'Unknown',
                    'Posts': post_count,
                    'Total Sats': total_sats or 0,
                    'Avg Virality': round(avg_virality or 0, 2)
                })

            creators_df = pd.DataFrame(creators_data)
            creators_df.insert(0, 'Rank', range(1, len(creators_df) + 1))

            col1, col2 = st.columns(2)

            with col1:
                fig_creators = px.scatter(
                    creators_df,
                    x='Posts',
                    y='Avg Virality',
                    size='Total Sats',
                    color='Total Sats',
                    hover_name='Name',
                    title='Content Quality vs Volume',
                    labels={'Posts': 'Number of Posts', 'Avg Virality': 'Average Virality Score'},
                    color_continuous_scale='Viridis'
                )
                fig_creators.update_layout(height=400)
                st.plotly_chart(fig_creators, width="stretch")

            with col2:
                fig_pie = px.pie(
                    creators_df.head(10),
                    values='Total Sats',
                    names='Name',
                    title='Sats Distribution (Top 10 Creators)'
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, width="stretch")

            st.dataframe(
                creators_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Posts": st.column_config.NumberColumn(format="%d"),
                    "Total Sats": st.column_config.NumberColumn(format="%d"),
                    "Avg Virality": st.column_config.ProgressColumn(
                        format="%.2f",
                        min_value=0,
                        max_value=float(creators_df['Avg Virality'].max()),
                    ),
                }
            )

        st.divider()

        # User Search
        st.subheader("🔍 User Lookup")
        pubkey_input = st.text_input("Enter pubkey (partial match supported)")

        if pubkey_input and len(pubkey_input) >= 8:
            profiles = (
                session.query(UserProfile)
                .filter(UserProfile.pubkey.like(f"%{pubkey_input}%"))
                .limit(10)
                .all()
            )

            if profiles:
                for profile in profiles:
                    with st.expander(f"{profile.name or 'Unknown'} ({profile.pubkey[:16]}...)"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Pubkey:** `{profile.pubkey}`")
                            st.write(f"**Name:** {profile.name or 'N/A'}")
                            st.write(f"**Display Name:** {profile.display_name or 'N/A'}")
                            st.write(f"**NIP-05:** {profile.nip05 or 'N/A'}")
                            st.write(f"**First Seen:** {profile.first_seen}")
                            st.write(f"**Last Updated:** {profile.last_updated}")

                        with col2:
                            # Get user stats
                            zaps_received = (
                                session.query(
                                    func.count(Zap.id),
                                    func.sum(Zap.amount_sats)
                                )
                                .filter_by(target_pubkey=profile.pubkey)
                                .first()
                            )

                            posts = (
                                session.query(func.count(ContentMetrics.event_id))
                                .filter_by(author_pubkey=profile.pubkey)
                                .scalar()
                            )

                            st.write(f"**Posts:** {posts or 0}")
                            st.write(f"**Zaps Received:** {zaps_received[0] or 0}")
                            st.write(f"**Total Sats:** {zaps_received[1] or 0:,}")
            else:
                st.info("No users found matching that pubkey.")

except Exception as e:
    st.error(f"Error loading user data: {str(e)}")
    st.exception(e)
