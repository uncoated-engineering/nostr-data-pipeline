"""Tests for event processor."""

import pytest
from datetime import datetime
from nostr_pipeline.transformers.event_processor import EventProcessor


@pytest.fixture
def processor():
    """Create event processor instance."""
    return EventProcessor()


def test_process_text_note(processor):
    """Test processing a text note event."""
    event = {
        "id": "test123",
        "pubkey": "pubkey123",
        "created_at": int(datetime.utcnow().timestamp()),
        "kind": 1,
        "content": "Hello #nostr! Check out this image: https://example.com/image.jpg",
        "sig": "sig123",
        "tags": [
            ["t", "nostr"],
            ["p", "mentioned_pubkey"],
        ],
    }

    result = processor.process_event(event, "wss://relay.test")

    assert result is not None
    assert result["id"] == "test123"
    assert result["kind"] == 1
    assert "text_note_data" in result

    note_data = result["text_note_data"]
    assert "nostr" in note_data["hashtags"]
    assert note_data["has_media"] is True
    assert len(note_data["media_urls"]) == 1


def test_extract_hashtags(processor):
    """Test hashtag extraction."""
    content = "This is a #test with #multiple #hashtags"
    tags = [["t", "tagged"]]

    hashtags = processor._extract_hashtags(content, tags)

    assert "test" in hashtags
    assert "multiple" in hashtags
    assert "hashtags" in hashtags
    assert "tagged" in hashtags


def test_parse_bolt11_amount(processor):
    """Test parsing bolt11 invoice amounts."""
    # Test micro-bitcoin (common for zaps)
    # 20u = 20 micro-bitcoin = 2000 sats = 2,000,000 msats
    bolt11_micro = "lnbc20u1pjexampledata"
    amount_micro = processor._parse_bolt11_amount(bolt11_micro)
    assert amount_micro == 2_000_000  # 2000 sats in msats

    # Test milli-bitcoin
    # 1m = 1 milli-bitcoin = 100,000 sats = 100,000,000 msats
    bolt11_milli = "lnbc1m1pjexampledata"
    amount_milli = processor._parse_bolt11_amount(bolt11_milli)
    assert amount_milli == 100_000_000  # 100,000 sats in msats

    # Test nano-bitcoin (small zaps)
    # 1000n = 1000 nano-bitcoin = 0.1 sats = 100 msats * 1000 = 100,000 msats
    bolt11_nano = "lnbc1000n1pjexampledata"
    amount_nano = processor._parse_bolt11_amount(bolt11_nano)
    assert amount_nano == 100_000  # 100 sats in msats


def test_check_media_urls(processor):
    """Test media URL detection."""
    urls = [
        "https://example.com/image.jpg",
        "https://example.com/page.html",
        "https://example.com/video.mp4",
    ]

    has_media, media_urls = processor._check_media(urls)

    assert has_media is True
    assert len(media_urls) == 2
    assert "image.jpg" in media_urls[0]
    assert "video.mp4" in media_urls[1]


def test_extract_reply_to(processor):
    """Test reply extraction from tags."""
    tags = [
        ["e", "event_id_1", "", "root"],
        ["e", "event_id_2", "", "reply"],
        ["p", "pubkey"],
    ]

    reply_to = processor._extract_reply_to(tags)

    assert reply_to == "event_id_2"
