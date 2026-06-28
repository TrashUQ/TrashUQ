# Reviewer 1 - Quantization + Synthetic Dataset Clarification

Repartiment de feina per als dos punts restants del revisor.

---

## Item A: Gradient Quantization per Communication Efficiency

### Objectiu

Afegir anàlisi de quantització de grads/weights a la simulació FL (Part B) per mostrar com reduir el coll de botella de comunicació.

### Estat actual

- `experiments/part_b/run_part_b.py` simula FedAvg amb float32 complet
- La comunicació es compta a `bytes_sent` / `bytes_received` per ronda
- Per 20 clients: 3.941 MB totals, accuracy-per-MB = 0.24
- `edge/bin_mpu/finetuner.py` i `backend/app/fl_coordinator.py` usen `list[float]` (float32) via gRPC
- El model a Part B és lineal: 16x16x4 + 4 = 1028 floats = 4112 bytes

### Tasques

#### Tasca 1: Afegir suport de quantització al simulador

**Fitxer**: `experiments/part_b/run_part_b.py`

**Què fer**: Crear funcions de quantització i desquantització, i integrar-les al loop d'experiment.

```python
def quantize_stochastic(weights: np.ndarray, bits: int = 8) -> tuple[np.ndarray, float, float]:
    \"\"\"Stochastic rounding quantization: float32 -> int{bits}.\"\"\"
    min_val = weights.min()
    max_val = weights.max()
    scale = (2**bits - 1) / (max_val - min_val + 1e-12)
    # Stochastic rounding
    scaled = (weights - min_val) * scale
    floor = np.floor(scaled).astype(np.int32)
    residual = scaled - floor
    rng = np.random.default_rng()
    quantized = np.where(rng.random(weights.shape) < residual, floor + 1, floor).astype(np.int32)
    return quantized, min_val, scale


def dequantize(quantized: np.ndarray, min_val: float, scale: float, bits: int = 8) -> np.ndarray:
    \"\"\"Recover float32 from quantized ints.\"\"\"
    return quantized.astype(np.float32) / scale + min_val
```

Després, al loop `run_experiment`, després de `local_train`:
```python
# Quantitzar abans d'enviar
q_weights, q_min, q_scale = quantize_stochastic(local_model, bits=8)
q_bytes = q_weights.nbytes + 8  # weights + min/scale metadata
bytes_received += q_bytes + 24  # overwrite línia 536
# Simular desquantització al coordinador
received_model = dequantize(q_weights, q_min, q_scale)
local_models.append(received_model)  # enlloc de local_model original
```

**Lliurable**: Branca amb `quantize_stochastic` i `dequantize`, i modificació del loop per comptar bytes quantitzats.

#### Tasca 2: Fer una execució comparativa

- Reexecutar la simulació Part B sencera amb quantització a 8 bits
- Reexecutar amb quantització a 4 bits (opcional)
- Recollir: accuracy final, loss, MB totals, accuracy-per-MB per cada configuració

**Output**: Taula comparativa:

| Configuració | Clients | Final Acc. (%) | Total Comm. (MB) | Acc-per-MB |
|---|---|---|---|---|
| float32 (original) | 20 | 93.75 | 3.941 | 0.24 |
| quant-8bit | 20 | ? | ~0.985 | ~0.95 |
| quant-4bit | 20 | ? | ~0.493 | ~1.90 |

#### Tasca 3: Redactar subsecció pel paper

Afegir a Section 4 una subsecció 4.4 (o dins de 4.3) "Communication Efficiency via Gradient Quantization" que:
- Expliqui el problema (linear growth in Section 4.3)
- Descrivi la tècnica (stochastic quantization)
- Mostri la taula comparativa
- Conclusió: es pot reduir comunicació ~4x (8-bit) o ~8x (4-bit) amb pèrdua negligible d'accuracy

#### Tasca 4 (opcional, si sobra temps): Aplicar al pipeline real

Modificar `fl_client.py` (edge) i `fl_coordinator.py` (backend) per suportar `local_weights` com a bytes quantitzats + metadades, enlloc de `list[float]` directe.

---

### Plan d'execució

| Pas | Qui | Estona |
|---|---|---|
| T1: funcions quantització + integració | | 1.5-2h |
| T2: execució comparativa (8-bit, 4-bit) | | 1-2h (CPU, 3 seeds x 4 settings x 2 configs) |
| T3: redactar text pel paper | | 1h |
| T4: opcional - pipeline real | | 2-3h |

---

## Item B: Synthetic TrashNet Fallback Clarification

### Objectiu

Millorar l'explicació al paper del synthetic dataset perquè el revisor entengui què es va fer exactament i per què.

### Estat actual

- A Section 4.1 només hi ha: "The dataset used in this campaign was a documented synthetic TrashNet-style fallback (4 classes, 220 samples per class) because a local real TrashNet corpus was unavailable at execution time."
- `run_part_b.py` genera dades sintètiques de 16x16 amb patrons geomètrics (línies, quadrats, diagonals)
- El generador és `generate_synthetic_dataset()` (línia 244)
- Si hi ha un dataset real a `--dataset-root`, el fa servir automàticament
- El report diu "Dataset path: generated://synthetic-trashnet-style"

### Tasca

#### Escriure text ampliat per Section 4.1

Substituir la frase actual per un paràgraf que expliqui:

1. **Per què synthetic?** TrashNet real no estava disponible localment al moment de l'execució (el dataset no té una font oficial estable, requereix descàrrega manual). Es va prioritzar la reproducibilitat i automatització.

2. **Què es va generar?** 4 classes (cardboard, glass, paper, plastic), 220 samples/class, imatges 16×16 en escala de grisos. Cada classe té un prototip geomètric:
   - Cardboard: franges horitzontals
   - Glass: diagonal
   - Paper: rectangle central
   - Plastic: franges verticals
   - S'hi afegeix sorra gaussiana, variacions d'escala, shifts aleatoris, i contaminació entre classes

3. **Limitacions:**
   - No captura la complexitat visual de residus reals
   - Les imatges (16×16) són molt més petites que TrashNet (224×224)
   - Els patrons geomètrics no representen textures reals
   - Per això els resultats (93-94% accuracy) només demostren convergència FL, no rendiment en el món real

4. **Compatibilitat amb real:** El simulador `run_part_b.py` detecta automàticament si hi ha TrashNet real a `--dataset-root` i el fa servir si existeix. El synthetic és un fallback reproducible.

5. **Impacte en resultats:** Com que l'objectiu de Part B és avaluar l'escalabilitat de FedAvg (convergència, comunicació), no el rendiment absolut del model, el synthetic dataset és suficient per validar les tendències.

**Output**: Text LaTeX (~150-200 paraules) llest per substituir el paràgraf actual.

---

### Plan d'execució

| Pas | Qui | Estona |
|---|---|---|
| Analitzar `generate_synthetic_dataset()` i `make_synthetic_prototypes()` | | 15min |
| Redactar text ampliat | | 30-45min |
| Inserir al `.tex` | | 5min |

---

## Resum de càrrega

| Item | Qui | Estona estimada |
|---|---|---|
| A-T1: quantize functions | | 1.5-2h |
| A-T2: run comparison | | 1-2h |
| A-T3: write paper section | | 1h |
| A-T4: opcional pipeline real | | 2-3h |
| B: synthetic explanation | | ~1h |
| **Total** | | **~4.5-7h** |
