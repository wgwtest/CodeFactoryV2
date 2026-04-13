from pathlib import Path

from app.config import Settings


def test_settings_resolve_data_roots_from_repo_root(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    monkeypatch.chdir(repo_root / "apps/api")

    settings = Settings()

    assert settings.storage_root == str(repo_root / ".data" / "storage")
    assert settings.knowledge_output_root == str(repo_root / ".data" / "knowledge_output")
    assert settings.application_modeling_root == str(repo_root / ".data" / "application_modeling")
