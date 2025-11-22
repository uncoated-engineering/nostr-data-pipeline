"""Database manager for handling connections and sessions."""

from contextlib import contextmanager
from typing import Generator
import structlog
from sqlalchemy import create_engine, event, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from nostr_pipeline.models import Base
from nostr_pipeline.config import settings

logger = structlog.get_logger()


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.engine: Engine = None
        self.SessionLocal: sessionmaker = None
        self.log = logger.bind(component="database_manager")

    def initialize(self) -> None:
        """Initialize database engine and create tables."""
        self.log.info("initializing_database", url=self._safe_url(self.database_url))

        # Create engine with connection pooling
        if self.database_url.startswith("sqlite"):
            # SQLite specific settings
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
        else:
            # PostgreSQL settings with connection pool
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False,
            )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        # Create all tables
        self._create_tables()

        self.log.info("database_initialized")

    def _create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.log.info("tables_created")
        except Exception as e:
            self.log.error("table_creation_failed", error=str(e))
            raise

    def _safe_url(self, url: str) -> str:
        """Return URL with password masked."""
        if "@" in url:
            parts = url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split(":")
                return f"{user_pass[0]}:****@{parts[1]}"
        return url

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session context manager."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.log.error("session_error", error=str(e))
            raise
        finally:
            session.close()

    def get_new_session(self) -> Session:
        """Get a new database session (caller must manage lifecycle)."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()

    def dispose(self) -> None:
        """Dispose of the database engine and connections."""
        if self.engine:
            self.engine.dispose()
            self.log.info("database_disposed")

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.log.error("health_check_failed", error=str(e))
            return False


# Global database instance
db_manager = DatabaseManager()
