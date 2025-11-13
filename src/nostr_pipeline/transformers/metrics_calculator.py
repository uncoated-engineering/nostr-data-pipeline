"""Metrics calculator for computing engagement and virality scores."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import math
import structlog

logger = structlog.get_logger()


class MetricsCalculator:
    """Calculate various metrics and scores for Nostr content."""

    def __init__(self):
        self.log = logger.bind(component="metrics_calculator")

    def calculate_virality_score(
        self,
        zap_count: int,
        zap_total_sats: int,
        reply_count: int,
        repost_count: int,
        reaction_count: int,
        age_hours: float,
    ) -> float:
        """
        Calculate virality score for content.

        Formula considers:
        - Engagement metrics (zaps, replies, reposts, reactions)
        - Monetary value (sats zapped)
        - Time decay (newer content scores higher)
        """
        # Weight factors
        ZAP_WEIGHT = 3.0
        SAT_WEIGHT = 0.001  # Per sat
        REPLY_WEIGHT = 2.0
        REPOST_WEIGHT = 2.5
        REACTION_WEIGHT = 1.0

        # Calculate engagement score
        engagement_score = (
            zap_count * ZAP_WEIGHT
            + zap_total_sats * SAT_WEIGHT
            + reply_count * REPLY_WEIGHT
            + repost_count * REPOST_WEIGHT
            + reaction_count * REACTION_WEIGHT
        )

        # Apply time decay (half-life of 6 hours)
        if age_hours > 0:
            time_decay = math.exp(-0.1155 * age_hours)  # ln(2)/6 ≈ 0.1155
        else:
            time_decay = 1.0

        virality_score = engagement_score * time_decay

        return round(virality_score, 2)

    def calculate_trend_score(
        self,
        mention_count: int,
        unique_authors: int,
        total_zaps: int,
        window_hours: int,
    ) -> float:
        """
        Calculate trending score for hashtags/topics.

        Considers:
        - Volume of mentions
        - Diversity of authors
        - Engagement (zaps)
        - Velocity (mentions per hour)
        """
        # Avoid division by zero
        if window_hours == 0:
            window_hours = 1

        # Calculate velocity (mentions per hour)
        velocity = mention_count / window_hours

        # Author diversity bonus (more unique authors = more trending)
        diversity_factor = math.log1p(unique_authors)

        # Zap engagement factor
        zap_factor = math.log1p(total_zaps)

        # Combined score
        trend_score = velocity * diversity_factor * (1 + zap_factor)

        return round(trend_score, 2)

    def calculate_user_influence_score(
        self,
        follower_count: int,
        total_zaps_received: int,
        avg_zaps_per_note: float,
        total_notes: int,
        account_age_days: int,
    ) -> float:
        """
        Calculate influence score for a user.

        Considers:
        - Follower count
        - Total zaps received
        - Average zaps per note
        - Activity level
        - Account longevity
        """
        # Logarithmic scaling for followers (diminishing returns)
        follower_score = math.log1p(follower_count)

        # Zap score
        zap_score = math.log1p(total_zaps_received)

        # Engagement rate
        engagement_score = avg_zaps_per_note * 10

        # Activity score (notes per day, capped at 10)
        if account_age_days > 0:
            activity_rate = min(total_notes / account_age_days, 10)
        else:
            activity_rate = 0
        activity_score = activity_rate * 2

        # Longevity bonus
        longevity_score = math.log1p(account_age_days / 30)  # Log of months

        # Combined weighted score
        influence_score = (
            follower_score * 2.0
            + zap_score * 1.5
            + engagement_score * 1.0
            + activity_score * 0.5
            + longevity_score * 0.5
        )

        return round(influence_score, 2)

    def calculate_relay_health_score(
        self,
        uptime_percentage: float,
        avg_latency_ms: float,
        events_per_second: float,
        error_rate: float,
    ) -> float:
        """
        Calculate health score for a relay.

        Considers:
        - Uptime percentage
        - Response latency
        - Event throughput
        - Error rate
        """
        # Uptime score (0-100)
        uptime_score = uptime_percentage

        # Latency score (lower is better)
        # 0ms = 100, 1000ms = 0
        latency_score = max(0, 100 - (avg_latency_ms / 10))

        # Throughput score (higher is better, log scale)
        throughput_score = min(100, math.log1p(events_per_second) * 20)

        # Error score (lower is better)
        error_score = max(0, 100 - (error_rate * 100))

        # Weighted average
        health_score = (
            uptime_score * 0.4
            + latency_score * 0.3
            + throughput_score * 0.2
            + error_score * 0.1
        )

        return round(health_score, 2)

    def calculate_content_quality_score(
        self,
        content_length: int,
        has_media: bool,
        hashtag_count: int,
        zap_count: int,
        reply_count: int,
    ) -> float:
        """
        Estimate content quality based on various signals.

        This is a heuristic score, not a definitive quality measure.
        """
        # Length score (sweet spot around 280-500 chars)
        if content_length < 50:
            length_score = content_length / 50 * 50
        elif 50 <= content_length <= 500:
            length_score = 50 + ((content_length - 50) / 450 * 50)
        else:
            length_score = 100 - min(50, (content_length - 500) / 100)

        # Media bonus
        media_score = 20 if has_media else 0

        # Hashtag score (some is good, too many is spam)
        if hashtag_count == 0:
            hashtag_score = 0
        elif 1 <= hashtag_count <= 3:
            hashtag_score = 15
        elif 4 <= hashtag_count <= 5:
            hashtag_score = 10
        else:
            hashtag_score = max(0, 10 - (hashtag_count - 5) * 2)

        # Engagement validation score
        engagement_score = min(30, (zap_count * 5) + (reply_count * 2))

        # Combined score (0-100)
        quality_score = (
            length_score * 0.3
            + media_score * 0.2
            + hashtag_score * 0.1
            + engagement_score * 0.4
        )

        return round(quality_score, 2)

    def calculate_network_growth_rate(
        self,
        new_users_today: int,
        total_users: int,
        new_users_yesterday: int,
    ) -> Dict[str, float]:
        """Calculate network growth metrics."""
        # Daily growth rate
        if total_users > 0:
            daily_growth_rate = (new_users_today / total_users) * 100
        else:
            daily_growth_rate = 0.0

        # Day-over-day growth
        if new_users_yesterday > 0:
            dod_growth = ((new_users_today - new_users_yesterday) / new_users_yesterday) * 100
        else:
            dod_growth = 0.0

        return {
            "daily_growth_rate": round(daily_growth_rate, 2),
            "day_over_day_change": round(dod_growth, 2),
        }

    def calculate_zap_stats(
        self,
        zap_amounts: List[int],
    ) -> Dict[str, Any]:
        """Calculate statistical metrics for zap amounts."""
        if not zap_amounts:
            return {
                "total": 0,
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "p95": 0,
            }

        zap_amounts_sorted = sorted(zap_amounts)
        count = len(zap_amounts_sorted)

        total = sum(zap_amounts_sorted)
        mean = total / count
        median = zap_amounts_sorted[count // 2]
        min_zap = zap_amounts_sorted[0]
        max_zap = zap_amounts_sorted[-1]
        p95_index = int(count * 0.95)
        p95 = zap_amounts_sorted[p95_index] if p95_index < count else max_zap

        return {
            "total": total,
            "count": count,
            "mean": round(mean, 2),
            "median": median,
            "min": min_zap,
            "max": max_zap,
            "p95": p95,
        }

    def is_spam_likely(
        self,
        content_length: int,
        hashtag_count: int,
        url_count: int,
        mention_count: int,
        is_reply: bool,
    ) -> bool:
        """
        Heuristic to detect likely spam content.

        This is a simple rule-based approach.
        """
        # Very short with many hashtags
        if content_length < 20 and hashtag_count > 5:
            return True

        # Too many hashtags
        if hashtag_count > 10:
            return True

        # Too many URLs relative to content
        if content_length < 100 and url_count > 3:
            return True

        # Excessive mentions without much content
        if content_length < 50 and mention_count > 5:
            return True

        # Not a reply, very short, but many mentions
        if not is_reply and content_length < 30 and mention_count > 3:
            return True

        return False

    def calculate_time_of_day_metrics(
        self,
        event_timestamps: List[datetime],
    ) -> Dict[int, int]:
        """Calculate distribution of events by hour of day."""
        hourly_distribution = {hour: 0 for hour in range(24)}

        for timestamp in event_timestamps:
            hour = timestamp.hour
            hourly_distribution[hour] += 1

        return hourly_distribution

    def calculate_engagement_rate(
        self,
        total_engagements: int,
        follower_count: int,
        content_count: int,
    ) -> float:
        """Calculate engagement rate as a percentage."""
        if follower_count == 0 or content_count == 0:
            return 0.0

        avg_engagements_per_content = total_engagements / content_count
        engagement_rate = (avg_engagements_per_content / follower_count) * 100

        return round(engagement_rate, 2)
