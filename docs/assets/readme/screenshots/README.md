# README Screenshot Capture Notes

The checked-in screenshot `dashboard_overview.png` was captured from the real local stack after running:

```sh
cd TrashUQ
docker compose up --build
```

and, in another terminal:

```sh
cd ../edge
uv run python -m app.edge_simulator
```

The dashboard uses client-side tab state instead of route-specific URLs, so the remaining tab screenshots are best captured manually from `http://localhost:3000`:

1. `live_devices.png`: open the **Live Devices** tab after the simulator or real node has published status.
2. `event_stream.png`: open **Alerts & Logs** after MQTT event/log traffic appears.
3. `fl_metrics.png`: open **Federated Rounds** or **Model Performance** after metric messages populate the charts.

Save any additional screenshots in this directory so the README can reference them with relative paths.
