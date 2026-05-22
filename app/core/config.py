"""Application configuration loaded from environment / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # External LLM (the only non-local dependency).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Storage.
    database_url: str = "sqlite:///./data/app.db"
    data_dir: str = "./data"

    # Embeddings / NLP.
    embedding_model: str = "all-MiniLM-L6-v2"
    spacy_model: str = "en_core_web_sm"

    # Retrieval / chunking.
    top_k: int = 6
    chunk_size: int = 180
    chunk_overlap: int = 40

    # Token map encryption (Fernet). Auto-generated if blank.
    token_encryption_key: str = ""

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
