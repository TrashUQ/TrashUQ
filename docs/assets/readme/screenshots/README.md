# README Screenshot Capture Notes

The checked-in `dashboard_overview.png` documents the local dashboard. To capture
a new screenshot with the current demo scripts, start the stack from the repository root:

```sh
cd .
cp -n backend/.env.example backend/.env
docker compose up --build
```

and, in another terminal:

```sh
cd edge
uv sync
cd ..
edge/.venv/bin/python docs/demos/mockups/scripts/mock_mqtt_publisher.py --devices 2 --loops 300
```

The dashboard uses client-side tab state instead of route-specific URLs, so the remaining tab screenshots are best captured manually from `http://localhost:3000`:

1. `live_devices.png`: open the **Live Devices** tab after the simulator or real node has published status.
2. `event_stream.png`: open **Alerts & Logs** after MQTT event/log traffic appears.
3. `fl_metrics.png`: open **Federated Rounds** or **Model Performance** after metric messages populate the charts.

Save any additional screenshots in this directory so the README can reference them with relative paths.
