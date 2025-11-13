"""Analytics query interface for retrieving insights."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from nostr_pipeline.models import (
    NostrEvent,
    UserProfile,
    Zap,
    ContentMetrics,
    TrendingTopic,
    RelayMetrics,
    NetworkStats,
)

logger = structlog.get_logger()


class AnalyticsQuery:
    """Query interface for analytics data."""

    def __init__(self):
        self.log = logger.bind(component="analytics_query")

    def get_top_zapped_content(
        self,
        session: Session,
        hours: int = 24,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top content by zap amount."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        results = (
            session.query(ContentMetrics)
            .filter(ContentMetrics.created_at >= cutoff)
            .order_by(desc(ContentMetrics.zap_total_sats))
            .limit(limit)
            .all()
        )

        return [
            {
                "event_id": r.event_id,
                "author_pubkey": r.author_pubkey,
                "zap_total_sats": r.zap_total_sats,
                "zap_count": r.zap_count,
                "reply_count": r.reply_count,
                "repost_count": r.repost_count,
                "virality_score": r.virality_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ]

    def get_trending_hashtags(
        self,
        session: Session,
        hours: int = 24,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get trending hashtags."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        results = (
            session.query(TrendingTopic)
            .filter(TrendingTopic.window_start >= cutoff)
            .order_by(desc(TrendingTopic.trend_score))
            .limit(limit)
            .all()
        )

        return [
            {
                "hashtag": r.hashtag,
                "mention_count": r.mention_count,
                "unique_authors": r.unique_authors,
                "total_zaps": r.total_zaps,
                "trend_score": r.trend_score,
                "sample_events": r.sample_event_ids,
            }
            for r in results
        ]

    def get_network_overview(self, session: Session) -> Dict[str, Any]:
        """Get current network overview."""
        latest_stats = (
            session.query(NetworkStats)
            .order_by(desc(NetworkStats.timestamp))
            .first()
        )

        if not latest_stats:
            return {}

        return {
            "timestamp": latest_stats.timestamp.isoformat(),
            "users": {
                "total": latest_stats.total_users,
                "active_1h": latest_stats.active_users_1h,
                "active_24h": latest_stats.active_users_24h,
                "new_24h": latest_stats.new_users_24h,
            },
            "events": {
                "total": latest_stats.total_events,
                "events_1h": latest_stats.events_1h,
                "events_24h": latest_stats.events_24h,
                "notes_24h": latest_stats.notes_24h,
            },
            "zaps": {
                "total": latest_stats.total_zaps,
                "zaps_24h": latest_stats.zaps_24h,
                "total_sats": latest_stats.total_sats_zapped,
                "sats_24h": latest_stats.sats_zapped_24h,
            },
            "top_content": {
                "event_id": latest_stats.top_event_id,
                "zaps": latest_stats.top_event_zaps,
            },
        }

    def get_user_stats(
        self,
        session: Session,
        pubkey: str,
    ) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific user."""
        profile = session.query(UserProfile).filter_by(pubkey=pubkey).first()
        if not profile:
            return None

        # Count events by user
        event_count = session.query(NostrEvent).filter_by(pubkey=pubkey).count()

        # Get zaps received
        zaps_received = (
            session.query(func.sum(Zap.amount_sats), func.count(Zap.id))
            .filter_by(target_pubkey=pubkey)
            .first()
        )
        total_zaps_sats = zaps_received[0] or 0
        zap_count = zaps_received[1] or 0

        # Get zaps sent
        zaps_sent = (
            session.query(func.sum(Zap.amount_sats), func.count(Zap.id))
            .filter_by(sender_pubkey=pubkey)
            .first()
        )
        total_zaps_sent_sats = zaps_sent[0] or 0
        zaps_sent_count = zaps_sent[1] or 0

        # Get top content
        top_content = (
            session.query(ContentMetrics)
            .filter_by(author_pubkey=pubkey)
            .order_by(desc(ContentMetrics.virality_score))
            .limit(5)
            .all()
        )

        return {
            "pubkey": pubkey,
            "profile": {
                "name": profile.name,
                "display_name": profile.display_name,
                "about": profile.about,
                "nip05": profile.nip05,
                "picture": profile.picture,
            },
            "activity": {
                "total_events": event_count,
                "first_seen": profile.first_seen.isoformat(),
                "last_updated": profile.last_updated.isoformat(),
            },
            "zaps": {
                "received_count": zap_count,
                "received_sats": total_zaps_sats,
                "sent_count": zaps_sent_count,
                "sent_sats": total_zaps_sent_sats,
            },
            "top_content": [
                {
                    "event_id": c.event_id,
                    "virality_score": c.virality_score,
                    "zap_total_sats": c.zap_total_sats,
                }
                for c in top_content
            ],
        }

    def get_relay_health(self, session: Session) -> List[Dict[str, Any]]:
        """Get health metrics for all relays."""
        # Get latest metrics for each relay
        subq = (
            session.query(
                RelayMetrics.relay_url,
                func.max(RelayMetrics.timestamp).label("max_timestamp"),
            )
            .group_by(RelayMetrics.relay_url)
            .subquery()
        )

        results = (
            session.query(RelayMetrics)
            .join(
                subq,
                (RelayMetrics.relay_url == subq.c.relay_url)
                & (RelayMetrics.timestamp == subq.c.max_timestamp),
            )
            .all()
        )

        return [
            {
                "relay_url": r.relay_url,
                "is_connected": r.is_connected,
                "latency_ms": r.connection_latency_ms,
                "events_received": r.events_received,
                "events_per_second": r.events_per_second,
                "error_count": r.error_count,
                "last_error": r.last_error,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]

    def get_zap_distribution(
        self,
        session: Session,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Get distribution of zap amounts."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        zaps = (
            session.query(Zap.amount_sats)
            .filter(Zap.created_at >= cutoff)
            .all()
        )

        amounts = [z[0] for z in zaps]

        if not amounts:
            return {
                "count": 0,
                "total": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
            }

        amounts_sorted = sorted(amounts)
        count = len(amounts_sorted)

        return {
            "count": count,
            "total": sum(amounts_sorted),
            "mean": sum(amounts_sorted) / count,
            "median": amounts_sorted[count // 2],
            "min": amounts_sorted[0],
            "max": amounts_sorted[-1],
            "p25": amounts_sorted[int(count * 0.25)],
            "p75": amounts_sorted[int(count * 0.75)],
            "p95": amounts_sorted[int(count * 0.95)],
        }

    def get_activity_timeline(
        self,
        session: Session,
        hours: int = 24,
        interval_minutes: int = 60,
    ) -> List[Dict[str, Any]]:
        """Get event activity over time."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # This is a simplified version - in production, use window functions
        events = (
            session.query(NostrEvent)
            .filter(NostrEvent.created_at >= cutoff)
            .all()
        )

        # Group by interval
        timeline = {}
        for event in events:
            # Round to nearest interval
            timestamp = event.created_at
            interval_start = timestamp.replace(
                minute=timestamp.minute // interval_minutes * interval_minutes,
                second=0,
                microsecond=0,
            )

            if interval_start not in timeline:
                timeline[interval_start] = {
                    "notes": 0,
                    "reactions": 0,
                    "zaps": 0,
                    "other": 0,
                }

            if event.kind == 1:
                timeline[interval_start]["notes"] += 1
            elif event.kind == 7:
                timeline[interval_start]["reactions"] += 1
            elif event.kind == 9735:
                timeline[interval_start]["zaps"] += 1
            else:
                timeline[interval_start]["other"] += 1

        # Convert to list
        result = []
        for timestamp in sorted(timeline.keys()):
            result.append({
                "timestamp": timestamp.isoformat(),
                "metrics": timeline[timestamp],
            })

        return result

    def search_events(
        self,
        session: Session,
        query: str,
        kind: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search events by content."""
        q = session.query(NostrEvent)

        if kind is not None:
            q = q.filter(NostrEvent.kind == kind)

        # Simple content search
        q = q.filter(NostrEvent.content.contains(query))

        results = q.order_by(desc(NostrEvent.created_at)).limit(limit).all()

        return [
            {
                "id": r.id,
                "pubkey": r.pubkey,
                "kind": r.kind,
                "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ]
