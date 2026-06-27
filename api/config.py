from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://synth:synth@localhost:5432/synthdata"
    redis_url: str = "redis://localhost:6379/0"
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
