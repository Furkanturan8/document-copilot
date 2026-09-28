from pathlib import Path
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_role_key: SecretStr

    database_url: SecretStr

    openai_api_key: SecretStr
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    # Hybrid retrieval tuning; see app/retrieval/README.md.
    retrieval_candidate_k: int = 50  # hits fetched from each search path before fusion
    retrieval_top_k: int = 10  # fused passages returned
    retrieval_rrf_k: int = 60  # RRF constant in 1 / (k + rank)
    retrieval_neighbor_radius: int = 1  # chunks before/after each hit, same document
    retrieval_fts_config: str = "english"
    retrieval_fts_keyword_model: str = "gpt-4.1-mini"
    retrieval_fts_keyword_min: int = 3
    retrieval_fts_keyword_max: int = 5
    retrieval_fts_keyword_fast_path_tokens: int = 5  # shorter queries skip the keyword LLM

    allowed_origins: Annotated[list[str], NoDecode]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str) -> list[str]:
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("database_url")
    @classmethod
    def _reject_transaction_pooler(cls, value: SecretStr) -> SecretStr:
        # The transaction pooler (port 6543) breaks migrations, extensions and index creation.
        if ":6543/" in value.get_secret_value():
            raise ValueError(
                "DATABASE_URL points at the Supabase transaction pooler (port 6543); "
                "use the direct or session connection string"
            )
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        # SQLAlchemy maps plain postgresql:// to psycopg2; this project ships psycopg 3.
        return self.database_url.get_secret_value().replace(
            "postgresql://", "postgresql+psycopg://", 1
        )


settings = Settings()
