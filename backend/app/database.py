"""Database engine, session factory, and declarative base.

SQLAlchemy is used as the ORM layer. The connection URL comes from settings so
migrating from SQLite to PostgreSQL/MySQL later is a one-line change.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

DATABASE_URL = settings.resolved_database_url

# ``check_same_thread`` is a SQLite-only quirk: FastAPI serves requests from a
# threadpool, so we must disable SQLite's default single-thread guard. The
# argument is ignored for other databases.
connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# For file-based SQLite, make sure the parent directory exists so SQLite can
# create both the database file and its journal/WAL files.
if DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:
    db_file = Path(DATABASE_URL[len("sqlite:///"):])
    db_file.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""


def init_db() -> None:
    """Create all tables. Called once at application startup.

    Importing the models module here ensures they are registered on ``Base``
    before ``create_all`` runs.
    """
    from app import models  # noqa: F401  (import for side effects)

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
