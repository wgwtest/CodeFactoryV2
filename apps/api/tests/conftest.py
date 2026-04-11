import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.main import create_app


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_local() as session:
        yield session


@pytest.fixture()
def temp_storage_dir(tmp_path):
    return tmp_path / "storage"
