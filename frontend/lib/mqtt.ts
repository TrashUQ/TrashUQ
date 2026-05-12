import type { MqttClient } from "mqtt";

export interface MqttMessage {
  topic: string;
  payload: string;
  timestamp: number;
}

export interface MqttConfig {
  brokerUrl: string;
  topicRoot: string;
  username?: string;
  password?: string;
  onMessage?: (message: MqttMessage) => void;
  onConnect?: () => void;
  onError?: (error: unknown) => void;
}

export class MqttService {
  private client: MqttClient | null = null;
  private config: MqttConfig;

  constructor(config: MqttConfig) {
    this.config = config;
  }

  async connect(): Promise<void> {
    try {
      const mqtt = await import("mqtt");
      const mqttConnect = mqtt.connect || (mqtt as any).default?.connect;
      
      if (!mqttConnect) {
        throw new Error("mqtt.connect is not available");
      }

      this.client = mqttConnect(this.config.brokerUrl, {
        reconnectPeriod: 3000,
        connectTimeout: 30000,
        clean: true,
        username: this.config.username,
        password: this.config.password,
      });

      this.client.on("connect", () => {
        console.log("MQTT connected to", this.config.brokerUrl);
        this.config.onConnect?.();

        // Subscribe to Arduino topics
        const topics = [
          `${this.config.topicRoot}/+/status`,
          `${this.config.topicRoot}/+/metrics`,
          `${this.config.topicRoot}/+/event`,
          `${this.config.topicRoot}/+/classification`,
          `${this.config.topicRoot}/+/help`,
          `${this.config.topicRoot}/+/logs`,
        ];

        topics.forEach((topic) => {
          this.client?.subscribe(topic, (err) => {
            if (err) {
              console.error("MQTT subscribe error:", err);
            } else {
              console.log("Subscribed to", topic);
            }
          });
        });
      });

      this.client.on("error", (error) => {
        console.error("MQTT error:", error);
        this.config.onError?.(error);
      });

      this.client.on("message", (topic, payloadBuffer) => {
        const payload = payloadBuffer.toString();
        const message: MqttMessage = {
          topic,
          payload,
          timestamp: Date.now(),
        };
        console.log("MQTT message:", message);
        this.config.onMessage?.(message);
      });
    } catch (error) {
      console.error("MQTT connection error:", error);
      this.config.onError?.(error);
    }
  }

  disconnect(): void {
    this.client?.end(true);
    this.client = null;
  }

  publish(topic: string, payload: string): void {
    this.client?.publish(topic, payload);
  }
}
