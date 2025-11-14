"""Database models for Nostr pipeline."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Float,
    DateTime,
    Text,
    JSON,
    Index,
    ForeignKey,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class NostrEvent(Base):
    """Raw Nostr events from relays."""

    __tablename__ = "nostr_events"

    id = Column(String(64), primary_key=True, index=True)  # Event ID (hex)
    pubkey = Column(String(64), index=True, nullable=False)  # Author pubkey
    created_at = Column(DateTime, index=True, nullable=False)  # Event timestamp
    kind = Column(Integer, index=True, nullable=False)  # Event kind
    content = Column(Text, nullable=False)  # Event content
    sig = Column(String(128), nullable=False)  # Event signature
    tags = Column(JSON, nullable=True)  # Event tags as JSON
    relay_url = Column(String(255), index=True, nullable=False)  # Source relay
    received_at = Column(DateTime, default=datetime.utcnow)  # When we received it
    processed = Column(Boolean, default=False, index=True)  # Processing status

    # Indexes for common queries
    __table_args__ = (
        Index("idx_kind_created", "kind", "created_at"),
        Index("idx_pubkey_created", "pubkey", "created_at"),
        Index("idx_relay_created", "relay_url", "created_at"),
        Index("idx_processed_created", "processed", "created_at"),
    )


class UserProfile(Base):
    """Nostr user profiles (kind 0 events)."""

    __tablename__ = "user_profiles"

    pubkey = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    about = Column(Text, nullable=True)
    picture = Column(String(512), nullable=True)
    nip05 = Column(String(255), nullable=True)
    lud06 = Column(String(255), nullable=True)  # Lightning address (LNURL)
    lud16 = Column(String(255), nullable=True)  # Lightning address
    banner = Column(String(512), nullable=True)
    website = Column(String(512), nullable=True)
    profile_metadata = Column(JSON, nullable=True)  # Full metadata JSON
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    event_count = Column(Integer, default=0)  # Total events by this user

    __table_args__ = (Index("idx_name", "name"),)


class Zap(Base):
    """Lightning zaps (kind 9735 events)."""

    __tablename__ = "zaps"

    id = Column(String(64), primary_key=True, index=True)  # Zap event ID
    target_event_id = Column(String(64), index=True, nullable=True)  # Zapped event
    target_pubkey = Column(String(64), index=True, nullable=False)  # Recipient
    sender_pubkey = Column(String(64), index=True, nullable=True)  # Sender
    amount_msats = Column(BigInteger, nullable=False)  # Amount in millisatoshis
    amount_sats = Column(Integer, nullable=False)  # Amount in satoshis
    comment = Column(Text, nullable=True)  # Zap comment
    created_at = Column(DateTime, index=True, nullable=False)
    bolt11 = Column(Text, nullable=True)  # Lightning invoice
    preimage = Column(String(64), nullable=True)  # Payment preimage
    relay_url = Column(String(255), nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_target_event_created", "target_event_id", "created_at"),
        Index("idx_target_pubkey_created", "target_pubkey", "created_at"),
        Index("idx_amount_created", "amount_sats", "created_at"),
    )


class ContentMetrics(Base):
    """Aggregated metrics for content (notes, articles, etc)."""

    __tablename__ = "content_metrics"

    event_id = Column(String(64), primary_key=True, index=True)
    author_pubkey = Column(String(64), index=True, nullable=False)
    kind = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime, index=True, nullable=False)

    # Engagement metrics
    zap_count = Column(Integer, default=0)
    zap_total_sats = Column(BigInteger, default=0)
    reply_count = Column(Integer, default=0)
    repost_count = Column(Integer, default=0)
    reaction_count = Column(Integer, default=0)

    # Content analysis
    content_length = Column(Integer, default=0)
    hashtag_count = Column(Integer, default=0)
    hashtags = Column(JSON, nullable=True)  # List of hashtags
    mentioned_pubkeys = Column(JSON, nullable=True)  # List of mentioned users
    has_media = Column(Boolean, default=False)
    media_urls = Column(JSON, nullable=True)
    language = Column(String(10), nullable=True)

    # Virality score (composite metric)
    virality_score = Column(Float, default=0.0, index=True)

    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_virality_created", "virality_score", "created_at"),
        Index("idx_zap_total_created", "zap_total_sats", "created_at"),
        Index("idx_author_created", "author_pubkey", "created_at"),
    )


class TrendingTopic(Base):
    """Trending hashtags and topics."""

    __tablename__ = "trending_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hashtag = Column(String(255), index=True, nullable=False)
    mention_count = Column(Integer, default=0)
    unique_authors = Column(Integer, default=0)
    total_zaps = Column(BigInteger, default=0)
    window_start = Column(DateTime, index=True, nullable=False)
    window_end = Column(DateTime, index=True, nullable=False)
    trend_score = Column(Float, default=0.0, index=True)
    sample_event_ids = Column(JSON, nullable=True)  # Sample events for this topic
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_hashtag_window", "hashtag", "window_start", "window_end"),
        Index("idx_trend_score", "trend_score", "window_start"),
    )


class RelayMetrics(Base):
    """Health and performance metrics for relays."""

    __tablename__ = "relay_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relay_url = Column(String(255), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)

    # Connection metrics
    is_connected = Column(Boolean, default=False)
    connection_latency_ms = Column(Float, nullable=True)
    last_successful_connection = Column(DateTime, nullable=True)

    # Event metrics
    events_received = Column(Integer, default=0)
    events_per_second = Column(Float, default=0.0)
    unique_authors = Column(Integer, default=0)

    # Event kind distribution
    kind_distribution = Column(JSON, nullable=True)  # {kind: count}

    # Error metrics
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Performance
    avg_event_size_bytes = Column(Float, nullable=True)
    total_bytes_received = Column(BigInteger, default=0)

    __table_args__ = (
        Index("idx_relay_timestamp", "relay_url", "timestamp"),
        Index("idx_timestamp", "timestamp"),
    )


class NetworkStats(Base):
    """Aggregate network-wide statistics."""

    __tablename__ = "network_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow, unique=True)

    # User metrics
    total_users = Column(Integer, default=0)
    active_users_1h = Column(Integer, default=0)
    active_users_24h = Column(Integer, default=0)
    new_users_24h = Column(Integer, default=0)

    # Content metrics
    total_events = Column(BigInteger, default=0)
    events_1h = Column(Integer, default=0)
    events_24h = Column(Integer, default=0)
    notes_24h = Column(Integer, default=0)  # Kind 1

    # Zap metrics
    total_zaps = Column(BigInteger, default=0)
    zaps_24h = Column(Integer, default=0)
    total_sats_zapped = Column(BigInteger, default=0)
    sats_zapped_24h = Column(BigInteger, default=0)

    # Relay metrics
    active_relays = Column(Integer, default=0)
    avg_relay_latency_ms = Column(Float, nullable=True)

    # Top content
    top_event_id = Column(String(64), nullable=True)  # Most zapped in window
    top_event_zaps = Column(Integer, default=0)

    __table_args__ = (Index("idx_timestamp_stats", "timestamp"),)
