# TrashUQ Mockups

Carpeta de proves per validar el flux real de l'app:
- MQTT cap a Mosquitto (`arduino/<device-id>/...`)
- Federated Learning per gRPC (`Join`, `GetGlobalModel`, `SubmitUpdate`)

## Requisits

```bash
pip install paho-mqtt grpcio
```

## 1) Simular dispositius MQTT

```bash
python mockups/scripts/mock_mqtt_publisher.py --devices 3 --loops 20
```

Això publica `status`, `metrics`, `event`, `classification`, `help`, `logs`.

## 2) Simular clients de Federated Learning (gRPC)

```bash
PYTHONPATH=backend python mockups/scripts/mock_fl_clients.py --clients 3 --rounds 3
```

Aquest script:
- fa `Join` per cada client
- demana model global
- envia actualitzacions locals
- espera agregació per ronda (`FL_MIN_CLIENTS_PER_ROUND` al backend)

## Variables útils

- MQTT host/port/topic root:

```bash
python mockups/scripts/mock_mqtt_publisher.py --help
```

- gRPC host/port i dimensió model:

```bash
PYTHONPATH=backend python mockups/scripts/mock_fl_clients.py --help
```
