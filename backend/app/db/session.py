from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

# SQLite is only ever used in the test suite (see backend/tests/conftest.py)
# -- production always runs against DATABASE_URL=postgresql://... . An
# in-memory SQLite database is otherwise dropped after every connection, so
# it needs a single shared connection (StaticPool) to persist for a test.
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    echo=not _is_sqlite,
    future=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=StaticPool if _is_sqlite and ":memory:" in settings.DATABASE_URL else None,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def translate_integrity_error(db: Session, message: str):
    """Roll back and raise a 409 with `message` if the wrapped block hits a DB constraint violation."""
    try:
        yield
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, message) from exc