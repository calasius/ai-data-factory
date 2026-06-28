from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://synth:synth@localhost:5432/synthdata"
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Ensure the database URL always uses the asyncpg async driver.

        Railway's Postgres service injects DATABASE_URL with the psycopg2
        scheme (postgresql:// or postgresql+psycopg2://), which is
        incompatible with SQLAlchemy's async engine. Replace any synchronous
        driver reference with asyncpg so the async engine can connect.
        """
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
                "postgres://", "postgresql+asyncpg://", 1
            )
        if "+psycopg2" in v:
            return v.replace("+psycopg2", "+asyncpg")
        return v

    projects_dir: str = "/data/projects"
    templates_dir: str = "./tools/templates"
    commands_dir: str = "./.claude/commands"
    max_concurrent_pipelines: int = 3
    secret_key: str = "changeme"

    # opencode + DeepSeek generation engine.
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-pro"            # coding agent (needs reasoning)
    deepseek_authoring_model: str = "deepseek-v4-flash"  # schema/plan (fast, non-reasoning)
    deepseek_edit_model: str = "deepseek-chat"         # intermediate artifact edits
    opencode_config_path: str = "./api/opencode.json"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
