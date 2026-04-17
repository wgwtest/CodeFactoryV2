from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARCHIVE_SOURCE_DIR = REPO_ROOT / "20161116体系结构文献翻译汇总"
DEFAULT_ARCHIVE_EXTRACT_ROOT = REPO_ROOT / ".data/source_archives/20161116"
DEFAULT_ARCHIVE_EXTRACT_PARENT = REPO_ROOT / ".data/source_archives"


def _resolve_repo_path(value: str | Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return str(path)


class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"
    database_url: str = "sqlite+pysqlite:///:memory:"
    storage_bucket: str = "knowledge-warehouse"
    storage_root: str = ".data/storage"
    knowledge_output_root: str = ".data/knowledge_output"
    application_modeling_root: str = ".data/application_modeling"
    tool_hub_root: str = ".data/tool_hub"
    software_design_root: str = ".data/software_design"
    default_archive_id: str = "20161116-nas"
    default_archive_name: str = "20161116 NAS 知识库"
    default_archive_source_dir: str = str(DEFAULT_ARCHIVE_SOURCE_DIR)
    default_archive_extract_root: str = str(DEFAULT_ARCHIVE_EXTRACT_ROOT)
    archive_extract_root: str = str(DEFAULT_ARCHIVE_EXTRACT_PARENT)
    published_knowledge_backend: str = "json"
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    llm_provider: str = "openai"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_temperature: float = 0
    llm_context_window: int | None = None
    llm_supports_function_calling: bool | None = None
    llm_supports_chat: bool | None = None
    docling_pdf_enabled: bool = False
    llm_enrichment_enabled: bool = False
    llm_enrichment_segment_limit: int = 24
    llm_enrichment_char_limit: int = 16000
    formal_chunk_segment_threshold: int = 120
    formal_chunk_char_threshold: int = 50000
    formal_chunk_char_limit: int = 32000

    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), env_prefix="KW_")

    @model_validator(mode="after")
    def resolve_repository_relative_paths(self) -> "Settings":
        self.storage_root = _resolve_repo_path(self.storage_root)
        self.knowledge_output_root = _resolve_repo_path(self.knowledge_output_root)
        self.application_modeling_root = _resolve_repo_path(self.application_modeling_root)
        self.tool_hub_root = _resolve_repo_path(self.tool_hub_root)
        self.software_design_root = _resolve_repo_path(self.software_design_root)
        self.default_archive_source_dir = _resolve_repo_path(self.default_archive_source_dir)
        self.default_archive_extract_root = _resolve_repo_path(self.default_archive_extract_root)
        self.archive_extract_root = _resolve_repo_path(self.archive_extract_root)
        return self


settings = Settings()
