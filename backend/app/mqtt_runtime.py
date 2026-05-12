from __future__ import annotations

import paho.mqtt.client as mqtt

from app.config import settings
from app.service import ingest_mqtt_message


class MqttIngestRuntime:
    def __init__(self) -> None:
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code != 0:
            return
        client.subscribe(f"{settings.mqtt_topic_root}/+/#")

    def _on_message(self, _client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
        payload = message.payload.decode("utf-8", errors="replace")
        ingest_mqtt_message(topic=message.topic, payload=payload)

    def start(self) -> None:
        self._client.connect(settings.mqtt_host, settings.mqtt_port, 60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
