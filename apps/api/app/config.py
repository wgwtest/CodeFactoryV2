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

    model_config = SettingsConfigDict(env_file=".env", env_prefix="KW_")


settings = Settings()
