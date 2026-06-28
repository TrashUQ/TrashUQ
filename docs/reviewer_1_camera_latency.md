# Reviewer 1 - Real Camera Inference Latency

## Objectiu

Afegir al paper les mesures de latència d'inferència amb càmera real al hardware Arduino UNO Q (Qualcomm QRB2210). El reviewer vol veure quant de temps passa des que es captura un frame fins que es classifica.

## Estat actual

- El daemon edge (`bin_mpu/main.py`) suporta càmera real via `--camera-index 0` (V4L2), però a la validació hardware (Section 3.3) es va usar `--fake-camera`
- El `bench_inference.py` existeix però usa soroll aleatori, no frames reals
- El `bench_e2e.py` mockeja la càmera completa

## Tasca

Instrumentar el pipeline per mesurar i reportar latència real, i documentar com executar-ho a les plaques.

---

### Part A: Instrumentar el pipeline edge (codi)

> **Què fer**: Afegir logging de timing a cada etapa del pipeline de captura+classificació.

**Fitxer**: `edge/bin_mpu/pipeline.py` + `edge/bin_mpu/classifier.py`

**Canvis concrets:**

1. A `classifier.py`, afegir un mètode `timed_predict_frame(frame) -> tuple[Prediction, float]` que retorni la predicció + el temps d'inferència en ms:
   ```python
   def timed_predict_frame(self, frame: np.ndarray) -> tuple[Prediction, float]:
       t0 = time.perf_counter()
       result = self.predict_frame(frame)
       elapsed = (time.perf_counter() - t0) * 1000.0
       return result, elapsed
   ```

2. A `pipeline.py`, al mètode `_handle_mcu_event` (o on es processi el burst), afegir timings:
   - `t_capture_start / t_capture_end` -- temps per capturar el burst de N frames
   - Per cada frame del burst: `t_inf_start / t_inf_end` -- latència individual
   - `t_total_start / t_total_end` -- de PIR trigger a lid_open (o low_confidence)
   - Publicar aquestes mètriques per MQTT a `arduino/<device-id>/timing`

3. Crear un flag `--benchmark` a `main.py` que:
   - Activa logging detallat de timing a cada cicle
   - Desa un CSV amb timings per sessió
   - Es compatible amb `--fake-camera` i amb càmera real (per comparar)

**Lliurable**: Branch amb els canvis + un CSV d'exemple d'una execució de 100+ cicles.

---

### Part B: Script de benchmark amb càmera real

> **Què fer**: Un script autònom que capti N frames amb la càmera, mesuri latència per frame+burst, i generi un report.

**Fitxer nou**: `edge/benchmarks/bench_real_camera.py`

**Comportament:**
1. Obre la càmera via V4L2 (cv2.VideoCapture)
2. Escalfa (5+ frames de descart)
3. Captura N iteracions (default 100) de `burst_size` frames cadascuna (default 5)
4. Per cada frame: mesura `capture_time` (camera.read) + `inference_time` (classifier.predict_frame)
5. Per cada burst: calcula `total_burst_time` i `classify_time` (majority vote)
6. Guarda resultats a `benchmarks/results/real_camera_latency.json`
7. Imprimeix: mean/p50/p95/p99/min/max per frame, per burst, per cicle complet

**Dependències**: Les mateixes que el daemon + càmera V4L2 disponible.

**Notes:**
- Usar `cv2.CAP_V4L2` explícitament (com fa `camera.py`)
- No depen de la resta del pipeline (MQTT, FL, etc.) -- pur benchmark
- Si no hi ha càmera, falla amb missatge clar

---

### Part C: Execució a les plaques (protocol)

1. Connectar una Arduino UNO Q amb càmera USB
2. SSH a la placa
3. Assegurar que `models/trash_classifier.tflite` hi és
4. Executar:
   ```bash
   python -m benchmarks.bench_real_camera \
       --iterations 200 \
       --burst 5 \
       --camera-index 0 \
       --report results/arduino_uno_q_latency.json
   ```
5. Copiar el JSON de resultats al repositori
6. Repetir en condicions d'il·luminació diferents (opcional però bo)

---

### Part D: Text pel paper (Section 3.3 o Section 3 nova)

Afegir una subsecció "Camera Inference Latency" amb:
- Setup: càmera USB, V4L2, 1280x720, MobileNetV2 TFLite
- Mètriques: single-frame inference latency (mean/p50/p95), burst latency (5 frames), capture-cycle estimate (amb intervals de 200ms)
- Taula senzilla amb els números
- Nota: la latència d'inferència domina sobre la de captura

---

### Plan d'execució

| Pas | Qui | Estona |
|---|---|---|
| A: Instrumentar pipeline | | 2-3h |
| B: Crear bench_real_camera.py | | 1-2h |
| C: Executar a les plaques | (requereix hardware) | 30min |
| D: Redactar secció pel paper | | 1h |
