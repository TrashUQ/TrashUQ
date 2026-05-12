from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://trashuq:trashuq@db:5432/dashboard"
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    fl_model_size: int = 16
    fl_min_clients_per_round: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
