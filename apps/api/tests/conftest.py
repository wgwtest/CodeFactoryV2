import pytest
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import create_app


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
def db_session() -> Session:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def temp_storage_dir(tmp_path):
    return tmp_path / "storage"
