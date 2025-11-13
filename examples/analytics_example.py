"""Example analytics queries using the Nostr Pipeline."""

from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery


def main():
    """Run example analytics queries."""
    # Initialize database connection
    db_manager = DatabaseManager()
    db_manager.initialize()

    with db_manager.get_session() as session:
        query = AnalyticsQuery()

        print("=" * 60)
        print("NOSTR DATA PIPELINE - ANALYTICS EXAMPLES")
        print("=" * 60)

        # 1. Network Overview
        print("\n📊 NETWORK OVERVIEW")
        print("-" * 60)
        overview = query.get_network_overview(session)
        if overview:
            print(f"Total Users: {overview['users']['total']:,}")
            print(f"Active Users (24h): {overview['users']['active_24h']:,}")
            print(f"New Users (24h): {overview['users']['new_24h']:,}")
            print(f"Total Events: {overview['events']['total']:,}")
            print(f"Events (24h): {overview['events']['events_24h']:,}")
            print(f"Total Sats Zapped: {overview['zaps']['total_sats']:,}")
            print(f"Sats Zapped (24h): {overview['zaps']['sats_24h']:,}")
        else:
            print("No data available yet.")

        # 2. Trending Hashtags
        print("\n🔥 TRENDING HASHTAGS (Last 24 Hours)")
        print("-" * 60)
        trending = query.get_trending_hashtags(session, hours=24, limit=10)
        for i, topic in enumerate(trending, 1):
            print(
                f"{i:2}. #{topic['hashtag']:20} "
                f"{topic['mention_count']:4} mentions  "
                f"{topic['unique_authors']:3} authors  "
                f"Score: {topic['trend_score']:.1f}"
            )

        # 3. Top Zapped Content
        print("\n⚡ TOP ZAPPED CONTENT (Last 24 Hours)")
        print("-" * 60)
        top_content = query.get_top_zapped_content(session, hours=24, limit=10)
        for i, content in enumerate(top_content, 1):
            event_id_short = content['event_id'][:16]
            print(
                f"{i:2}. {event_id_short}...  "
                f"{content['zap_total_sats']:6,} sats  "
                f"{content['zap_count']:3} zaps  "
                f"{content['reply_count']:3} replies  "
                f"Score: {content['virality_score']:.1f}"
            )

        # 4. Zap Distribution
        print("\n💰 ZAP DISTRIBUTION (Last 24 Hours)")
        print("-" * 60)
        zap_dist = query.get_zap_distribution(session, hours=24)
        if zap_dist['count'] > 0:
            print(f"Total Zaps: {zap_dist['count']:,}")
            print(f"Total Amount: {zap_dist['total']:,} sats")
            print(f"Mean: {zap_dist['mean']:.0f} sats")
            print(f"Median: {zap_dist['median']} sats")
            print(f"Min: {zap_dist['min']} sats")
            print(f"Max: {zap_dist['max']:,} sats")
            print(f"95th Percentile: {zap_dist['p95']:,} sats")
        else:
            print("No zaps recorded yet.")

        # 5. Relay Health
        print("\n🌐 RELAY HEALTH")
        print("-" * 60)
        relays = query.get_relay_health(session)
        for relay in relays:
            status = "✓" if relay['is_connected'] else "✗"
            url = relay['relay_url'].replace('wss://', '')
            latency = f"{relay['latency_ms']:.0f}ms" if relay['latency_ms'] else "N/A"
            print(
                f"{status} {url:30} "
                f"Latency: {latency:6}  "
                f"Events: {relay['events_received']:6,}  "
                f"Errors: {relay['error_count']}"
            )

        # 6. Activity Timeline
        print("\n📈 ACTIVITY TIMELINE (Last 6 Hours)")
        print("-" * 60)
        timeline = query.get_activity_timeline(session, hours=6, interval_minutes=60)
        for entry in timeline[-6:]:  # Last 6 hours
            timestamp = entry['timestamp'][:16].replace('T', ' ')
            metrics = entry['metrics']
            total = sum(metrics.values())
            print(
                f"{timestamp}  "
                f"Notes: {metrics['notes']:4}  "
                f"Reactions: {metrics['reactions']:4}  "
                f"Zaps: {metrics['zaps']:4}  "
                f"Total: {total:5}"
            )

        print("\n" + "=" * 60)
        print("Analytics complete!")


if __name__ == "__main__":
    main()
