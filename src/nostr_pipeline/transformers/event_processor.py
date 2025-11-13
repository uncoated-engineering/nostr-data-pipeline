"""Event processor for transforming raw Nostr events."""

import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger()


class EventProcessor:
    """Process and enrich Nostr events."""

    # Nostr event kinds
    KIND_METADATA = 0  # User metadata
    KIND_TEXT_NOTE = 1  # Text note
    KIND_RECOMMEND_RELAY = 2  # Recommend relay
    KIND_CONTACTS = 3  # Contact list
    KIND_ENCRYPTED_DM = 4  # Encrypted direct message
    KIND_DELETE = 5  # Delete event
    KIND_REPOST = 6  # Repost
    KIND_REACTION = 7  # Reaction
    KIND_ZAP_REQUEST = 9734  # Zap request
    KIND_ZAP = 9735  # Zap receipt
    KIND_LONG_FORM = 30023  # Long-form content

    # Regex patterns
    HASHTAG_PATTERN = re.compile(r"#(\w+)")
    URL_PATTERN = re.compile(r"https?://[^\s]+")
    MENTION_PATTERN = re.compile(r"nostr:npub1[a-z0-9]{58}")

    def __init__(self):
        self.log = logger.bind(component="event_processor")

    def process_event(self, event: Dict[str, Any], relay_url: str) -> Dict[str, Any]:
        """Process a raw Nostr event and extract structured data."""
        try:
            # Basic event data
            processed = {
                "id": event.get("id"),
                "pubkey": event.get("pubkey"),
                "created_at": datetime.fromtimestamp(event.get("created_at", 0)),
                "kind": event.get("kind"),
                "content": event.get("content", ""),
                "sig": event.get("sig"),
                "tags": event.get("tags", []),
                "relay_url": relay_url,
                "received_at": datetime.utcnow(),
            }

            # Process based on event kind
            if event["kind"] == self.KIND_METADATA:
                processed["metadata"] = self._process_metadata(event)
            elif event["kind"] == self.KIND_TEXT_NOTE:
                processed["text_note_data"] = self._process_text_note(event)
            elif event["kind"] == self.KIND_REACTION:
                processed["reaction_data"] = self._process_reaction(event)
            elif event["kind"] == self.KIND_REPOST:
                processed["repost_data"] = self._process_repost(event)
            elif event["kind"] == self.KIND_ZAP:
                processed["zap_data"] = self._process_zap(event)

            return processed

        except Exception as e:
            self.log.error("event_processing_error", error=str(e), event_id=event.get("id"))
            return None

    def _process_metadata(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process kind 0 metadata events."""
        try:
            content = json.loads(event["content"])
            return {
                "name": content.get("name"),
                "display_name": content.get("display_name"),
                "about": content.get("about"),
                "picture": content.get("picture"),
                "nip05": content.get("nip05"),
                "lud06": content.get("lud06"),
                "lud16": content.get("lud16"),
                "banner": content.get("banner"),
                "website": content.get("website"),
                "raw_metadata": content,
            }
        except json.JSONDecodeError:
            return None

    def _process_text_note(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process kind 1 text note events."""
        content = event.get("content", "")
        tags = event.get("tags", [])

        # Extract hashtags
        hashtags = self._extract_hashtags(content, tags)

        # Extract URLs
        urls = self._extract_urls(content)

        # Extract mentioned pubkeys
        mentioned_pubkeys = self._extract_mentions(tags)

        # Check for media
        has_media, media_urls = self._check_media(urls)

        # Extract reply information
        reply_to = self._extract_reply_to(tags)

        return {
            "content_length": len(content),
            "hashtags": hashtags,
            "hashtag_count": len(hashtags),
            "urls": urls,
            "has_media": has_media,
            "media_urls": media_urls,
            "mentioned_pubkeys": mentioned_pubkeys,
            "reply_to_event": reply_to,
            "is_reply": reply_to is not None,
        }

    def _process_reaction(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process kind 7 reaction events."""
        tags = event.get("tags", [])
        content = event.get("content", "")

        # Find the event being reacted to
        event_id = None
        author_pubkey = None

        for tag in tags:
            if len(tag) >= 2:
                if tag[0] == "e":
                    event_id = tag[1]
                elif tag[0] == "p":
                    author_pubkey = tag[1]

        return {
            "target_event_id": event_id,
            "target_author": author_pubkey,
            "reaction_content": content,
            "is_like": content in ["+", "👍", "❤️", "🤙"],
        }

    def _process_repost(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process kind 6 repost events."""
        tags = event.get("tags", [])

        event_id = None
        author_pubkey = None

        for tag in tags:
            if len(tag) >= 2:
                if tag[0] == "e":
                    event_id = tag[1]
                elif tag[0] == "p":
                    author_pubkey = tag[1]

        return {
            "reposted_event_id": event_id,
            "reposted_author": author_pubkey,
        }

    def _process_zap(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process kind 9735 zap receipt events."""
        tags = event.get("tags", [])
        description = None
        bolt11 = None
        preimage = None
        target_event = None
        target_pubkey = None

        for tag in tags:
            if len(tag) >= 2:
                if tag[0] == "description":
                    try:
                        description = json.loads(tag[1])
                    except json.JSONDecodeError:
                        pass
                elif tag[0] == "bolt11":
                    bolt11 = tag[1]
                elif tag[0] == "preimage":
                    preimage = tag[1]
                elif tag[0] == "e":
                    target_event = tag[1]
                elif tag[0] == "p":
                    target_pubkey = tag[1]

        # Parse zap amount from bolt11
        amount_msats = self._parse_bolt11_amount(bolt11)

        # Extract sender from description
        sender_pubkey = None
        comment = None
        if description:
            sender_pubkey = description.get("pubkey")
            comment = description.get("content")

        return {
            "target_event_id": target_event,
            "target_pubkey": target_pubkey,
            "sender_pubkey": sender_pubkey,
            "amount_msats": amount_msats,
            "amount_sats": amount_msats // 1000 if amount_msats else 0,
            "comment": comment,
            "bolt11": bolt11,
            "preimage": preimage,
        }

    def _extract_hashtags(self, content: str, tags: List[List[str]]) -> List[str]:
        """Extract hashtags from content and tags."""
        hashtags = set()

        # From content
        for match in self.HASHTAG_PATTERN.finditer(content):
            hashtags.add(match.group(1).lower())

        # From tags
        for tag in tags:
            if len(tag) >= 2 and tag[0] == "t":
                hashtags.add(tag[1].lower())

        return list(hashtags)

    def _extract_urls(self, content: str) -> List[str]:
        """Extract URLs from content."""
        return self.URL_PATTERN.findall(content)

    def _extract_mentions(self, tags: List[List[str]]) -> List[str]:
        """Extract mentioned pubkeys from tags."""
        mentions = []
        for tag in tags:
            if len(tag) >= 2 and tag[0] == "p":
                mentions.append(tag[1])
        return mentions

    def _check_media(self, urls: List[str]) -> Tuple[bool, List[str]]:
        """Check if URLs contain media files."""
        media_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".webm"}
        media_urls = []

        for url in urls:
            parsed = urlparse(url)
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in media_extensions):
                media_urls.append(url)

        return len(media_urls) > 0, media_urls

    def _extract_reply_to(self, tags: List[List[str]]) -> Optional[str]:
        """Extract the event ID being replied to."""
        # Look for 'e' tags with 'reply' marker or the last 'e' tag
        reply_event = None
        for tag in tags:
            if len(tag) >= 2 and tag[0] == "e":
                if len(tag) >= 4 and tag[3] == "reply":
                    return tag[1]
                reply_event = tag[1]  # Keep the last one as fallback

        return reply_event

    def _parse_bolt11_amount(self, bolt11: Optional[str]) -> Optional[int]:
        """Parse amount from lightning invoice."""
        if not bolt11:
            return None

        try:
            # Simple parsing - look for amount in bolt11
            # Format: lnbc<amount><multiplier>
            bolt11_lower = bolt11.lower()
            if not bolt11_lower.startswith("lnbc"):
                return None

            # Extract amount and multiplier
            amount_str = bolt11_lower[4:].split("1")[0]
            if not amount_str:
                return None

            # Get multiplier
            multiplier_char = amount_str[-1]
            multipliers = {
                "m": 100_000,  # milli-bitcoin = 100,000 msats
                "u": 100,  # micro-bitcoin = 100 msats
                "n": 0.1,  # nano-bitcoin = 0.1 msats
                "p": 0.0001,  # pico-bitcoin = 0.0001 msats
            }

            if multiplier_char in multipliers:
                amount = float(amount_str[:-1])
                return int(amount * multipliers[multiplier_char])
            else:
                # No multiplier, amount is in bitcoin
                amount = float(amount_str)
                return int(amount * 100_000_000_000)  # btc to msats

        except (ValueError, IndexError):
            return None

    def extract_language(self, content: str) -> Optional[str]:
        """Detect language of content (simplified version)."""
        # This is a placeholder - in production, use langdetect or similar
        # For now, just detect common patterns
        if not content:
            return None

        # Simple heuristic based on character ranges
        if any("\u4e00" <= char <= "\u9fff" for char in content):
            return "zh"  # Chinese
        elif any("\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff" for char in content):
            return "ja"  # Japanese
        elif any("\uac00" <= char <= "\ud7af" for char in content):
            return "ko"  # Korean

        # Default to English for ASCII content
        return "en"
