# Nostr Analytics Dashboard

A beautiful, interactive web dashboard for visualizing real-time Nostr data.

## Features

### 🏠 Home
- Quick network statistics overview
- Connection status monitoring
- Easy navigation to all analytics views
- Auto-refresh capabilities

### 📈 Overview
- **Key Metrics**: Total users, active users, events, and zaps
- **User Activity**: Real-time gauges and distribution charts
- **Lightning Stats**: Zap volumes, distribution, and trends
- **Event Statistics**: Event rates and breakdowns
- **Activity Timeline**: 24-hour event activity visualization
- **Network Health**: Activity scores, growth rates, engagement metrics

### 🔥 Trending
- **Trending Hashtags**: Real-time trending topics with scores
- **Top Content**: Most zapped and viral posts
- **Engagement Analysis**: Hashtag reach vs engagement scatter plots
- **Virality Metrics**: Content virality scoring and distribution
- **Interactive Charts**: Bar charts, treemaps, and scatter plots

### 📡 Network
- **Activity Timeline**: Real-time event distribution over time
- **Historical Stats**: User growth and network trends
- **Live Metrics**: Events/second, active users, zap rates
- **Velocity Indicators**: Growth rate, activity rate, engagement gauges

### 👥 Users
- **Top Zap Recipients**: Leaderboard of most tipped users
- **Top Content Creators**: Best performing authors by engagement
- **User Lookup**: Search and view detailed user profiles
- **Engagement Analysis**: Quality vs volume scatter plots

### 🌐 Relays
- **Relay Overview**: Connection status and performance metrics
- **Health Scores**: Individual relay health monitoring
- **Latency Comparison**: Performance benchmarking
- **Event Distribution**: Relay contribution analysis

### ⚡ Zaps
- **Distribution Analytics**: Mean, median, percentiles
- **Activity Timeline**: Zaps and sats over time
- **Top Zappers**: Most generous tippers
- **Top Recipients**: Most tipped users
- **Size Categories**: Small, medium, large, huge zaps

## Quick Start

### Using Docker (Recommended)

```bash
# Start all services including dashboard
docker-compose up -d

# Dashboard will be available at:
# http://localhost:8501
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
make dashboard

# Or manually:
cd dashboard
streamlit run Home.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

## Configuration

### Auto-Refresh

Each page supports auto-refresh:
1. Check the "Auto-refresh" checkbox in the sidebar
2. Adjust the refresh interval (5-120 seconds)
3. Dashboard will automatically update with fresh data

### Time Windows

Most analytics support customizable time windows:
- 6 hours
- 12 hours
- 24 hours (default)
- 48 hours
- 72 hours
- 7 days

### Data Limits

Control the number of results displayed:
- Trending hashtags: 5-50 items
- Top content: 5-50 items
- User leaderboards: Configurable limits

## Pages in Detail

### Overview Page

The overview page provides a comprehensive snapshot of network health:

**Metrics Displayed:**
- Total users and growth
- Active user counts (1h, 24h)
- Event volumes and rates
- Zap statistics and distribution
- Real-time activity gauges
- 24-hour activity timeline

**Visualizations:**
- Gauge charts for activity levels
- Pie charts for user distribution
- Area charts for timeline activity
- Bar charts for zap distribution

### Trending Page

Discover what's hot on Nostr:

**Features:**
- Trend score calculation based on velocity and engagement
- Hashtag mention volume treemaps
- Engagement scatter plots (mentions vs authors)
- Virality analysis for top content
- Detailed tabular data

**Algorithms:**
- Trend Score = (mentions/hour) × log(unique_authors) × (1 + log(zaps))
- Virality Score with time decay

### Network Page

Monitor real-time network activity:

**Components:**
- Stacked area charts for event types
- Historical user growth trends
- Daily events and sats trends
- Real-time velocity gauges
- Network health indicators

**Metrics:**
- Growth rate (%)
- Events per active user
- Zap engagement rate (%)

### Users Page

User analytics and leaderboards:

**Leaderboards:**
- Top zap recipients by total sats
- Top content creators by engagement
- Most active users

**User Profiles:**
- Search by pubkey
- Profile information
- Activity statistics
- Zap metrics (sent/received)

### Relays Page

Relay health monitoring:

**Monitoring:**
- Connection status (online/offline)
- Latency measurements
- Event throughput
- Error tracking
- Health scores (0-100)

**Health Score Formula:**
```
health_score = (latency_score + error_score) / 2
latency_score = max(0, 100 - latency_ms / 10)
error_score = max(0, 100 - error_count * 5)
```

### Zaps Page

Lightning Network analytics:

**Statistics:**
- Total zaps and sats
- Mean, median, percentiles
- Distribution analysis
- Time-series charts

**Categories:**
- 🥉 Small: 1-100 sats
- 🥈 Medium: 101-1000 sats
- 🥇 Large: 1001-10000 sats
- 💎 Huge: 10000+ sats

## Dashboard Architecture

```
dashboard/
├── Home.py                 # Main entry point
└── pages/
    ├── 1_📈_Overview.py    # Network overview
    ├── 2_🔥_Trending.py    # Trending content
    ├── 3_📡_Network.py     # Network activity
    ├── 4_👥_Users.py       # User analytics
    ├── 5_🌐_Relays.py      # Relay health
    └── 6_⚡_Zaps.py         # Zap analytics
```

## Technology Stack

- **Framework**: Streamlit 1.31+
- **Visualization**: Plotly, Altair
- **Data**: Pandas, SQLAlchemy
- **Backend**: PostgreSQL database
- **Styling**: Custom CSS for modern UI

## Performance Tips

1. **Auto-Refresh**: Use longer intervals (30-60s) for better performance
2. **Time Windows**: Shorter windows load faster
3. **Data Limits**: Reduce limits for quicker rendering
4. **Database**: Ensure PostgreSQL is properly indexed
5. **Caching**: Streamlit caches database connections automatically

## Customization

### Custom CSS

Edit `Home.py` to modify the dashboard theme:

```python
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(90deg, #8B5CF6 0%, #EC4899 100%);
    }
</style>
""", unsafe_allow_html=True)
```

### Adding New Pages

1. Create new file in `dashboard/pages/`
2. Name format: `N_ICON_Title.py` (e.g., `7_📊_Custom.py`)
3. Streamlit automatically adds to navigation
4. Use existing pages as templates

### Custom Queries

Add new analytics queries in `src/nostr_pipeline/analytics/query.py`:

```python
def get_custom_metric(self, session: Session) -> Dict[str, Any]:
    # Your custom query
    results = session.query(...).all()
    return process_results(results)
```

Then use in dashboard:

```python
from nostr_pipeline.analytics.query import AnalyticsQuery

query = AnalyticsQuery()
data = query.get_custom_metric(session)
```

## Troubleshooting

### Dashboard Won't Start

```bash
# Check if port 8501 is available
lsof -i :8501

# Kill existing process
kill -9 <PID>

# Restart dashboard
make dashboard
```

### No Data Displayed

1. Check if pipeline is running: `docker-compose logs pipeline`
2. Verify database connection: Check DATABASE_URL
3. Ensure data exists: Run `nostr-pipeline stats`
4. Wait a few minutes for data collection

### Slow Performance

1. Reduce auto-refresh frequency
2. Use shorter time windows
3. Lower data limits
4. Check database query performance
5. Add database indexes if needed

### Browser Issues

- Clear browser cache
- Try incognito/private mode
- Use Chrome/Firefox for best compatibility
- Disable browser extensions

## Production Deployment

### Using Docker

```bash
# Production docker-compose.yml
docker-compose -f docker-compose.prod.yml up -d
```

### Behind Reverse Proxy

Nginx configuration:

```nginx
server {
    listen 80;
    server_name dashboard.example.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Authentication

Add basic auth to docker-compose.yml:

```yaml
dashboard:
  environment:
    - STREAMLIT_SERVER_ENABLE_CORS=false
    - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
```

Or use external auth proxy (OAuth2 Proxy, Authelia, etc.)

## API Integration

The dashboard uses the same analytics API as the CLI:

```python
from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery

db_manager = DatabaseManager()
db_manager.initialize()

with db_manager.get_session() as session:
    query = AnalyticsQuery()

    # Get any metric
    overview = query.get_network_overview(session)
    trending = query.get_trending_hashtags(session, hours=24)
    top_content = query.get_top_zapped_content(session, hours=24)
```

## Screenshots

See the dashboard in action:
- Home page with quick stats
- Overview with comprehensive metrics
- Trending hashtags visualization
- Real-time network activity
- User leaderboards
- Relay health monitoring
- Zap distribution analysis

## Contributing

Want to add new visualizations?

1. Fork the repository
2. Create a new page in `dashboard/pages/`
3. Add analytics queries if needed
4. Submit a pull request

## License

MIT License - same as the main project

## Support

- Documentation: This file
- Issues: GitHub Issues
- Community: Nostr (#nostr-pipeline)
