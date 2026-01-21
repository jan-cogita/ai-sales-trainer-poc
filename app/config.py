from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Storage
    storage_backend: str = "local"
    local_data_path: str = "./data"

    # S3 (optional)
    s3_bucket_name: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "sales_trainer_docs"

    # RAG mode
    use_full_context: bool = False  # True = load all docs, False = vector search

    # LLM
    llm_provider: str = "openai"
    openai_api_key: str = ""
    google_api_key: str = ""

    @property
    def embedding_size(self) -> int:
        """Return embedding size based on provider."""
        return 768 if self.llm_provider == "gemini" else 1536

    # Voice
    voice_provider: str = "openai"  # "openai" or "elevenlabs"
    elevenlabs_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
