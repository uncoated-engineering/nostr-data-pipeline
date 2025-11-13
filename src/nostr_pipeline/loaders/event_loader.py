"""Event loader for persisting Nostr events to database."""

from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func

from nostr_pipeline.models import (
    NostrEvent,
    UserProfile,
    Zap,
    ContentMetrics,
    TrendingTopic,
    RelayMetrics,
    NetworkStats,
)
from nostr_pipeline.loaders.database import DatabaseManager

logger = structlog.get_logger()


class EventLoader:
    """Load processed events into the database."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.log = logger.bind(component="event_loader")

    def save_event(self, session: Session, event_data: Dict[str, Any]) -> bool:
        """Save a raw Nostr event."""
        try:
            event = NostrEvent(
                id=event_data["id"],
                pubkey=event_data["pubkey"],
                created_at=event_data["created_at"],
                kind=event_data["kind"],
                content=event_data["content"],
                sig=event_data["sig"],
                tags=event_data["tags"],
                relay_url=event_data["relay_url"],
                received_at=event_data["received_at"],
                processed=False,
            )

            # Use INSERT ... ON CONFLICT DO NOTHING for PostgreSQL
            # For SQLite, just try to insert and ignore duplicates
            session.merge(event)
            return True

        except Exception as e:
            self.log.error("save_event_failed", error=str(e), event_id=event_data.get("id"))
            return False

    def save_user_profile(self, session: Session, profile_data: Dict[str, Any]) -> bool:
        """Save or update user profile."""
        try:
            # Check if profile exists
            existing = session.query(UserProfile).filter_by(
                pubkey=profile_data["pubkey"]
            ).first()

            if existing:
                # Update existing profile
                for key, value in profile_data.items():
                    if key != "pubkey" and value is not None:
                        setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
            else:
                # Create new profile
                profile = UserProfile(**profile_data)
                session.add(profile)

            return True

        except Exception as e:
            self.log.error(
                "save_profile_failed",
                error=str(e),
                pubkey=profile_data.get("pubkey"),
            )
            return False

    def save_zap(self, session: Session, zap_data: Dict[str, Any]) -> bool:
        """Save a zap receipt."""
        try:
            zap = Zap(
                id=zap_data["id"],
                target_event_id=zap_data.get("target_event_id"),
                target_pubkey=zap_data["target_pubkey"],
                sender_pubkey=zap_data.get("sender_pubkey"),
                amount_msats=zap_data["amount_msats"],
                amount_sats=zap_data["amount_sats"],
                comment=zap_data.get("comment"),
                created_at=zap_data["created_at"],
                bolt11=zap_data.get("bolt11"),
                preimage=zap_data.get("preimage"),
                relay_url=zap_data["relay_url"],
                received_at=zap_data["received_at"],
            )

            session.merge(zap)
            return True

        except Exception as e:
            self.log.error("save_zap_failed", error=str(e), zap_id=zap_data.get("id"))
            return False

    def update_content_metrics(
        self,
        session: Session,
        event_id: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """Update or create content metrics."""
        try:
            # Check if metrics exist
            existing = session.query(ContentMetrics).filter_by(event_id=event_id).first()

            if existing:
                # Update existing metrics
                for key, value in metrics.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
            else:
                # Create new metrics
                metrics_obj = ContentMetrics(event_id=event_id, **metrics)
                session.add(metrics_obj)

            return True

        except Exception as e:
            self.log.error("update_metrics_failed", error=str(e), event_id=event_id)
            return False

    def save_trending_topic(self, session: Session, topic_data: Dict[str, Any]) -> bool:
        """Save trending topic data."""
        try:
            topic = TrendingTopic(**topic_data)
            session.add(topic)
            return True

        except Exception as e:
            self.log.error("save_trending_failed", error=str(e))
            return False

    def save_relay_metrics(self, session: Session, metrics_data: Dict[str, Any]) -> bool:
        """Save relay health metrics."""
        try:
            metrics = RelayMetrics(**metrics_data)
            session.add(metrics)
            return True

        except Exception as e:
            self.log.error("save_relay_metrics_failed", error=str(e))
            return False

    def save_network_stats(self, session: Session, stats_data: Dict[str, Any]) -> bool:
        """Save network-wide statistics."""
        try:
            stats = NetworkStats(**stats_data)
            session.add(stats)
            return True

        except Exception as e:
            self.log.error("save_network_stats_failed", error=str(e))
            return False

    def batch_save_events(
        self,
        session: Session,
        events: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Save multiple events in batch."""
        stats = {"saved": 0, "failed": 0, "duplicates": 0}

        for event_data in events:
            if self.save_event(session, event_data):
                stats["saved"] += 1
            else:
                stats["failed"] += 1

        return stats

    def get_event_by_id(self, session: Session, event_id: str) -> Optional[NostrEvent]:
        """Retrieve an event by ID."""
        return session.query(NostrEvent).filter_by(id=event_id).first()

    def get_user_profile(self, session: Session, pubkey: str) -> Optional[UserProfile]:
        """Retrieve user profile by pubkey."""
        return session.query(UserProfile).filter_by(pubkey=pubkey).first()

    def get_content_metrics(self, session: Session, event_id: str) -> Optional[ContentMetrics]:
        """Retrieve content metrics for an event."""
        return session.query(ContentMetrics).filter_by(event_id=event_id).first()

    def get_unprocessed_events(
        self,
        session: Session,
        limit: int = 1000,
    ) -> List[NostrEvent]:
        """Get events that haven't been processed yet."""
        return (
            session.query(NostrEvent)
            .filter_by(processed=False)
            .order_by(NostrEvent.received_at)
            .limit(limit)
            .all()
        )

    def mark_events_processed(self, session: Session, event_ids: List[str]) -> int:
        """Mark events as processed."""
        count = (
            session.query(NostrEvent)
            .filter(NostrEvent.id.in_(event_ids))
            .update({"processed": True}, synchronize_session=False)
        )
        return count

    def get_top_content_by_zaps(
        self,
        session: Session,
        limit: int = 10,
        hours: int = 24,
    ) -> List[ContentMetrics]:
        """Get top content by zap amount in the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return (
            session.query(ContentMetrics)
            .filter(ContentMetrics.created_at >= cutoff_time)
            .order_by(ContentMetrics.zap_total_sats.desc())
            .limit(limit)
            .all()
        )

    def get_trending_hashtags(
        self,
        session: Session,
        limit: int = 10,
        hours: int = 24,
    ) -> List[TrendingTopic]:
        """Get trending hashtags in the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return (
            session.query(TrendingTopic)
            .filter(TrendingTopic.window_start >= cutoff_time)
            .order_by(TrendingTopic.trend_score.desc())
            .limit(limit)
            .all()
        )

    def get_latest_network_stats(self, session: Session) -> Optional[NetworkStats]:
        """Get the most recent network statistics."""
        return (
            session.query(NetworkStats)
            .order_by(NetworkStats.timestamp.desc())
            .first()
        )

    def cleanup_old_data(self, session: Session, days: int = 30) -> Dict[str, int]:
        """Clean up data older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stats = {}

        # Clean up old events
        events_deleted = (
            session.query(NostrEvent)
            .filter(NostrEvent.created_at < cutoff_date)
            .delete(synchronize_session=False)
        )
        stats["events_deleted"] = events_deleted

        # Clean up old relay metrics
        relay_metrics_deleted = (
            session.query(RelayMetrics)
            .filter(RelayMetrics.timestamp < cutoff_date)
            .delete(synchronize_session=False)
        )
        stats["relay_metrics_deleted"] = relay_metrics_deleted

        # Clean up old trending topics
        topics_deleted = (
            session.query(TrendingTopic)
            .filter(TrendingTopic.window_end < cutoff_date)
            .delete(synchronize_session=False)
        )
        stats["topics_deleted"] = topics_deleted

        return stats


from datetime import timedelta
