from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"
    database_url: str = "sqlite+pysqlite:///:memory:"
    storage_bucket: str = "knowledge-warehouse"
    storage_root: str = ".data/storage"
    knowledge_output_root: str = ".data/knowledge_output"
    default_archive_id: str = "20161116-nas"
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

    model_config = SettingsConfigDict(env_file=".env", env_prefix="KW_")


settings = Settings()
