from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="FIRSAT_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://firsat:firsat@localhost:5432/firsat_radari"
    log_level: str = "INFO"
    raw_storage_path: Path = BACKEND_ROOT / "data" / "raw"
    ingestion_api_enabled: bool = False
    ingestion_api_max_pages: int = Field(default=10, ge=1, le=100)
    normalization_api_enabled: bool = False
    normalization_api_max_items: int = Field(default=500, ge=1, le=10_000)
    metrics_api_enabled: bool = False
    problem_extraction_api_enabled: bool = False
    problem_extraction_api_max_items: int = Field(
        default=500,
        ge=1,
        le=10_000,
    )
    entity_link_review_api_enabled: bool = False
    problem_clustering_api_enabled: bool = False
    problem_cluster_review_api_enabled: bool = False
    commercial_validation_api_enabled: bool = False
    source_governance_api_enabled: bool = False
    opportunity_materialization_api_enabled: bool = False
    ontology_claim_api_enabled: bool = False
    scoring_api_enabled: bool = False
    research_review_api_enabled: bool = False
    research_api_enabled: bool = False
    sales_export_api_enabled: bool = False
    research_settings_api_enabled: bool = False
    scheduler_api_enabled: bool = False
    scheduler_lease_minutes: int = Field(default=120, ge=15, le=1_440)
    scheduler_poll_seconds: int = Field(default=60, ge=10, le=3_600)
    audit_log_enabled: bool = False
    operations_api_enabled: bool = False
    source_freshness_hours: int = Field(default=48, ge=1, le=8_760)
    daily_cost_budget_usd: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_cost_budget_usd: Decimal = Field(default=Decimal("0"), ge=0)
    cors_allowed_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,"
        "http://127.0.0.1:3002"
    )
    mutation_api_key: SecretStr | None = None
    github_token: SecretStr | None = None
    stack_exchange_key: SecretStr | None = None
    validation_hash_secret: SecretStr | None = None

    @field_validator("raw_storage_path")
    @classmethod
    def resolve_raw_storage_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value.resolve()
        return (BACKEND_ROOT / value).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
