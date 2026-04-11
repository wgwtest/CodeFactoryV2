from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        return {
            "future": True,
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    if database_url.startswith("sqlite"):
        return {"future": True, "connect_args": {"check_same_thread": False}}
    return {"future": True}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
