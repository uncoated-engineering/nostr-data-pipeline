"""Nostr relay client for extracting events."""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any, Set
from dataclasses import dataclass
import structlog
import websockets
from websockets.client import WebSocketClientProtocol

logger = structlog.get_logger()


@dataclass
class NostrFilter:
    """Nostr subscription filter."""

    kinds: Optional[List[int]] = None
    authors: Optional[List[str]] = None
    since: Optional[int] = None
    until: Optional[int] = None
    limit: Optional[int] = None
    ids: Optional[List[str]] = None
    tags: Optional[Dict[str, List[str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to Nostr protocol format."""
        filter_dict = {}
        if self.kinds:
            filter_dict["kinds"] = self.kinds
        if self.authors:
            filter_dict["authors"] = self.authors
        if self.since:
            filter_dict["since"] = self.since
        if self.until:
            filter_dict["until"] = self.until
        if self.limit:
            filter_dict["limit"] = self.limit
        if self.ids:
            filter_dict["ids"] = self.ids
        if self.tags:
            for tag_name, tag_values in self.tags.items():
                filter_dict[f"#{tag_name}"] = tag_values
        return filter_dict


class RelayClient:
    """Client for connecting to a single Nostr relay."""

    def __init__(
        self,
        relay_url: str,
        event_callback: Optional[Callable[[Dict[str, Any], str], None]] = None,
    ):
        self.relay_url = relay_url
        self.event_callback = event_callback
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.subscriptions: Dict[str, NostrFilter] = {}
        self.is_connected = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
        self.log = logger.bind(relay=relay_url)
        self.connection_latency: Optional[float] = None
        self.last_event_time: Optional[datetime] = None
        self.event_count = 0
        self.error_count = 0

    async def connect(self) -> bool:
        """Connect to the relay."""
        try:
            start_time = time.time()
            self.log.info("connecting_to_relay")
            self.websocket = await websockets.connect(
                self.relay_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
            )
            self.connection_latency = (time.time() - start_time) * 1000  # ms
            self.is_connected = True
            self.reconnect_delay = 1
            self.log.info(
                "connected_to_relay",
                latency_ms=round(self.connection_latency, 2),
            )
            return True
        except Exception as e:
            self.is_connected = False
            self.error_count += 1
            self.log.error("failed_to_connect", error=str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from the relay."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.log.info("disconnected_from_relay")

    async def subscribe(self, subscription_id: str, filters: NostrFilter) -> None:
        """Subscribe to events matching the filter."""
        if not self.websocket:
            raise RuntimeError("Not connected to relay")

        self.subscriptions[subscription_id] = filters
        req_message = json.dumps(["REQ", subscription_id, filters.to_dict()])
        await self.websocket.send(req_message)
        self.log.info("subscribed", subscription_id=subscription_id, filter=filters.to_dict())

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        if not self.websocket:
            return

        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            close_message = json.dumps(["CLOSE", subscription_id])
            await self.websocket.send(close_message)
            self.log.info("unsubscribed", subscription_id=subscription_id)

    async def publish_event(self, event: Dict[str, Any]) -> bool:
        """Publish an event to the relay."""
        if not self.websocket:
            raise RuntimeError("Not connected to relay")

        try:
            event_message = json.dumps(["EVENT", event])
            await self.websocket.send(event_message)
            self.log.debug("published_event", event_id=event.get("id"))
            return True
        except Exception as e:
            self.log.error("failed_to_publish", error=str(e))
            return False

    async def listen(self) -> None:
        """Listen for events from the relay."""
        if not self.websocket:
            raise RuntimeError("Not connected to relay")

        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            self.log.warning("connection_closed")
        except Exception as e:
            self.is_connected = False
            self.error_count += 1
            self.log.error("listen_error", error=str(e))

    async def _handle_message(self, message: str) -> None:
        """Handle incoming message from relay."""
        try:
            data = json.loads(message)
            msg_type = data[0]

            if msg_type == "EVENT":
                subscription_id = data[1]
                event = data[2]
                self.event_count += 1
                self.last_event_time = datetime.utcnow()

                if self.event_callback:
                    await asyncio.create_task(
                        self._call_event_callback(event, subscription_id)
                    )

            elif msg_type == "EOSE":
                # End of stored events
                subscription_id = data[1]
                self.log.debug("end_of_stored_events", subscription_id=subscription_id)

            elif msg_type == "OK":
                # Event acceptance status
                event_id = data[1]
                accepted = data[2]
                message = data[3] if len(data) > 3 else ""
                self.log.debug(
                    "event_status",
                    event_id=event_id,
                    accepted=accepted,
                    message=message,
                )

            elif msg_type == "NOTICE":
                # Relay notice
                notice = data[1]
                self.log.info("relay_notice", notice=notice)

        except json.JSONDecodeError:
            self.error_count += 1
            self.log.error("invalid_json", message=message[:100])
        except Exception as e:
            self.error_count += 1
            self.log.error("message_handling_error", error=str(e))

    async def _call_event_callback(self, event: Dict[str, Any], subscription_id: str) -> None:
        """Call the event callback function."""
        try:
            if asyncio.iscoroutinefunction(self.event_callback):
                await self.event_callback(event, self.relay_url)
            else:
                self.event_callback(event, self.relay_url)
        except Exception as e:
            self.log.error("callback_error", error=str(e), event_id=event.get("id"))

    async def run_with_reconnect(self) -> None:
        """Run the client with automatic reconnection."""
        while True:
            if not await self.connect():
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                continue

            # Resubscribe to all subscriptions
            for sub_id, filters in list(self.subscriptions.items()):
                try:
                    await self.subscribe(sub_id, filters)
                except Exception as e:
                    self.log.error("resubscribe_error", subscription_id=sub_id, error=str(e))

            # Listen for events
            await self.listen()

            # If we get here, connection was lost
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)


class RelayPool:
    """Pool of relay clients for connecting to multiple relays."""

    def __init__(
        self,
        relay_urls: List[str],
        event_callback: Optional[Callable[[Dict[str, Any], str], None]] = None,
    ):
        self.relay_urls = relay_urls
        self.event_callback = event_callback
        self.clients: Dict[str, RelayClient] = {}
        self.log = logger.bind(component="relay_pool")
        self._tasks: List[asyncio.Task] = []

    async def connect_all(self) -> None:
        """Connect to all relays in the pool."""
        self.log.info("connecting_to_relays", count=len(self.relay_urls))

        for relay_url in self.relay_urls:
            client = RelayClient(relay_url, self.event_callback)
            self.clients[relay_url] = client

        # Connect to all relays concurrently
        connect_tasks = [client.connect() for client in self.clients.values()]
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        connected = sum(1 for r in results if r is True)
        self.log.info("relays_connected", connected=connected, total=len(self.relay_urls))

    async def disconnect_all(self) -> None:
        """Disconnect from all relays."""
        self.log.info("disconnecting_from_all_relays")

        # Stop all running tasks
        for task in self._tasks:
            task.cancel()

        # Disconnect all clients
        disconnect_tasks = [client.disconnect() for client in self.clients.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        self.clients.clear()
        self._tasks.clear()

    async def subscribe_all(self, subscription_id: str, filters: NostrFilter) -> None:
        """Subscribe to events on all connected relays."""
        self.log.info("subscribing_all_relays", subscription_id=subscription_id)

        subscribe_tasks = []
        for client in self.clients.values():
            if client.is_connected:
                subscribe_tasks.append(client.subscribe(subscription_id, filters))

        await asyncio.gather(*subscribe_tasks, return_exceptions=True)

    async def unsubscribe_all(self, subscription_id: str) -> None:
        """Unsubscribe from events on all relays."""
        self.log.info("unsubscribing_all_relays", subscription_id=subscription_id)

        unsubscribe_tasks = [
            client.unsubscribe(subscription_id)
            for client in self.clients.values()
            if client.is_connected
        ]
        await asyncio.gather(*unsubscribe_tasks, return_exceptions=True)

    async def publish_to_all(self, event: Dict[str, Any]) -> Dict[str, bool]:
        """Publish an event to all connected relays."""
        results = {}
        publish_tasks = []
        relay_urls = []

        for relay_url, client in self.clients.items():
            if client.is_connected:
                publish_tasks.append(client.publish_event(event))
                relay_urls.append(relay_url)

        task_results = await asyncio.gather(*publish_tasks, return_exceptions=True)

        for relay_url, result in zip(relay_urls, task_results):
            results[relay_url] = result if isinstance(result, bool) else False

        return results

    def start_listening(self) -> None:
        """Start listening for events on all relays."""
        self.log.info("starting_listeners")

        for client in self.clients.values():
            if client.is_connected:
                task = asyncio.create_task(client.run_with_reconnect())
                self._tasks.append(task)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all relays."""
        stats = {
            "total_relays": len(self.clients),
            "connected_relays": sum(1 for c in self.clients.values() if c.is_connected),
            "total_events": sum(c.event_count for c in self.clients.values()),
            "total_errors": sum(c.error_count for c in self.clients.values()),
            "relays": {},
        }

        for relay_url, client in self.clients.items():
            stats["relays"][relay_url] = {
                "connected": client.is_connected,
                "events": client.event_count,
                "errors": client.error_count,
                "latency_ms": client.connection_latency,
                "last_event": client.last_event_time.isoformat() if client.last_event_time else None,
            }

        return stats
