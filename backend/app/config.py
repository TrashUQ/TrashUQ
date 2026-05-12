from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://trashuq:trashuq@db:5432/dashboard"
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    fl_model_size: int = 16
    fl_min_clients_per_round: int = 2
    mqtt_host: str = "mqtt"
    mqtt_port: int = 1883
    mqtt_topic_root: str = "arduino"
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
