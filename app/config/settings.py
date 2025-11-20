from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，使用 Pydantic Settings 方便从环境变量或 .env 加载。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field("社交类APP隐私政策合规检测系统", validation_alias="APP_NAME")
    api_prefix: str = Field("/api/v1", validation_alias="API_PREFIX")

    # 数据库配置
    postgres_user: str = Field("ppna_user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field("ppna_password", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("ppna_db", validation_alias="POSTGRES_DB")
    postgres_host: str = Field("localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, validation_alias="POSTGRES_PORT")

    # Celery / Broker
    broker_url: str = Field("redis://localhost:6379/0", validation_alias="CELERY_BROKER_URL")
    result_backend: str = Field(
        "redis://localhost:6379/1", validation_alias="CELERY_RESULT_BACKEND"
    )
    celery_task_default_queue: str = Field(
        "detection_queue", validation_alias="CELERY_DEFAULT_QUEUE"
    )

    # Milvus
    milvus_host: str = Field("localhost", validation_alias="MILVUS_HOST")
    milvus_port: str = Field("19530", validation_alias="MILVUS_PORT")
    milvus_collection: str = Field(
        "privacy_policy_knowledge", validation_alias="MILVUS_COLLECTION"
    )

    # 模型 & 推理配置
    dashscope_api_key: str = Field("", validation_alias="DASHSCOPE_API_KEY")
    dashscope_base_url: str = Field(
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias="DASHSCOPE_BASE_URL",
    )
    dashscope_embedding_model: str = Field(
        "text-embedding-v4",
        validation_alias="DASHSCOPE_EMBED_MODEL",
    )
    dashscope_moe_model: str = Field(
        "qwen3-30b-a3b-instruct-2507",
        validation_alias="DASHSCOPE_MOE_MODEL",
    )
    bert_model_name: str = Field(
        "hfl/chinese-bert-wwm-ext",
        validation_alias="BERT_MODEL_NAME",
    )
    bert_max_chunk_tokens: int = Field(
        360,
        validation_alias="BERT_MAX_CHUNK_TOKENS",
    )
    risk_model_path: str = Field(
        "models/risk_classifier.json",
        validation_alias="RISK_MODEL_PATH",
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

