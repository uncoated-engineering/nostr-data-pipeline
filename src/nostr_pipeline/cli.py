"""Command-line interface for Nostr pipeline."""

import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import structlog

from nostr_pipeline.pipeline import NostrPipeline
from nostr_pipeline.config import settings
from nostr_pipeline.loaders.database import DatabaseManager
from nostr_pipeline.analytics.query import AnalyticsQuery

app = typer.Typer(help="Nostr Data Pipeline - Real-time ETL for Nostr Protocol")
console = Console()


@app.command()
def run():
    """Start the ETL pipeline."""
    console.print("[bold green]Starting Nostr Data Pipeline...[/bold green]")
    console.print(f"Relays: {', '.join(settings.nostr_relays)}")
    console.print(f"Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")

    asyncio.run(_run_pipeline())


async def _run_pipeline():
    """Run the pipeline."""
    pipeline = NostrPipeline()

    try:
        await pipeline.initialize()
        await pipeline.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down gracefully...[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Pipeline failed: {e}[/bold red]")
        raise


@app.command()
def init_db():
    """Initialize the database schema."""
    console.print("[bold blue]Initializing database...[/bold blue]")

    try:
        db_manager = DatabaseManager()
        db_manager.initialize()
        console.print("[bold green]✓ Database initialized successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Database initialization failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show network statistics."""
    console.print("[bold blue]Fetching network statistics...[/bold blue]\n")

    db_manager = DatabaseManager()
    db_manager.initialize()

    with db_manager.get_session() as session:
        query = AnalyticsQuery()
        overview = query.get_network_overview(session)

        if not overview:
            console.print("[yellow]No statistics available yet.[/yellow]")
            return

        # Users table
        users_table = Table(title="👥 User Metrics")
        users_table.add_column("Metric", style="cyan")
        users_table.add_column("Value", style="green", justify="right")

        users_table.add_row("Total Users", f"{overview['users']['total']:,}")
        users_table.add_row("Active (1h)", f"{overview['users']['active_1h']:,}")
        users_table.add_row("Active (24h)", f"{overview['users']['active_24h']:,}")
        users_table.add_row("New (24h)", f"{overview['users']['new_24h']:,}")

        console.print(users_table)
        console.print()

        # Events table
        events_table = Table(title="📝 Event Metrics")
        events_table.add_column("Metric", style="cyan")
        events_table.add_column("Value", style="green", justify="right")

        events_table.add_row("Total Events", f"{overview['events']['total']:,}")
        events_table.add_row("Events (1h)", f"{overview['events']['events_1h']:,}")
        events_table.add_row("Events (24h)", f"{overview['events']['events_24h']:,}")
        events_table.add_row("Notes (24h)", f"{overview['events']['notes_24h']:,}")

        console.print(events_table)
        console.print()

        # Zaps table
        zaps_table = Table(title="⚡ Zap Metrics")
        zaps_table.add_column("Metric", style="cyan")
        zaps_table.add_column("Value", style="green", justify="right")

        zaps_table.add_row("Total Zaps", f"{overview['zaps']['total']:,}")
        zaps_table.add_row("Zaps (24h)", f"{overview['zaps']['zaps_24h']:,}")
        zaps_table.add_row("Total Sats", f"{overview['zaps']['total_sats']:,}")
        zaps_table.add_row("Sats (24h)", f"{overview['zaps']['sats_24h']:,}")

        console.print(zaps_table)


@app.command()
def trending(
    hours: int = typer.Option(24, help="Time window in hours"),
    limit: int = typer.Option(10, help="Number of results"),
):
    """Show trending hashtags."""
    console.print(f"[bold blue]Top {limit} trending hashtags (last {hours}h)...[/bold blue]\n")

    db_manager = DatabaseManager()
    db_manager.initialize()

    with db_manager.get_session() as session:
        query = AnalyticsQuery()
        trending_topics = query.get_trending_hashtags(session, hours=hours, limit=limit)

        if not trending_topics:
            console.print("[yellow]No trending topics found.[/yellow]")
            return

        table = Table(title="🔥 Trending Hashtags")
        table.add_column("#", style="dim", width=3)
        table.add_column("Hashtag", style="cyan bold")
        table.add_column("Mentions", style="green", justify="right")
        table.add_column("Authors", style="blue", justify="right")
        table.add_column("Zaps", style="yellow", justify="right")
        table.add_column("Score", style="magenta", justify="right")

        for i, topic in enumerate(trending_topics, 1):
            table.add_row(
                str(i),
                f"#{topic['hashtag']}",
                f"{topic['mention_count']:,}",
                f"{topic['unique_authors']:,}",
                f"{topic['total_zaps']:,}",
                f"{topic['trend_score']:.2f}",
            )

        console.print(table)


@app.command()
def top_zapped(
    hours: int = typer.Option(24, help="Time window in hours"),
    limit: int = typer.Option(10, help="Number of results"),
):
    """Show top zapped content."""
    console.print(f"[bold blue]Top {limit} zapped content (last {hours}h)...[/bold blue]\n")

    db_manager = DatabaseManager()
    db_manager.initialize()

    with db_manager.get_session() as session:
        query = AnalyticsQuery()
        top_content = query.get_top_zapped_content(session, hours=hours, limit=limit)

        if not top_content:
            console.print("[yellow]No content found.[/yellow]")
            return

        table = Table(title="⚡ Top Zapped Content")
        table.add_column("#", style="dim", width=3)
        table.add_column("Event ID", style="cyan")
        table.add_column("Sats", style="green", justify="right")
        table.add_column("Zaps", style="blue", justify="right")
        table.add_column("Replies", style="yellow", justify="right")
        table.add_column("Reposts", style="magenta", justify="right")
        table.add_column("Score", style="red", justify="right")

        for i, content in enumerate(top_content, 1):
            table.add_row(
                str(i),
                content["event_id"][:16] + "...",
                f"{content['zap_total_sats']:,}",
                f"{content['zap_count']:,}",
                f"{content['reply_count']:,}",
                f"{content['repost_count']:,}",
                f"{content['virality_score']:.2f}",
            )

        console.print(table)


@app.command()
def user(pubkey: str):
    """Show statistics for a specific user."""
    console.print(f"[bold blue]Fetching stats for {pubkey[:16]}...[/bold blue]\n")

    db_manager = DatabaseManager()
    db_manager.initialize()

    with db_manager.get_session() as session:
        query = AnalyticsQuery()
        user_stats = query.get_user_stats(session, pubkey)

        if not user_stats:
            console.print("[yellow]User not found.[/yellow]")
            return

        # Profile info
        profile = user_stats["profile"]
        if profile.get("name") or profile.get("display_name"):
            name = profile.get("display_name") or profile.get("name")
            console.print(f"[bold]{name}[/bold]")

        if profile.get("about"):
            console.print(f"{profile['about'][:100]}...")

        console.print()

        # Stats table
        table = Table(title="📊 User Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Events", f"{user_stats['activity']['total_events']:,}")
        table.add_row("Zaps Received", f"{user_stats['zaps']['received_count']:,}")
        table.add_row("Sats Received", f"{user_stats['zaps']['received_sats']:,}")
        table.add_row("Zaps Sent", f"{user_stats['zaps']['sent_count']:,}")
        table.add_row("Sats Sent", f"{user_stats['zaps']['sent_sats']:,}")

        console.print(table)


@app.command()
def relays():
    """Show relay health metrics."""
    console.print("[bold blue]Relay Health Status...[/bold blue]\n")

    db_manager = DatabaseManager()
    db_manager.initialize()

    with db_manager.get_session() as session:
        query = AnalyticsQuery()
        relay_health = query.get_relay_health(session)

        if not relay_health:
            console.print("[yellow]No relay metrics available yet.[/yellow]")
            return

        table = Table(title="🌐 Relay Metrics")
        table.add_column("Relay", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Latency", style="blue", justify="right")
        table.add_column("Events", style="yellow", justify="right")
        table.add_column("Errors", style="red", justify="right")

        for relay in relay_health:
            status = "✓ Online" if relay["is_connected"] else "✗ Offline"
            latency = f"{relay['latency_ms']:.0f}ms" if relay["latency_ms"] else "N/A"

            table.add_row(
                relay["relay_url"].replace("wss://", ""),
                status,
                latency,
                f"{relay['events_received']:,}",
                f"{relay['error_count']}",
            )

        console.print(table)


@app.command()
def version():
    """Show version information."""
    from nostr_pipeline import __version__

    console.print(f"[bold]Nostr Data Pipeline[/bold] v{__version__}")
    console.print("Real-time ETL for Nostr Protocol")


if __name__ == "__main__":
    app()
