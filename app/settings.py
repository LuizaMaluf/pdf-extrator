from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    anthropic_api_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    confidence_threshold: float = 0.85
    max_few_shot_examples: int = 5
    min_few_shot_score: float = 0.6
    pdf_upload_dir: str = "/app/uploads"


settings = Settings()
