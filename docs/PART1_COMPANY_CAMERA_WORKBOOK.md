# PART 1 - COMPANY: Hardware Camera Latency

**Responsable**: _________________________
**Data límit**: _________________________

---

## Objectiu

Mesurar latència d'inferència amb càmera real a l'Arduino UNO Q i reportar els números per incloure'ls a Section 3 del paper.

---

## Tasques

### Tasca A: Crear bench_real_camera.py

**Fitxer nou**: `edge/benchmarks/bench_real_camera.py`

**Comportament** (usant `bench_inference.py` com a plantilla):
- Obrir càmera via V4L2 (cv2.VideoCapture, com fa `camera.py`)
- Escalfar: 5 frames de descart
- Per cada iteració (default 200):
  - Capturar 1 frame (mesurar `capture_time`)
  - Executar predict_frame (mesurar `inference_time`)
  - Repetir per burst_size frames (default 5)
  - Al final del burst: majority vote
- Guardar resultats a `benchmarks/results/real_camera_latency.json`
- Imprimir: mean, p50, p95, p99, min, max per:
  - Single-frame capture time
  - Single-frame inference time
  - Burst total time (5 frames)
  - Capture-cycle estimate (burst + intervals 200ms)

**Checklist**:
- [ ] `bench_real_camera.py` creat i funcional en mode --fake-camera (per testejar)
- [ ] Logging a JSON + stdout
- [ ] Testejat en local (amb --fake-camera)

### Tasca B: Executar a l'Arduino UNO Q

**Requisits hardware**:
- [ ] Arduino UNO Q amb Debian 13
- [ ] Càmera USB connectada i detectada per V4L2
- [ ] `models/trash_classifier.tflite` present al device
- [ ] Dependències Python instal·lades (cv2, tflite-runtime, numpy)

**Execució**:
```bash
cd /path/to/edge
python -m benchmarks.bench_real_camera \
    --iterations 200 \
    --burst 5 \
    --camera-index 0 \
    --report results/arduino_uno_q_latency.json
```

**Checklist**:
- [ ] Execució 1: il·luminació normal
- [ ] Execució 2: il·luminació baixa (opcional, per veure si afecta)
- [ ] Fitxer JSON de resultats copiat al repo
- [ ] Captura de pantalla del output (per incloure al paper si cal)

### Tasca C: Reportar resultats

Ompliu:

| Mètrica | mean | p50 | p95 | p99 | max |
|---------|------|-----|-----|-----|-----|
| Single-frame capture (ms) | ____ | ____ | ____ | ____ | ____ |
| Single-frame inference (ms) | ____ | ____ | ____ | ____ | ____ |
| Burst 5 frames total (ms) | ____ | ____ | ____ | ____ | ____ |
| Capture-cycle estimate (ms) | ____ | ____ | ____ | ____ | ____ |

**Notes/addendes**:
- Resolució de càmera utilitzada: _________________________
- Model TFLite utilitzat: _________________________
- Condicions d'il·luminació: _________________________
- Alguna anomalia observada? _________________________

---

## Output per al paper

Text proposat per Section 3.3 (o nova subsecció "Camera Inference Latency"):

```
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________
```

---

## Temps estimat

| Tasca | Temps |
|-------|-------|
| A: bench_real_camera.py | 1.5-2h |
| B: Execució a placa | 1-2h |
| C: Report | 30min |
| **Total** | **~3-4h** |
