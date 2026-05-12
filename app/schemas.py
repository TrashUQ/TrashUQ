from pydantic import BaseModel


class IngestMqttRequest(BaseModel):
    topic: str
    payload: str
    timestamp: int | None = None
