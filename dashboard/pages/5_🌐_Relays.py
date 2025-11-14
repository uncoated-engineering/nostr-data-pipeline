"""Relay Health - Monitor relay performance."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery

st.set_page_config(page_title="Relays", page_icon="🌐", layout="wide")

@st.cache_resource
def get_db_manager():
    db_manager = DatabaseManager()
    db_manager.initialize()
    return db_manager

st.title("🌐 Relay Health Monitor")
st.markdown("Monitor relay performance and connectivity")

st.divider()

try:
    with get_db_manager().get_session() as session:
        query = AnalyticsQuery()
        relay_health = query.get_relay_health(session)

        if relay_health:
            # Relay overview
            st.subheader("📊 Relay Overview")

            col1, col2, col3, col4 = st.columns(4)

            total_relays = len(relay_health)
            connected_relays = sum(1 for r in relay_health if r['is_connected'])
            avg_latency = sum(r['latency_ms'] for r in relay_health if r['latency_ms']) / max(connected_relays, 1)
            total_events = sum(r['events_received'] for r in relay_health)

            with col1:
                st.metric("Total Relays", total_relays)

            with col2:
                st.metric(
                    "Connected",
                    connected_relays,
                    delta=f"{(connected_relays/total_relays*100):.0f}%" if total_relays > 0 else "0%"
                )

            with col3:
                st.metric("Avg Latency", f"{avg_latency:.0f}ms")

            with col4:
                st.metric("Total Events", f"{total_events:,}")

            st.divider()

            # Relay status table
            st.subheader("🔌 Relay Status")

            relay_df = pd.DataFrame(relay_health)
            relay_df['relay_name'] = relay_df['relay_url'].str.replace('wss://', '').str.replace('ws://', '')
            relay_df['status'] = relay_df['is_connected'].apply(lambda x: '🟢 Online' if x else '🔴 Offline')

            display_df = relay_df[['relay_name', 'status', 'latency_ms', 'events_received', 'error_count']].copy()
            display_df.columns = ['Relay', 'Status', 'Latency (ms)', 'Events', 'Errors']

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Latency (ms)": st.column_config.NumberColumn(format="%.0f"),
                    "Events": st.column_config.NumberColumn(format="%d"),
                    "Errors": st.column_config.NumberColumn(format="%d"),
                }
            )

            st.divider()

            # Visualizations
            col1, col2 = st.columns(2)

            with col1:
                # Latency comparison
                connected_relays_df = relay_df[relay_df['is_connected']].copy()
                if not connected_relays_df.empty:
                    fig_latency = px.bar(
                        connected_relays_df,
                        x='relay_name',
                        y='latency_ms',
                        title='Relay Latency Comparison',
                        labels={'latency_ms': 'Latency (ms)', 'relay_name': 'Relay'},
                        color='latency_ms',
                        color_continuous_scale='RdYlGn_r'
                    )
                    fig_latency.update_layout(height=400, xaxis_tickangle=-45)
                    st.plotly_chart(fig_latency, use_container_width=True)

            with col2:
                # Event distribution
                fig_events = px.pie(
                    relay_df,
                    values='events_received',
                    names='relay_name',
                    title='Event Distribution by Relay'
                )
                fig_events.update_layout(height=400)
                st.plotly_chart(fig_events, use_container_width=True)

            # Performance matrix
            st.subheader("📈 Performance Matrix")

            fig_scatter = px.scatter(
                relay_df,
                x='latency_ms',
                y='events_received',
                size='error_count',
                color='is_connected',
                hover_name='relay_name',
                title='Relay Performance: Latency vs Events',
                labels={
                    'latency_ms': 'Latency (ms)',
                    'events_received': 'Events Received',
                    'error_count': 'Errors',
                    'is_connected': 'Connected'
                },
                color_discrete_map={True: '#10B981', False: '#EF4444'}
            )
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)

            # Health scores
            st.subheader("💚 Health Scores")

            # Calculate health score for each relay
            for relay in relay_df.to_dict('records'):
                with st.expander(f"{relay['relay_name']} - {'🟢' if relay['is_connected'] else '🔴'}"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Status", "Connected" if relay['is_connected'] else "Disconnected")
                        st.metric("Latency", f"{relay['latency_ms']:.0f}ms" if relay['latency_ms'] else "N/A")

                    with col2:
                        st.metric("Events Received", f"{relay['events_received']:,}")
                        st.metric("Events/Second", f"{relay['events_per_second']:.2f}" if relay['events_per_second'] else "0")

                    with col3:
                        st.metric("Errors", relay['error_count'])
                        if relay['last_error']:
                            st.caption(f"Last error: {relay['last_error'][:50]}...")

                    # Health score gauge
                    if relay['is_connected']:
                        # Simple health score based on latency and errors
                        latency_score = max(0, 100 - (relay['latency_ms'] or 0) / 10)
                        error_score = max(0, 100 - relay['error_count'] * 5)
                        health_score = (latency_score + error_score) / 2

                        fig_health = go.Figure(go.Indicator(
                            mode="gauge+number",
                            value=health_score,
                            title={'text': "Health Score"},
                            gauge={
                                'axis': {'range': [0, 100]},
                                'bar': {'color': "#10B981" if health_score > 70 else "#F59E0B" if health_score > 40 else "#EF4444"},
                                'steps': [
                                    {'range': [0, 40], 'color': "#FEE2E2"},
                                    {'range': [40, 70], 'color': "#FEF3C7"},
                                    {'range': [70, 100], 'color': "#D1FAE5"}
                                ]
                            }
                        ))
                        fig_health.update_layout(height=200)
                        st.plotly_chart(fig_health, use_container_width=True)

        else:
            st.warning("No relay health data available yet.")

except Exception as e:
    st.error(f"Error loading relay data: {str(e)}")
    st.exception(e)

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh", value=True, key="relay_refresh"):
    import time
    refresh_interval = st.sidebar.slider("Interval (seconds)", 10, 120, 30)
    time.sleep(refresh_interval)
    st.rerun()
