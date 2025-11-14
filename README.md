# Nostr Data Pipeline

A real-time ETL (Extract, Transform, Load) pipeline for streaming and analyzing data from the Nostr protocol. Built with Python, this pipeline connects to multiple Nostr relays, processes events in real-time, and provides powerful analytics on network activity, trending content, and user behavior.

## Features

### Real-Time Data Collection
- **Multi-Relay Support**: Connect to multiple Nostr relays simultaneously
- **Event Streaming**: Real-time WebSocket connections for live event ingestion
- **Automatic Reconnection**: Resilient relay connections with exponential backoff
- **Event Buffering**: Efficient queuing system to handle high-volume streams

### Comprehensive Data Tracking
- **Popular Content Metrics**: Track most zapped notes, viral posts, and trending topics
- **Network Activity**: Monitor posts per second, active users, and relay health
- **Lightning Network Stats**: Analyze zap amounts, tipping patterns, and payment flows
- **Content Analysis**: Extract hashtags, mentions, media, and language distribution
- **User Growth**: Track new pubkeys, profile updates, and user engagement

### Advanced Analytics
- **Virality Scoring**: Calculate engagement-based virality scores with time decay
- **Trending Topics**: Identify trending hashtags with velocity-based algorithms
- **User Influence**: Compute influence scores based on followers, zaps, and engagement
- **Content Quality**: Heuristic-based content quality assessment
- **Network Statistics**: Aggregate network-wide metrics and growth rates

### Interactive Web Dashboard 🎨
- **Real-Time Visualizations**: Beautiful, interactive charts and graphs powered by Plotly
- **Multiple Views**: Overview, Trending, Network, Users, Relays, and Zaps pages
- **Live Updates**: Auto-refresh capabilities for real-time monitoring
- **Responsive Design**: Modern UI that works on desktop and mobile
- **Easy Navigation**: Intuitive multi-page dashboard with sidebar navigation

### Rich CLI Interface
- **Pipeline Control**: Start/stop the ETL pipeline
- **Live Statistics**: View network stats, trending topics, and top content
- **User Analytics**: Query detailed statistics for specific users
- **Relay Health**: Monitor relay performance and connection status

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NOSTR RELAYS                             │
│  wss://relay.damus.io  wss://nos.lol  wss://relay.nostr.band   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket Connections
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXTRACTOR LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Relay Pool  │  │ WebSocket   │  │   Event     │            │
│  │  Manager    │→ │  Listeners  │→ │   Buffer    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Raw Events
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TRANSFORMER LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Event     │  │   Metrics    │  │   Content    │         │
│  │  Processor   │→ │  Calculator  │→ │  Enrichment  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│   • Parse events    • Virality score  • Extract hashtags       │
│   • Extract metadata • Trend analysis  • Identify media        │
│   • Validate sigs   • Quality scores  • Parse mentions         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Processed Data
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LOADER LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Database    │  │    Batch     │  │    Cache     │         │
│  │   Manager    │← │   Inserter   │← │   Manager    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │   PostgreSQL     │         │      Redis       │             │
│  │  • Raw events    │         │  • Rate limiting │             │
│  │  • User profiles │         │  • Caching       │             │
│  │  • Zaps          │         │  • Temp storage  │             │
│  │  • Metrics       │         └──────────────────┘             │
│  │  • Aggregations  │                                           │
│  └──────────────────┘                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYTICS LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Aggregator  │  │    Query     │  │  Reporting   │         │
│  │   Engine     │→ │   Interface  │→ │    API       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│   • Trending topics • User stats     • CLI commands            │
│   • Network stats   • Top content    • JSON exports            │
│   • Growth metrics  • Relay health   • Dashboards              │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

### Core Tables
- **nostr_events**: Raw Nostr events with full event data
- **user_profiles**: User metadata (kind 0 events)
- **zaps**: Lightning zap receipts with amounts and comments
- **content_metrics**: Aggregated engagement metrics per event
- **trending_topics**: Trending hashtags with time windows
- **relay_metrics**: Health and performance data for relays
- **network_stats**: Network-wide aggregate statistics

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd nostr-data-pipeline

# Copy environment configuration
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f pipeline

# Stop services
docker-compose down
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
nostr-pipeline init-db

# Run the pipeline
nostr-pipeline run
```

## Usage

### Web Dashboard

Access the interactive dashboard for real-time visualizations:

```bash
# With Docker
docker-compose up -d
# Dashboard available at http://localhost:8501

# Or run locally
make dashboard
# Opens browser at http://localhost:8501
```

**Dashboard Pages:**
- 📈 **Overview**: Network statistics and key metrics
- 🔥 **Trending**: Trending hashtags and viral content
- 📡 **Network**: Real-time activity and timelines
- 👥 **Users**: Top users and leaderboards
- 🌐 **Relays**: Relay health and performance
- ⚡ **Zaps**: Lightning Network analytics

See [DASHBOARD.md](DASHBOARD.md) for detailed documentation.

### Pipeline Commands

```bash
# Start the ETL pipeline
nostr-pipeline run

# Initialize database schema
nostr-pipeline init-db

# View network statistics
nostr-pipeline stats

# Show trending hashtags (last 24 hours)
nostr-pipeline trending --hours 24 --limit 10

# Show top zapped content
nostr-pipeline top-zapped --hours 24 --limit 10

# Get user statistics
nostr-pipeline user <pubkey>

# Check relay health
nostr-pipeline relays

# Show version
nostr-pipeline version
```

### Configuration

Edit `.env` file to customize:

```env
# Nostr Relays (comma-separated WebSocket URLs)
NOSTR_RELAYS=wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band

# Database
DATABASE_URL=postgresql://nostr:nostr@localhost:5432/nostr_pipeline

# Redis
REDIS_URL=redis://localhost:6379/0

# Pipeline Settings
BATCH_SIZE=100
PROCESSING_INTERVAL_SECONDS=5
MAX_EVENTS_PER_BATCH=1000

# Metrics
METRICS_AGGREGATION_INTERVAL_SECONDS=60
TRENDING_WINDOW_HOURS=24
MIN_ZAPS_FOR_TRENDING=10

# Performance
MAX_RELAY_CONNECTIONS=10
EVENT_BUFFER_SIZE=10000
WORKER_THREADS=4
```

## Example Queries

### Python API

```python
from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery

# Initialize
db_manager = DatabaseManager()
db_manager.initialize()

with db_manager.get_session() as session:
    query = AnalyticsQuery()

    # Get network overview
    overview = query.get_network_overview(session)
    print(f"Total users: {overview['users']['total']}")

    # Get trending hashtags
    trending = query.get_trending_hashtags(session, hours=24, limit=10)
    for topic in trending:
        print(f"#{topic['hashtag']}: {topic['mention_count']} mentions")

    # Get top content by zaps
    top_content = query.get_top_zapped_content(session, hours=24, limit=5)
    for content in top_content:
        print(f"Event {content['event_id']}: {content['zap_total_sats']} sats")

    # Get user statistics
    user_stats = query.get_user_stats(session, pubkey="<pubkey>")
    if user_stats:
        print(f"User: {user_stats['profile']['name']}")
        print(f"Total events: {user_stats['activity']['total_events']}")
```

## Metrics and Analytics

### Content Virality Score

Calculated using weighted engagement metrics with time decay:

```
virality_score = (
    zap_count × 3.0 +
    zap_total_sats × 0.001 +
    reply_count × 2.0 +
    repost_count × 2.5 +
    reaction_count × 1.0
) × exp(-0.1155 × age_hours)
```

### Trend Score

For hashtags and topics:

```
trend_score = (mentions / window_hours) × log(unique_authors) × (1 + log(total_zaps))
```

### Tracked Metrics

- **User Metrics**: Total users, active users, new users, engagement rates
- **Content Metrics**: Zap counts, reply counts, repost counts, virality scores
- **Network Metrics**: Events per second, relay health, network growth
- **Zap Metrics**: Total volume, distribution, tipping patterns
- **Trending Analysis**: Hashtag velocity, topic emergence, viral content

## Development

### Project Structure

```
nostr-data-pipeline/
├── src/
│   └── nostr_pipeline/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── models.py               # Database models
│       ├── pipeline.py             # Main orchestrator
│       ├── cli.py                  # Command-line interface
│       ├── extractors/             # Data extraction
│       │   ├── __init__.py
│       │   └── relay_client.py     # Nostr relay client
│       ├── transformers/           # Data transformation
│       │   ├── __init__.py
│       │   ├── event_processor.py  # Event parsing
│       │   └── metrics_calculator.py
│       ├── loaders/                # Data loading
│       │   ├── __init__.py
│       │   ├── database.py         # DB manager
│       │   └── event_loader.py     # Data persistence
│       └── analytics/              # Analytics engine
│           ├── __init__.py
│           ├── aggregator.py       # Metrics aggregation
│           └── query.py            # Query interface
├── tests/                          # Test suite
├── docker/                         # Docker configurations
├── pyproject.toml                  # Project metadata
├── requirements.txt                # Dependencies
├── Dockerfile                      # Container image
├── docker-compose.yml              # Multi-container setup
└── README.md                       # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=nostr_pipeline --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

## Performance

- **Event Throughput**: Handles 1000+ events/second
- **Latency**: Sub-100ms event processing
- **Scalability**: Horizontal scaling via multiple workers
- **Storage**: Efficient time-series storage with automatic cleanup
- **Memory**: Configurable buffer sizes for memory management

## Use Cases

1. **Social Analytics**: Track viral content, trending topics, and user engagement
2. **Market Research**: Analyze Lightning Network adoption and tipping behavior
3. **Network Monitoring**: Monitor relay health and network performance
4. **Content Discovery**: Find popular content and influential users
5. **Research**: Study decentralized social network dynamics
6. **Bot Detection**: Identify spam patterns and suspicious behavior

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built on the [Nostr Protocol](https://github.com/nostr-protocol/nostr)
- Inspired by the decentralized social networking movement
- Thanks to all Nostr relay operators and developers

## Support

- Documentation: [docs/](docs/)
- Issues: GitHub Issues
- Community: Nostr (find us by searching #nostr-pipeline)

## Roadmap

- [ ] Web dashboard for real-time visualization
- [ ] Machine learning models for content recommendations
- [ ] Advanced spam detection
- [ ] GraphQL API
- [ ] WebSocket API for real-time subscriptions
- [ ] Multi-language support for content analysis
- [ ] Integration with additional Lightning Network stats
- [ ] Custom alert system for trending topics
- [ ] Export to data warehouses (BigQuery, Snowflake)
