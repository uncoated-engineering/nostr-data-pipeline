"""Configuration management for Nostr pipeline."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Nostr Configuration
    nostr_relays: List[str] = Field(
        default=[
            "wss://relay.damus.io",
            "wss://nos.lol",
            "wss://relay.nostr.band",
            "wss://nostr.wine",
            "wss://relay.snort.social",
        ],
        description="List of Nostr relay WebSocket URLs",
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./nostr_data.db",
        description="Database connection URL",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching",
    )

    # Pipeline Configuration
    batch_size: int = Field(default=100, description="Events to process per batch")
    processing_interval_seconds: int = Field(
        default=5, description="Seconds between processing batches"
    )
    max_events_per_batch: int = Field(
        default=1000, description="Maximum events in a single batch"
    )

    # Metrics Configuration
    metrics_aggregation_interval_seconds: int = Field(
        default=60, description="Seconds between metrics aggregation"
    )
    trending_window_hours: int = Field(
        default=24, description="Time window for trending calculations"
    )
    min_zaps_for_trending: int = Field(
        default=10, description="Minimum zaps for trending content"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or console)")

    # Performance
    max_relay_connections: int = Field(
        default=10, description="Maximum concurrent relay connections"
    )
    event_buffer_size: int = Field(
        default=10000, description="Size of event buffer"
    )
    worker_threads: int = Field(default=4, description="Number of worker threads")


# Global settings instance
settings = Settings()
