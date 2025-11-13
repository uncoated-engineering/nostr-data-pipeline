# Quick Start Guide

Get the Nostr Data Pipeline running in 5 minutes!

## Option 1: Docker (Easiest)

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Start everything
docker-compose up -d

# 3. Check logs
docker-compose logs -f pipeline

# 4. View stats (in another terminal)
docker-compose exec pipeline nostr-pipeline stats

# 5. See trending hashtags
docker-compose exec pipeline nostr-pipeline trending
```

Done! The pipeline is now collecting data from Nostr relays.

## Option 2: Local Installation

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -e .

# 3. Setup environment
cp .env.example .env
# Edit .env if needed (defaults work with SQLite)

# 4. Initialize database
nostr-pipeline init-db

# 5. Run pipeline
nostr-pipeline run
```

## Verify It's Working

Open another terminal and run:

```bash
# View network statistics
nostr-pipeline stats

# Show trending hashtags
nostr-pipeline trending --hours 24

# Show top zapped content
nostr-pipeline top-zapped --hours 24

# Check relay health
nostr-pipeline relays
```

## What's Happening?

1. **Connecting**: Pipeline connects to 5 default Nostr relays
2. **Streaming**: Events are streamed in real-time via WebSocket
3. **Processing**: Events are parsed and enriched with metrics
4. **Storing**: Data is saved to PostgreSQL (or SQLite locally)
5. **Analyzing**: Metrics are aggregated every 60 seconds

## Monitoring

Watch the logs to see:
- Connection status to relays
- Events being received and processed
- Metrics aggregation runs
- Any errors or warnings

```bash
# Docker
docker-compose logs -f pipeline

# Local
# Logs output to console
```

## Customization

Edit `.env` to:
- Add/remove Nostr relays
- Change database connection
- Adjust batch sizes
- Configure aggregation intervals
- Set buffer sizes

## Next Steps

1. **Explore Data**: Use the CLI commands to explore collected data
2. **Write Queries**: Check `examples/analytics_example.py`
3. **Build Dashboard**: Use the analytics API to build visualizations
4. **Scale Up**: Add more relays, increase workers, optimize database

## Troubleshooting

### Can't connect to relays
- Check internet connection
- Some relays may be temporarily down
- Try different relays in `.env`

### Database errors
- Ensure PostgreSQL is running (for Docker setup)
- Check DATABASE_URL in `.env`
- Run `nostr-pipeline init-db` again

### Low event count
- Wait a few minutes for data to accumulate
- Check relay connections with `nostr-pipeline relays`
- Increase number of relays in config

## Getting Help

- Read the full [README.md](README.md)
- Check the [examples/](examples/) directory
- Review logs for error messages
- Open an issue on GitHub
