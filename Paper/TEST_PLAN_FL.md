# Plan de Ejecución — Validación FL con 2 Arduinos

Este documento es el procedimiento operativo para rellenar el informe
`PART_A_Arduino_Mixed_Test_Report_SHORT.md`. La parte mecánica del bin (PIR,
LED, tapa, cámara montada) **no se prueba** — se asume operativa. El foco son
ingesta MQTT, persistencia, dashboard y, sobre todo, fine-tuning + rondas
federadas con dos clientes edge físicos.

---

## 0. Notación

- **Host backend**: `bepes-server` (alias). Define `SERVER_HOST` antes de empezar:
  `export SERVER_HOST=172.20.10.12` (ajusta a la IP real).
- **Arduino A (cámara real)** → `device_id = unoq-01`, modo `real_camera`.
- **Arduino B (mock)** → `device_id = unoq-02`, modo `fake_camera`
  (`bin_mpu` genera frames sintéticos en RAM, sin USB cam).
- Daemon en cada nodo: `python -m bin_mpu.main`.

**Importante**: por defecto `device_id = <bin-class>-bin-01`. El informe pide
`unoq-01` / `unoq-02`, así que **siempre pasar `--device-id`** explícito.

---

## 1. Preparación previa (una sola vez)

### 1.1 Backend / stack TrashUQ
Desde el host `bepes-server`:

```bash
# Stack completo (backend API, frontend, MQTT broker, PostgreSQL, gRPC FL coord)
docker compose up -d
docker compose ps              # verificar 6 servicios "running/healthy"

# Pinear el tamaño del modelo FL al esperado por el cliente (4 clases → 20 floats)
# El daemon lo imprime al arrancar: "set FL_MODEL_SIZE=20 on the backend".
# Asegurar que la variable de entorno del coordinador gRPC vale 20.
```

### 1.2 Dos Arduinos / UNO Q MPU
`deploy.sh` acepta ahora `DEVICE_ID` y `CAMERA` por env var:

```bash
# Arduino A (cámara real) — unoq-01
BOARD=arduino@<IP_A> DEVICE_ID=unoq-01 CAMERA=real CAMERA_INDEX=2 \
  SERVER_HOST=$SERVER_HOST ./deploy.sh --run

# Arduino B (mock) — unoq-02
BOARD=arduino@<IP_B> DEVICE_ID=unoq-02 CAMERA=fake \
  SERVER_HOST=$SERVER_HOST ./deploy.sh --run
```

Otros overrides: `BIN_CLASS=paper`, `FL_TRIGGER_SAMPLES=2`, `HTTP_PORT=8080`.

`--fl-trigger-samples 2` baja el umbral para disparar una ronda cada **2**
etiquetas (por defecto 10). Para conseguir ≥5 rondas necesitarás ≥10
etiquetas por nodo — las inyectaremos automáticamente con `tools/feed_labels.py`
(ver Paso C).

---

## 2. Mapping del código → tablas del informe

| Sección informe | Fuente real de datos | Comando / endpoint |
|---|---|---|
| §5 Service Readiness | Docker stack | `curl :4000/health`, `docker compose ps` |
| §6 Node Connectivity | MQTT topics `arduino/<id>/{status,classification,metrics,event}` | `mosquitto_sub -t 'arduino/+/+' -v` |
| §6 Persistencia | Tabla `mqtt_messages` | `psql ... select … from mqtt_messages` |
| §7 FL rounds | gRPC `Join` / `GetGlobalModel` / `SubmitUpdate` (`bin_mpu/fl.proto`) + logs del coordinador | logs del backend + `arduino/<id>/event` con `name=fl_round_*` |
| §7 per-client | `bin_mpu/fl_client.py` emite `event` `fl_round_local_done` y `fl_round_submitted` con `round`, `model_version`, `aggregated`, `num_samples`, `local_loss`, `local_accuracy` | suscribir a `arduino/+/event` |
| §8 Performance | `bin_mpu/pipeline.py` (latencia inferencia), MQTT timestamps | derivado de logs + comparación `timestamp` MQTT vs `created_at` PG |
| §9 Frontend | dashboard `:3000` | inspección visual + screenshots |

Observación: el campo `model_version` del coordinador se llama así en el RPC,
y se publica en MQTT como `modelVersion` dentro de `metrics`. Mismo dato.

---

## 3. Procedimiento ordenado

### Paso A — Sanity (§5)
Con el stack arriba, **antes** de encender los Arduinos:

```bash
curl -s http://$SERVER_HOST:4000/health | tee evidence/health.json
curl -s http://$SERVER_HOST:4000/api/dashboard/bootstrap > evidence/bootstrap_pre.json

# MQTT alcanzable
mosquitto_pub -h $SERVER_HOST -p 1883 -t 'test/ping' -m 'hello' && echo OK

# gRPC FL coordinator alcanzable (puerto abierto)
nc -z $SERVER_HOST 50051 && echo "FL gRPC OK"
```

Rellenar §5: cada chequeo → `PASS/FAIL` + breve observación.

### Paso B — Arranque y conectividad por nodo (§6)
1. Arrancar **solo `unoq-01`**. En una terminal separada del host:
   ```bash
   mosquitto_sub -h $SERVER_HOST -p 1883 -t 'arduino/unoq-01/+' -v
   ```
   Verificar que llegan: `status` (con `cpu`, `ram`, `heartbeat`),
   `classification` (al menos una al apuntar la cámara a algo), `event`.
2. Arrancar **`unoq-02`** (fake camera). En modo `--fake-camera` el pipeline
   genera frames sintéticos y producirá `classification` con `source` indistinto
   (no añade `mode` por payload). Verificar `status` con `mode: "real_camera"`
   por defecto; **dado que el código no diferencia el `mode` en el `status`**,
   anotar manualmente en el informe que `unoq-02` corre en `--fake-camera`.
3. Persistencia:
   ```bash
   docker compose exec db psql -U trashuq -d dashboard -c \
     "select topic, payload->>'device_id' as dev, created_at
        from mqtt_messages
        where topic like 'arduino/unoq-%/%'
        order by created_at desc limit 20;"
   ```
   Esperar filas con `dev = unoq-01` y `dev = unoq-02`.

### Paso C — Inyectar etiquetas para disparar rondas (§7)
Endpoint nuevo en el daemon: `POST /api/inject` recibe `multipart`
con `label` + `file` (imagen JPG/PNG), llama a
`pipeline.inject_labeled_sample()`, persiste la muestra como `label_src='user'`
y dispara el hook FL — saltándose cámara, UI iPad y `WAITING_LABEL`.

Driver: `tools/feed_labels.py` (corre en el Mac, no en los Arduinos). Coge
imágenes pre-etiquetadas de `model/trashnet/data/dataset-resized/<class>/`
(cardboard / glass / paper / plastic) y las postea a cada bin:

```bash
# Mismas imágenes a los dos bins (modelo IID):
uv run python tools/feed_labels.py \
  --bin http://<IP_A>:8080 \
  --bin http://<IP_B>:8080 \
  --per-class 5 --delay 1.0

# Distintas imágenes por bin (más realista para FL):
uv run python tools/feed_labels.py \
  --bin http://<IP_A>:8080 \
  --bin http://<IP_B>:8080 \
  --per-class 5 --delay 1.0 --shuffle-bins
```

Con `--per-class 5` × 4 clases = 20 etiquetas/bin y `--fl-trigger-samples 2` en
el daemon, salen ~10 rondas por bin (más que de sobra para llenar las 5 filas
del informe).

`--delay 1.0` deja respirar las rondas: cada `on_user_label` puede arrancar un
hilo de fine-tune; sin delay se acumulan muchas y `_busy.acquire` salta las
solapadas (`bin_mpu/fl_client.py:81`), lo que sesgaría el conteo de rondas.

### Paso D — Capturar las rondas
En el host, suscribirse a los `event` de FL antes/durante:

```bash
mosquitto_sub -h $SERVER_HOST -p 1883 -t 'arduino/+/event' -v \
  | tee evidence/fl_events.log
```

Buscar los `name` `fl_round_local_done` (con `num_samples`, `local_loss`,
`local_accuracy`) y `fl_round_submitted` (con `model_version`, `aggregated`,
`round`).

En el coordinador (logs del contenedor `trashuq-backend` o servicio gRPC):
```bash
docker compose logs -f --tail=200 backend | grep -Ei 'round|aggregat|client|fl'
```

Por cada ronda anotar en la tabla §7:
- `Active Clients` / `Joined Clients` → del log del coordinador
- `Updates Received` → `n` `SubmitUpdate` recibidos antes de aggregar
- `Aggregation YES/NO` → flag `round_aggregated` de la respuesta
- `Model Version Before/After` → `model_version` pre/post
- `Duration (s)` → `t(submit_2) - t(get_global_model_1)` (timestamps de evento)

### Paso E — Performance (§8)
Métricas y dónde sacarlas:

| Métrica | Fuente |
|---|---|
| `inference_ms` (mean, p95) | `bin_mpu/pipeline.py` loguea por inferencia; grep en logs del daemon |
| `FPS` | derivar de la cadencia de `classification` MQTT |
| `MQTT publish delay` | `timestamp` del payload vs `created_at` en `mqtt_messages` |
| `Dashboard refresh lag` | cronometrar a ojo (WS push); típicamente <1s |
| `Total messages` | `select count(*) from mqtt_messages where payload->>'device_id' = '…';` |
| `Mean confidence` | `select avg((payload->>'confidence')::float) … where topic like 'arduino/%/classification';` |
| `Invalid payload rate` | logs del backend (`json_decode_error` o similar) |
| `Dropped message rate` | comparar `count` publicados (logs daemon) vs `count` PG |

### Paso F — Consistencia (§9)
Visualmente, en `http://$SERVER_HOST:3000`:
- Ambos `unoq-01` y `unoq-02` listados como online.
- Panel de status muestra `cpu`/`ram`/`heartbeat` coherentes con MQTT crudo.
- Gráficos de `loss`/`accuracy`/`round` actualizan tras cada `metrics` push.
- Stream de clasificaciones muestra eventos de ambos `device_id`.
- `GET /api/dashboard/bootstrap` (post-test) contiene ambos.

Capturar **una screenshot** del dashboard con ambos dispositivos para §10.

### Paso G — Evidencias (§10)
Crear carpeta `Paper/evidence/` con:

```
evidence/
  health.json
  bootstrap_pre.json
  bootstrap_post.json
  fl_events.log
  mqtt_dump_sample.txt        # 1 classification + 1 metrics por nodo
  fl_submitupdate_response.txt
  pg_recent_messages.txt
  dashboard.png
```

---

## 4. Limitaciones a declarar (§12)
Confirmar/añadir al cierre del informe:
- `unoq-02` usa `--fake-camera` (frames sintéticos en `bin_mpu/camera.py`), no
  representa variabilidad real de iluminación/posición.
- El modelo es solo clasificación (`MobileNetV2` finetuneado en TrashNet,
  4 clases). `bbox: null` siempre.
- FL intercambia únicamente la **cabeza de calibración** (20 floats), no toda
  la red. `globalLoss`/`globalAccuracy` reportados son aproximaciones; el
  cliente publica `global*` = `local*` para una única-bin agregada
  (`bin_mpu/mqtt_telemetry.py:121`).
- Si la red entre Arduino y `bepes-server` es WiFi compartido, la latencia
  MQTT y la duración de ronda pueden variar significativamente.

---

## 5. Checklist mínimo para dar §7 por cerrado

- [ ] ≥5 rondas completadas con `aggregated=true` en al menos 3 de ellas.
- [ ] `model_version` estrictamente creciente entre rondas agregadas.
- [ ] Ambos nodos aparecen en `SubmitUpdate` de al menos 2 rondas.
- [ ] Evidencia gRPC capturada (respuesta `SubmitUpdateResponse` con
      `current_round` y `model_version`).
- [ ] `metrics` publicado en MQTT visible en dashboard tras cada ronda.

---

## 6. Riesgos / cosas que suelen petar

1. **`device_id` por defecto** se cuela como `paper-bin-01` y rompe el filtro
   del dashboard (`unoq-*`). Mitigación: `--device-id` obligatorio.
2. **`FL_MODEL_SIZE`** en el coordinador distinto de 20 → `Join` devuelve
   `ok=false` o `apply_global_weights` descarta el vector
   (`bin_mpu/finetuner.py:152`).
3. **Pesos globales todo-ceros**: el cliente los ignora intencionadamente
   (`finetuner.py:163`). Si en el informe ves `model_version > 0` pero el
   cliente sigue con cabeza local, es esto — anotar.
4. **`--fl-trigger-samples` muy alto** → no se dispara ronda y la tabla §7
   queda vacía. Con 2 está bien para validación; en producción está en 10.
5. **MQTT no llega a PG**: revisar el bridge MQTT→backend en logs; el topic
   debe matchear `arduino/+/#`.
