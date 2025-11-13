"""Metrics aggregator for computing analytics."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import func

from nostr_pipeline.models import (
    NostrEvent,
    UserProfile,
    Zap,
    ContentMetrics,
    TrendingTopic,
    NetworkStats,
)
from nostr_pipeline.transformers.metrics_calculator import MetricsCalculator
from nostr_pipeline.loaders.database import DatabaseManager

logger = structlog.get_logger()


class MetricsAggregator:
    """Aggregate metrics from raw events."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.metrics_calculator = MetricsCalculator()
        self.log = logger.bind(component="metrics_aggregator")

    async def run_aggregation(self, session: Session) -> Dict[str, int]:
        """Run all aggregation tasks."""
        self.log.info("starting_metrics_aggregation")

        stats = {
            "content_metrics_updated": 0,
            "trending_topics_found": 0,
            "network_stats_computed": False,
        }

        try:
            # Aggregate content metrics
            stats["content_metrics_updated"] = await self._aggregate_content_metrics(session)

            # Find trending topics
            stats["trending_topics_found"] = await self._aggregate_trending_topics(session)

            # Compute network statistics
            await self._compute_network_stats(session)
            stats["network_stats_computed"] = True

            session.commit()
            self.log.info("aggregation_completed", stats=stats)

        except Exception as e:
            session.rollback()
            self.log.error("aggregation_failed", error=str(e))
            raise

        return stats

    async def _aggregate_content_metrics(self, session: Session) -> int:
        """Aggregate engagement metrics for content."""
        self.log.debug("aggregating_content_metrics")

        # Get all text notes from last 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        events = (
            session.query(NostrEvent)
            .filter(
                NostrEvent.kind == 1,
                NostrEvent.created_at >= cutoff_date,
            )
            .all()
        )

        updated_count = 0

        for event in events:
            metrics = await self._compute_event_metrics(session, event)
            if metrics:
                # Update or create metrics record
                existing = (
                    session.query(ContentMetrics)
                    .filter_by(event_id=event.id)
                    .first()
                )

                if existing:
                    for key, value in metrics.items():
                        setattr(existing, key, value)
                    existing.last_updated = datetime.utcnow()
                else:
                    content_metrics = ContentMetrics(event_id=event.id, **metrics)
                    session.add(content_metrics)

                updated_count += 1

        return updated_count

    async def _compute_event_metrics(
        self,
        session: Session,
        event: NostrEvent,
    ) -> Dict[str, Any]:
        """Compute metrics for a single event."""
        event_id = event.id

        # Count zaps
        zaps = session.query(Zap).filter_by(target_event_id=event_id).all()
        zap_count = len(zaps)
        zap_total_sats = sum(z.amount_sats for z in zaps)

        # Count replies
        reply_count = (
            session.query(NostrEvent)
            .filter(NostrEvent.kind == 1)
            .filter(NostrEvent.tags.contains([["e", event_id]]))
            .count()
        )

        # Count reposts
        repost_count = (
            session.query(NostrEvent)
            .filter(NostrEvent.kind == 6)
            .filter(NostrEvent.tags.contains([["e", event_id]]))
            .count()
        )

        # Count reactions
        reaction_count = (
            session.query(NostrEvent)
            .filter(NostrEvent.kind == 7)
            .filter(NostrEvent.tags.contains([["e", event_id]]))
            .count()
        )

        # Parse content
        content = event.content
        content_length = len(content)

        # Extract hashtags from tags
        hashtags = []
        for tag in event.tags or []:
            if len(tag) >= 2 and tag[0] == "t":
                hashtags.append(tag[1].lower())

        # Extract mentioned pubkeys
        mentioned_pubkeys = []
        for tag in event.tags or []:
            if len(tag) >= 2 and tag[0] == "p":
                mentioned_pubkeys.append(tag[1])

        # Check for media
        urls = []
        media_urls = []
        import re

        url_pattern = re.compile(r"https?://[^\s]+")
        urls = url_pattern.findall(content)

        media_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}
        for url in urls:
            if any(url.lower().endswith(ext) for ext in media_extensions):
                media_urls.append(url)

        has_media = len(media_urls) > 0

        # Calculate age in hours
        age_hours = (datetime.utcnow() - event.created_at).total_seconds() / 3600

        # Calculate virality score
        virality_score = self.metrics_calculator.calculate_virality_score(
            zap_count=zap_count,
            zap_total_sats=zap_total_sats,
            reply_count=reply_count,
            repost_count=repost_count,
            reaction_count=reaction_count,
            age_hours=age_hours,
        )

        return {
            "author_pubkey": event.pubkey,
            "kind": event.kind,
            "created_at": event.created_at,
            "zap_count": zap_count,
            "zap_total_sats": zap_total_sats,
            "reply_count": reply_count,
            "repost_count": repost_count,
            "reaction_count": reaction_count,
            "content_length": content_length,
            "hashtag_count": len(hashtags),
            "hashtags": hashtags,
            "mentioned_pubkeys": mentioned_pubkeys,
            "has_media": has_media,
            "media_urls": media_urls if has_media else None,
            "virality_score": virality_score,
        }

    async def _aggregate_trending_topics(self, session: Session) -> int:
        """Identify and save trending hashtags."""
        self.log.debug("aggregating_trending_topics")

        # Time window for trending
        window_hours = 24
        window_start = datetime.utcnow() - timedelta(hours=window_hours)
        window_end = datetime.utcnow()

        # Get all content metrics with hashtags in window
        metrics = (
            session.query(ContentMetrics)
            .filter(
                ContentMetrics.created_at >= window_start,
                ContentMetrics.hashtags.isnot(None),
            )
            .all()
        )

        # Aggregate by hashtag
        hashtag_stats = defaultdict(lambda: {
            "count": 0,
            "authors": set(),
            "zaps": 0,
            "events": [],
        })

        for metric in metrics:
            if metric.hashtags:
                for hashtag in metric.hashtags:
                    hashtag_stats[hashtag]["count"] += 1
                    hashtag_stats[hashtag]["authors"].add(metric.author_pubkey)
                    hashtag_stats[hashtag]["zaps"] += metric.zap_total_sats or 0
                    hashtag_stats[hashtag]["events"].append(metric.event_id)

        # Calculate trend scores and save
        trending_count = 0

        for hashtag, stats in hashtag_stats.items():
            unique_authors = len(stats["authors"])
            mention_count = stats["count"]
            total_zaps = stats["zaps"]

            # Skip low-volume hashtags
            if mention_count < 3:
                continue

            trend_score = self.metrics_calculator.calculate_trend_score(
                mention_count=mention_count,
                unique_authors=unique_authors,
                total_zaps=total_zaps,
                window_hours=window_hours,
            )

            # Sample events (top 5)
            sample_events = stats["events"][:5]

            trending_topic = TrendingTopic(
                hashtag=hashtag,
                mention_count=mention_count,
                unique_authors=unique_authors,
                total_zaps=total_zaps,
                window_start=window_start,
                window_end=window_end,
                trend_score=trend_score,
                sample_event_ids=sample_events,
            )

            session.add(trending_topic)
            trending_count += 1

        return trending_count

    async def _compute_network_stats(self, session: Session) -> None:
        """Compute network-wide statistics."""
        self.log.debug("computing_network_stats")

        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        twenty_four_hours_ago = now - timedelta(hours=24)

        # User metrics
        total_users = session.query(UserProfile).count()

        active_users_1h = (
            session.query(NostrEvent.pubkey)
            .filter(NostrEvent.created_at >= one_hour_ago)
            .distinct()
            .count()
        )

        active_users_24h = (
            session.query(NostrEvent.pubkey)
            .filter(NostrEvent.created_at >= twenty_four_hours_ago)
            .distinct()
            .count()
        )

        new_users_24h = (
            session.query(UserProfile)
            .filter(UserProfile.first_seen >= twenty_four_hours_ago)
            .count()
        )

        # Event metrics
        total_events = session.query(NostrEvent).count()

        events_1h = (
            session.query(NostrEvent)
            .filter(NostrEvent.created_at >= one_hour_ago)
            .count()
        )

        events_24h = (
            session.query(NostrEvent)
            .filter(NostrEvent.created_at >= twenty_four_hours_ago)
            .count()
        )

        notes_24h = (
            session.query(NostrEvent)
            .filter(
                NostrEvent.kind == 1,
                NostrEvent.created_at >= twenty_four_hours_ago,
            )
            .count()
        )

        # Zap metrics
        total_zaps = session.query(Zap).count()

        zaps_24h = (
            session.query(Zap)
            .filter(Zap.created_at >= twenty_four_hours_ago)
            .count()
        )

        total_sats = session.query(func.sum(Zap.amount_sats)).scalar() or 0

        sats_24h = (
            session.query(func.sum(Zap.amount_sats))
            .filter(Zap.created_at >= twenty_four_hours_ago)
            .scalar()
            or 0
        )

        # Top content in last 24h
        top_content = (
            session.query(ContentMetrics)
            .filter(ContentMetrics.created_at >= twenty_four_hours_ago)
            .order_by(ContentMetrics.zap_total_sats.desc())
            .first()
        )

        # Create network stats record
        stats = NetworkStats(
            timestamp=now,
            total_users=total_users,
            active_users_1h=active_users_1h,
            active_users_24h=active_users_24h,
            new_users_24h=new_users_24h,
            total_events=total_events,
            events_1h=events_1h,
            events_24h=events_24h,
            notes_24h=notes_24h,
            total_zaps=total_zaps,
            zaps_24h=zaps_24h,
            total_sats_zapped=total_sats,
            sats_zapped_24h=sats_24h,
            top_event_id=top_content.event_id if top_content else None,
            top_event_zaps=top_content.zap_total_sats if top_content else 0,
        )

        session.add(stats)
