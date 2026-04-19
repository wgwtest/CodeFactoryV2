import pytest
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import create_app


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture(autouse=True)
def reset_database_schema() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session() -> Session:
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def temp_storage_dir(tmp_path):
    return tmp_path / "storage"
