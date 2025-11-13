"""Tests for metrics calculator."""

import pytest
from nostr_pipeline.transformers.metrics_calculator import MetricsCalculator


@pytest.fixture
def calculator():
    """Create metrics calculator instance."""
    return MetricsCalculator()


def test_calculate_virality_score(calculator):
    """Test virality score calculation."""
    score = calculator.calculate_virality_score(
        zap_count=10,
        zap_total_sats=5000,
        reply_count=5,
        repost_count=3,
        reaction_count=20,
        age_hours=1,
    )

    assert score > 0
    assert isinstance(score, float)

    # Test time decay - older content should score lower
    score_old = calculator.calculate_virality_score(
        zap_count=10,
        zap_total_sats=5000,
        reply_count=5,
        repost_count=3,
        reaction_count=20,
        age_hours=24,
    )

    assert score_old < score


def test_calculate_trend_score(calculator):
    """Test trend score calculation."""
    score = calculator.calculate_trend_score(
        mention_count=100,
        unique_authors=20,
        total_zaps=1000,
        window_hours=24,
    )

    assert score > 0
    assert isinstance(score, float)

    # More authors should increase score
    score_more_authors = calculator.calculate_trend_score(
        mention_count=100,
        unique_authors=50,
        total_zaps=1000,
        window_hours=24,
    )

    assert score_more_authors > score


def test_is_spam_likely(calculator):
    """Test spam detection heuristic."""
    # Short content with many hashtags - likely spam
    assert calculator.is_spam_likely(
        content_length=15,
        hashtag_count=8,
        url_count=1,
        mention_count=2,
        is_reply=False,
    ) is True

    # Normal content - not spam
    assert calculator.is_spam_likely(
        content_length=200,
        hashtag_count=2,
        url_count=1,
        mention_count=1,
        is_reply=False,
    ) is False


def test_calculate_zap_stats(calculator):
    """Test zap statistics calculation."""
    zap_amounts = [100, 500, 1000, 2000, 5000]

    stats = calculator.calculate_zap_stats(zap_amounts)

    assert stats["count"] == 5
    assert stats["total"] == 8600
    assert stats["mean"] == 1720
    assert stats["median"] == 1000
    assert stats["min"] == 100
    assert stats["max"] == 5000


def test_calculate_content_quality_score(calculator):
    """Test content quality score."""
    # High quality: good length, media, some hashtags, good engagement
    score_high = calculator.calculate_content_quality_score(
        content_length=300,
        has_media=True,
        hashtag_count=2,
        zap_count=10,
        reply_count=5,
    )

    # Low quality: very short, no media, too many hashtags, no engagement
    score_low = calculator.calculate_content_quality_score(
        content_length=20,
        has_media=False,
        hashtag_count=15,
        zap_count=0,
        reply_count=0,
    )

    assert score_high > score_low
    assert 0 <= score_high <= 100
    assert 0 <= score_low <= 100
