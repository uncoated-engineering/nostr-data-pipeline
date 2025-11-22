"""Main ETL pipeline orchestrator."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

from nostr_pipeline.config import settings
from nostr_pipeline.extractors.relay_client import RelayPool, NostrFilter
from nostr_pipeline.transformers.event_processor import EventProcessor
from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.loaders.event_loader import EventLoader
from nostr_pipeline.analytics.aggregator import MetricsAggregator

logger = structlog.get_logger()


class NostrPipeline:
    """Main ETL pipeline for Nostr data."""

    def __init__(self):
        self.config = settings
        self.log = logger.bind(component="nostr_pipeline")

        # Components
        self.db_manager = DatabaseManager()
        self.event_loader = EventLoader(self.db_manager)
        self.event_processor = EventProcessor()
        self.metrics_aggregator = MetricsAggregator(self.db_manager)

        # Relay pool
        self.relay_pool: Optional[RelayPool] = None

        # Event buffer
        self.event_buffer = asyncio.Queue(maxsize=self.config.event_buffer_size)

        # Processing stats
        self.stats = {
            "events_received": 0,
            "events_processed": 0,
            "events_saved": 0,
            "errors": 0,
            "start_time": None,
        }

        # Control flags
        self.running = False
        self.tasks = []

    async def initialize(self) -> None:
        """Initialize the pipeline."""
        self.log.info("initializing_pipeline")

        # Initialize database
        self.db_manager.initialize()

        # Check database health
        if not self.db_manager.health_check():
            raise RuntimeError("Database health check failed")

        # Initialize relay pool with event callback
        self.relay_pool = RelayPool(
            relay_urls=self.config.nostr_relays,
            event_callback=self._on_event_received,
        )

        self.log.info("pipeline_initialized")

    async def start(self) -> None:
        """Start the ETL pipeline."""
        self.log.info("starting_pipeline")
        self.running = True
        self.stats["start_time"] = datetime.utcnow()

        try:
            # Connect to all relays
            await self.relay_pool.connect_all()

            # Subscribe to events
            await self._subscribe_to_events()

            # Start background tasks
            self.tasks = [
                asyncio.create_task(self._event_processor_loop()),
                asyncio.create_task(self._metrics_aggregator_loop()),
                asyncio.create_task(self._stats_reporter_loop()),
            ]

            # Start listening for events
            self.relay_pool.start_listening()

            self.log.info("pipeline_started")

            # Wait for shutdown signal
            await self._wait_for_shutdown()

        except Exception as e:
            self.log.error("pipeline_error", error=str(e))
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the pipeline gracefully."""
        self.log.info("stopping_pipeline")
        self.running = False

        # Cancel background tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Disconnect from relays
        if self.relay_pool:
            await self.relay_pool.disconnect_all()

        # Dispose database connections
        self.db_manager.dispose()

        self.log.info("pipeline_stopped")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to Nostr events."""
        # Subscribe to all event kinds we care about
        filters = NostrFilter(
            kinds=[
                0,  # Metadata
                1,  # Text notes
                6,  # Reposts
                7,  # Reactions
                9735,  # Zaps
            ],
            since=int(datetime.utcnow().timestamp()),
        )

        await self.relay_pool.subscribe_all("main", filters)
        self.log.info("subscribed_to_events")

    async def _on_event_received(self, event: Dict[str, Any], relay_url: str) -> None:
        """Callback when an event is received from a relay."""
        try:
            self.stats["events_received"] += 1

            # Add to processing queue
            await self.event_buffer.put((event, relay_url))

        except Exception as e:
            self.log.error(
                "event_receive_error",
                error=str(e),
                event_id=event.get("id"),
            )
            self.stats["errors"] += 1

    async def _event_processor_loop(self) -> None:
        """Background loop for processing events."""
        self.log.info("starting_event_processor_loop")

        batch = []
        last_batch_time = datetime.utcnow()

        while self.running:
            try:
                # Get event from queue (with timeout)
                try:
                    event, relay_url = await asyncio.wait_for(
                        self.event_buffer.get(),
                        timeout=1.0,
                    )
                    batch.append((event, relay_url))
                except asyncio.TimeoutError:
                    pass

                # Process batch if ready
                now = datetime.utcnow()
                time_since_batch = (now - last_batch_time).total_seconds()

                should_process = (
                    len(batch) >= self.config.batch_size
                    or (batch and time_since_batch >= self.config.processing_interval_seconds)
                )

                if should_process:
                    await self._process_batch(batch)
                    batch = []
                    last_batch_time = now

            except Exception as e:
                self.log.error("event_processor_error", error=str(e))
                self.stats["errors"] += 1
                await asyncio.sleep(1)

    async def _process_batch(self, batch: list) -> None:
        """Process a batch of events."""
        if not batch:
            return

        self.log.debug("processing_batch", size=len(batch))

        # Deduplicate events by ID (same event can arrive from multiple relays)
        seen_ids = set()
        unique_batch = []
        for event, relay_url in batch:
            event_id = event.get("id")
            if event_id and event_id not in seen_ids:
                seen_ids.add(event_id)
                unique_batch.append((event, relay_url))

        self.log.debug("deduplicated_batch", original=len(batch), unique=len(unique_batch))

        with self.db_manager.get_session() as session:
            for event, relay_url in unique_batch:
                try:
                    # Process event
                    processed = self.event_processor.process_event(event, relay_url)
                    if not processed:
                        continue

                    # Save raw event
                    self.event_loader.save_event(session, processed)

                    # Handle specific event types
                    kind = processed["kind"]

                    if kind == 0 and "metadata" in processed:
                        # User metadata
                        metadata = processed["metadata"]
                        if metadata:
                            profile_data = {
                                "pubkey": processed["pubkey"],
                                **metadata,
                            }
                            self.event_loader.save_user_profile(session, profile_data)

                    elif kind == 9735 and "zap_data" in processed:
                        # Zap
                        zap_data = processed["zap_data"]
                        if zap_data and zap_data["amount_msats"]:
                            zap_data.update({
                                "id": processed["id"],
                                "created_at": processed["created_at"],
                                "relay_url": processed["relay_url"],
                                "received_at": processed["received_at"],
                            })
                            self.event_loader.save_zap(session, zap_data)

                    self.stats["events_processed"] += 1
                    self.stats["events_saved"] += 1

                except Exception as e:
                    self.log.error(
                        "event_processing_error",
                        error=str(e),
                        event_id=event.get("id"),
                    )
                    self.stats["errors"] += 1

    async def _metrics_aggregator_loop(self) -> None:
        """Background loop for aggregating metrics."""
        self.log.info("starting_metrics_aggregator_loop")

        while self.running:
            try:
                # Wait for aggregation interval
                await asyncio.sleep(self.config.metrics_aggregation_interval_seconds)

                # Run aggregation
                with self.db_manager.get_session() as session:
                    stats = await self.metrics_aggregator.run_aggregation(session)
                    self.log.info("metrics_aggregated", stats=stats)

            except Exception as e:
                self.log.error("metrics_aggregator_error", error=str(e))
                self.stats["errors"] += 1

    async def _stats_reporter_loop(self) -> None:
        """Background loop for reporting stats."""
        self.log.info("starting_stats_reporter_loop")

        while self.running:
            try:
                await asyncio.sleep(60)  # Report every minute

                # Calculate runtime
                runtime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()

                # Get relay stats
                relay_stats = self.relay_pool.get_stats() if self.relay_pool else {}

                # Log stats
                self.log.info(
                    "pipeline_stats",
                    runtime_seconds=runtime,
                    events_received=self.stats["events_received"],
                    events_processed=self.stats["events_processed"],
                    events_saved=self.stats["events_saved"],
                    errors=self.stats["errors"],
                    buffer_size=self.event_buffer.qsize(),
                    relay_stats=relay_stats,
                )

            except Exception as e:
                self.log.error("stats_reporter_error", error=str(e))

    async def _wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.log.info("received_shutdown_signal")


async def main():
    """Main entry point."""
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if settings.log_format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Create and run pipeline
    pipeline = NostrPipeline()

    try:
        await pipeline.initialize()
        await pipeline.start()
    except KeyboardInterrupt:
        logger.info("shutting_down")
    except Exception as e:
        logger.error("pipeline_failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
