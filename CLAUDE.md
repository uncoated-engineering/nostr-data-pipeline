# CLAUDE.md - AI Assistant Guide for Nostr Data Pipeline

## Project Overview

This is a real-time ETL (Extract, Transform, Load) pipeline for streaming and analyzing data from the Nostr protocol. The pipeline connects to multiple Nostr relays via WebSocket, processes events in real-time, stores them in PostgreSQL, and provides analytics on network activity, trending content, and user behavior.

**Tech Stack:**
- Python 3.10+ with async/await patterns
- SQLAlchemy 2.0+ for ORM and database management
- PostgreSQL for persistent storage
- Redis for caching
- Streamlit for web dashboard
- Pydantic for configuration and validation
- Typer/Rich for CLI interface
- Structlog for structured logging

## Quick Reference Commands

```bash
# Development setup
pip install -r requirements.txt
pip install -e ".[dev]"

# Run pipeline
nostr-pipeline run

# Initialize database
nostr-pipeline init-db

# View statistics
nostr-pipeline stats
nostr-pipeline trending --hours 24 --limit 10
nostr-pipeline top-zapped --hours 24 --limit 10
nostr-pipeline relays

# Run dashboard locally
cd dashboard && streamlit run Home.py
# Or: make dashboard

# Docker workflow
docker-compose up -d          # Start all services
docker-compose logs -f        # View logs
docker-compose down           # Stop services

# Testing and quality
pytest tests/ -v --cov=nostr_pipeline
black src/ tests/             # Format code
ruff check src/               # Lint code
mypy src/                     # Type checking
```

## Architecture

The pipeline follows a classic ETL pattern with distinct layers:

```
Nostr Relays (WebSocket)
    -> Extractors (relay_client.py)
    -> Transformers (event_processor.py, metrics_calculator.py)
    -> Loaders (database.py, event_loader.py)
    -> Analytics (aggregator.py, query.py)
    -> Dashboard (Streamlit)
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Pipeline Orchestrator | `src/nostr_pipeline/pipeline.py` | Main async event loop, coordinates all components |
| Configuration | `src/nostr_pipeline/config.py` | Pydantic Settings for env-based config |
| Database Models | `src/nostr_pipeline/models.py` | SQLAlchemy ORM models |
| CLI Interface | `src/nostr_pipeline/cli.py` | Typer-based CLI commands |
| Relay Client | `src/nostr_pipeline/extractors/relay_client.py` | WebSocket connections to Nostr relays |
| Event Processor | `src/nostr_pipeline/transformers/event_processor.py` | Parse and enrich events |
| Database Manager | `src/nostr_pipeline/loaders/database.py` | Session management and DB operations |
| Analytics Query | `src/nostr_pipeline/analytics/query.py` | SQL queries for analytics |
| Aggregator | `src/nostr_pipeline/analytics/aggregator.py` | Metrics aggregation logic |

## Directory Structure

```
nostr-data-pipeline/
├── src/nostr_pipeline/          # Main package
│   ├── __init__.py
│   ├── config.py                # Environment configuration (pydantic-settings)
│   ├── models.py                # SQLAlchemy models (7 tables)
│   ├── pipeline.py              # Main async orchestrator
│   ├── cli.py                   # Typer CLI commands
│   ├── extractors/              # Data extraction layer
│   │   └── relay_client.py      # WebSocket relay connections
│   ├── transformers/            # Data transformation layer
│   │   ├── event_processor.py   # Event parsing/enrichment
│   │   └── metrics_calculator.py # Virality/trend scoring
│   ├── loaders/                 # Data loading layer
│   │   ├── database.py          # DB connection management
│   │   └── event_loader.py      # Event persistence
│   └── analytics/               # Analytics layer
│       ├── aggregator.py        # Background metrics aggregation
│       └── query.py             # Query interface for CLI/API
├── dashboard/                   # Streamlit dashboard
│   ├── Home.py                  # Main dashboard page
│   └── pages/                   # Multi-page dashboard
│       ├── 1_📈_Overview.py
│       ├── 2_🔥_Trending.py
│       ├── 3_📡_Network.py
│       ├── 4_👥_Users.py
│       ├── 5_🌐_Relays.py
│       └── 6_⚡_Zaps.py
├── tests/                       # Pytest test suite
│   ├── test_event_processor.py
│   └── test_metrics_calculator.py
├── examples/                    # Usage examples
├── pyproject.toml               # Project metadata and tool config
├── requirements.txt             # Direct dependencies
├── docker-compose.yml           # Multi-container setup
├── Dockerfile                   # Container image
└── Makefile                     # Common commands
```

## Database Schema

Seven core tables defined in `models.py`:

1. **nostr_events** - Raw Nostr events with full event data
2. **user_profiles** - User metadata from kind 0 events
3. **zaps** - Lightning zap receipts (kind 9735)
4. **content_metrics** - Aggregated engagement metrics per event
5. **trending_topics** - Trending hashtags with time windows
6. **relay_metrics** - Health and performance data for relays
7. **network_stats** - Network-wide aggregate statistics

## Nostr Event Kinds

The pipeline specifically handles these event kinds:

| Kind | Name | Description |
|------|------|-------------|
| 0 | Metadata | User profile information |
| 1 | Text Note | Regular posts |
| 6 | Repost | Reposts of other events |
| 7 | Reaction | Likes and emoji reactions |
| 9735 | Zap | Lightning payment receipts |

## Code Conventions

### Python Style
- **Line length:** 100 characters (configured in pyproject.toml)
- **Formatting:** Black for code formatting
- **Linting:** Ruff for linting
- **Type hints:** Required (mypy enforced with `disallow_untyped_defs`)
- **Python version:** 3.10+ (uses modern syntax like `match`, union types with `|`)

### Async Patterns
- The pipeline is fully async using `asyncio`
- Use `async def` for I/O-bound operations
- Use `asyncio.create_task()` for background tasks
- Use `asyncio.gather()` for concurrent operations

### Logging
- Use `structlog` for structured JSON logging
- Bind context with `logger.bind(component="name")`
- Log events with meaningful names: `log.info("event_name", key=value)`

### Database
- Use SQLAlchemy 2.0 style with `Session` context managers
- Always use `with db_manager.get_session() as session:`
- Define indexes for commonly queried columns
- Use `JSON` column type for flexible schema fields

### Configuration
- All config via environment variables
- Use `.env` file for local development
- Pydantic Settings validates and parses config
- Comma-separated lists supported (e.g., `NOSTR_RELAYS`)

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=nostr_pipeline --cov-report=html

# Run specific test
pytest tests/test_event_processor.py -v
```

### Test Conventions
- Test files: `test_*.py`
- Test functions: `test_*`
- Use `@pytest.fixture` for shared setup
- Use `pytest-asyncio` for async tests (configured with `asyncio_mode = "auto"`)

## Environment Variables

Key configuration options (see `.env.example`):

```bash
# Required for production
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379/0
NOSTR_RELAYS=wss://relay1.com,wss://relay2.com

# Pipeline tuning
BATCH_SIZE=100
PROCESSING_INTERVAL_SECONDS=5
EVENT_BUFFER_SIZE=10000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'console' for development
```

## Common Development Tasks

### Adding a New Event Kind

1. Add constant to `EventProcessor` class in `transformers/event_processor.py`
2. Create `_process_<kind>()` method
3. Add handling in `process_event()` method
4. If needed, create new model in `models.py`
5. Add loader method in `loaders/event_loader.py`
6. Update subscription filter in `pipeline.py:_subscribe_to_events()`

### Adding a New CLI Command

1. Add command function in `cli.py` with `@app.command()` decorator
2. Use `typer.Option()` for flags
3. Use `rich.table.Table` for formatted output
4. Use `console.print()` for styled output

### Adding a New Analytics Query

1. Add method to `AnalyticsQuery` class in `analytics/query.py`
2. Use SQLAlchemy ORM queries with session
3. Return structured dict/list data
4. Add CLI command if needed

### Adding Dashboard Page

1. Create new file in `dashboard/pages/` with emoji prefix for ordering
2. Follow existing page patterns with Streamlit
3. Use Plotly for interactive charts
4. Add auto-refresh with `st.rerun()` in sidebar

## Important Notes for AI Assistants

### When Modifying Code

1. **Maintain async patterns** - The pipeline is fully async; don't introduce blocking calls
2. **Use type hints** - All functions must have type annotations
3. **Follow existing patterns** - Match the style of surrounding code
4. **Update tests** - Add tests for new functionality
5. **Consider database indexes** - Add indexes for new query patterns

### When Debugging

1. Check `LOG_LEVEL=DEBUG` for verbose logging
2. Use `LOG_FORMAT=console` for readable local output
3. Check relay connectivity with `nostr-pipeline relays`
4. Verify database state with `nostr-pipeline stats`

### Common Gotchas

1. **Column naming** - The `metadata` column in `user_profiles` was renamed to `profile_metadata` to avoid SQLAlchemy reserved name conflict
2. **Relay URLs** - Must start with `wss://` and be comma-separated in env var
3. **Timestamps** - Nostr uses Unix timestamps, convert with `datetime.fromtimestamp()`
4. **Event IDs** - 64-character hex strings
5. **Pubkeys** - 64-character hex strings
6. **Zap amounts** - Stored in both millisatoshis and satoshis

### Performance Considerations

- Event buffer size: 10,000 events default
- Batch processing: 100 events per batch
- Metrics aggregation: Every 60 seconds
- Max 1,000+ events/second throughput

## Dependencies

Core dependencies (from requirements.txt):
- `nostr-sdk>=0.32.0` - Nostr protocol support
- `websockets>=12.0` - WebSocket connections
- `sqlalchemy>=2.0.0` - ORM
- `psycopg2-binary>=2.9.9` - PostgreSQL driver
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Environment config
- `structlog>=24.1.0` - Structured logging
- `typer>=0.9.0` - CLI framework
- `rich>=13.7.0` - Rich terminal output
- `streamlit>=1.31.0` - Dashboard
- `plotly>=5.18.0` - Interactive charts

Dev dependencies:
- `pytest>=7.4.0`, `pytest-asyncio>=0.21.0`, `pytest-cov>=4.1.0`
- `black>=23.12.0`, `ruff>=0.1.9`, `mypy>=1.8.0`
