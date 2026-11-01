from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+asyncpg://payments:payments@localhost:5432/payments'
    rabbit_url: str = 'amqp://guest:guest@localhost:5672/'
    api_key: str = 'change-me'

    outbox_poll_interval: float = 1.0
    outbox_batch_size: int = 100

    max_attempts: int = 3
    retry_base_delay: float = 1.0
    webhook_timeout: float = 10.0


settings = Settings()
