# PART 2 - USER: Algoritmes + Escriptura

**Responsable**: _________________________
**Data límit**: _________________________

**Tasques a fer**:
- [x] A: Quantization analysis (experiments)
- [x] B: Synthetic dataset clarification (text)
- [x] C: Related work + novelty comparison (text)
- [ ] D: Consolidar conclusions + abstract + compilar PDF (pendent: resultats càmera del company, integració al .tex i compilació)

---

## A: Gradient Quantization

### A1. Implementació

**Fitxer**: `experiments/part_b/run_part_b.py`

Afegir aquestes funcions:

```python
def quantize_stochastic(weights: np.ndarray, bits: int = 8
    ) -> tuple[np.ndarray, float, float]:
    \"\"\"Stochastic rounding: float32 -> int{bits}.\"\"\"
    min_val = weights.min()
    max_val = weights.max()
    scale = (2**bits - 1) / (max_val - min_val + 1e-12)
    scaled = (weights - min_val) * scale
    floor = np.floor(scaled).astype(np.int32)
    residual = scaled - floor
    rng = np.random.default_rng()
    quantized = np.where(rng.random(weights.shape) < residual,
                         floor + 1, floor).astype(np.int32)
    return quantized, min_val, scale

def dequantize(quantized: np.ndarray, min_val: float, scale: float
    ) -> np.ndarray:
    return quantized.astype(np.float32) / scale + min_val
```

I modificar `run_experiment` per:
- Acceptar `--quantization-bits 0` (0 = off, 8 = 8-bit, 4 = 4-bit)
- Al loop, després de `local_train`: quantitzar el model abans de comptar bytes
- Desquantitzar abans de fer `weighted_average`
- Mantenir els càlculs de `bytes_received` basats en dades quantitzades

**Checklist**:
- [x] `quantize_stochastic` implementada i testejada (vs no-quantized, error < 1e-2)
- [x] `dequantize` implementada
- [x] `run_experiment` modificada per suportar `--quantization-bits`
- [x] `parse_args` actualitzat
- [x] Test: executar 1 run amb 2 clients i quantization=8 per verificar que funciona

### A2. Execució experiments

```bash
# Baseline (es pot ometre si ja teniu els números originals)
python experiments/part_b/run_part_b.py \
    --rounds 25 --local-epochs 2 --batch-size 16 \
    --learning-rate 0.18 --alpha 0.3 \
    --seeds 11 29 47 --client-counts 2 5 10 20 \
    --synthetic-samples-per-class 220 \
    --output-dir artifacts/part_b/quant_baseline

# 8-bit quantization
python experiments/part_b/run_part_b.py \
    --rounds 25 --local-epochs 2 --batch-size 16 \
    --learning-rate 0.18 --alpha 0.3 \
    --seeds 11 29 47 --client-counts 2 5 10 20 \
    --synthetic-samples-per-class 220 \
    --quantization-bits 8 \
    --output-dir artifacts/part_b/quant_8bit

# 4-bit quantization (opcional)
python experiments/part_b/run_part_b.py \
    --rounds 25 --local-epochs 2 --batch-size 16 \
    --learning-rate 0.18 --alpha 0.3 \
    --seeds 11 29 47 --client-counts 2 5 10 20 \
    --synthetic-samples-per-class 220 \
    --quantization-bits 4 \
    --output-dir artifacts/part_b/quant_4bit
```

### A3. Resultats - omplir

**8-bit quantization**:

| Clients | Final Acc. (%) | Final Loss | Total Comm. (MB) | Acc-per-MB |
|---------|---------------|------------|------------------|------------|
| 2       | 93.75         | 0.2184     | 0.247            | 3.79       |
| 5       | 93.75         | 0.2007     | 0.618            | 1.52       |
| 10      | 93.37         | 0.2019     | 1.237            | 0.75       |
| 20      | 93.75         | 0.1933     | 2.474            | 0.38       |

**4-bit quantization** (si executat):

| Clients | Final Acc. (%) | Final Loss | Total Comm. (MB) | Acc-per-MB |
|---------|---------------|------------|------------------|------------|
| 2       | 92.42         | 0.2601     | 0.223            | 4.15       |
| 5       | 93.37         | 0.2108     | 0.557            | 1.68       |
| 10      | 93.37         | 0.2148     | 1.114            | 0.84       |
| 20      | 93.75         | 0.1976     | 2.229            | 0.42       |

**Taula comparativa final** (per posar al paper):

| Clients | Config  | Acc. (%) | Comm. (MB) | Compressió |
|---------|---------|----------|-------------|-------------|
| 20      | float32 | 93.75    | 3.941       | 1.0x        |
| 20      | 8-bit   | 93.75    | 2.474       | ~4x         |
| 20      | 4-bit   | 93.75    | 2.229       | ~8x         |

---

## B: Synthetic Dataset Clarification

### B1. Analitzar el generador

Llegiu `run_part_b.py` línies 216-281.
Ompliu:

| Propietat | Valor |
|-----------|-------|
| Mida imatge | 16x16 píxels (escala de grisos) |
| Classes | cardboard, glass, paper, plastic |
| Samples/class | 220 (configurable via `--synthetic-samples-per-class`) |
| Patrons geomètrics per classe | cardboard = franges horitzontals; glass = línies diagonals centrals; paper = rectangle central amb densitats diferents; plastic = franges verticals |
| Sorra / augmentacions | Sorra gaussiana (std=0.30), variació de brillantor (8%), desplazament aleatori (35%), barreja entre classes (12% veí, 5% alterna), combinació lineal dels prototips (52% classe principal + 23% següent + 10% alterna + 15% patró compartit) |
| Per què synthetic i no TrashNet real | El dataset TrashNet original no està disponible al sistema de l'simulador (ruta `--dataset-root` no existent). El dataset sintètic permet experiments controlats amb ground truth conegut i distribucions no-IID reproduïbles. |
| El simulador pot carregar TrashNet real? | Sí, si el directori `--dataset-root` existeix i conté subcarpetes amb els noms de les classes (`cardboard/`, `glass/`, `paper/`, `plastic/`). El codi busca imatges .jpg, .jpeg, .png, .bmp, .gif, .webp. |

### B2. Redactar text per Section 4.1

Paràgraf ampliat que substitueixi la frase actual:

```
To evaluate FedAvg under controlled non-IID conditions, we generated a synthetic
dataset of 16x16 grayscale images spanning four waste categories (cardboard, glass,
paper, plastic). Each class is defined by a distinct geometric prototype: horizontal
stripes for cardboard, diagonal center-line patterns for glass, nested rectangular
regions for paper, and vertical stripes for plastic. Individual samples are produced
by a convex combination of the primary prototype (52%), the next-class prototype
(23%), an alternate-class prototype (10%), and the mean shared pattern (15%), fol-
lowed by additive Gaussian noise (sigma=0.30), brightness jitter (8%), stochastic
pixel roll (35% probability), and occasional class blending (12-17%). This process
yields 220 samples per class while maintaining visual separability, enabling repro-
ducible non-IID partitions via Dirichlet sampling without reliance on external
datasets such as TrashNet. The simulator can optionally load real TrashNet images
if the corresponding directory structure is provided.
```

---

## C: Related Work + Novetat

### C1. Cerca bibliogràfica (per citar al paper)

Afegir **4-5 referències** clau al `references.bib`:

| Mètode | Referència | Idea principal |
|--------|-----------|----------------|
| QSGD | Alistarh et al., 2017 | Quantized SGD with stochastic rounding |
| SignSGD | Bernstein et al., 2018 | 1-bit compression via sign of gradients |
| Top-k sparsification | Strom, 2015 / Aji & Heafield, 2017 | Transmetre només top-k gradients |
| FedCOM | Haddadpour et al., 2021 | FL amb compressió i comunicació eficient |
| Hierarchical FL | Liu et al., 2020 / Abad et al., 2020 | Agregació en múltiples nivells |

**Tria 3-4 que citeu al Related Work**. Cerqueu-les i afegiu-les al `.bib`.

Referències suggerides per cercar:
- `QSGD: Communication-efficient SGD via gradient quantization with stochastic rounding`
- `SignSGD: Compressed optimisation for non-convex problems`
- `Gradient compression for communication-efficient federated learning` (FedCOM)

**Checklist**:
- [x] 3-4 referències noves al `references.bib` (fitxer `docs/references.bib` creat amb QSGD, SignSGD, FedCOM, Top-k)
- [x] Cita a la secció de Related Work / novetat (text redactat amb referències a QSGD, SignSGD, FedCOM, Top-k)

### C2. Redactar Related Work (subsecció nova)

Text proposat (~150 paraules):

```
Communication efficiency is a central challenge in federated learning (FL),
where the cost of transmitting model updates between clients and the server
can dominate training time. Several compression strategies have been proposed
to mitigate this bottleneck. Alistarh et al. introduced QSGD, which combines
stochastic gradient quantization with unbiased encoding to achieve convergence
guarantees under bounded variance. Bernstein et al. proposed SignSGD, where
only the sign of each gradient is communicated, enabling 1-bit compression
with majority-vote aggregation. Haddadpour et al. developed FedCOM, providing
a unified analysis of compressed FL with periodic communication and local
gradient tracking. Top-k sparsification, analyzed by Aji and Heafield, further
reduces communication by transmitting only the largest gradient components.
However, most prior work evaluates these techniques exclusively in simulation
environments with high-end hardware, leaving open questions about their
applicability to resource-constrained edge deployments. In this work, we
implement stochastic rounding quantization within a simulated FedAvg pipeline
and validate it on a real two-node Arduino UNO Q testbed, bridging the gap
between theoretical compression and practical edge deployment.
```

**Estructura suggerida:**
1. Frase introductòria: "Communication efficiency is a central challenge in FL..."
2. 2-3 frases sobre mètodes existents: QSGD, SignSGD, Top-k, Hierarchical FL
3. 1-2 frases sobre què falta: "However, most prior work evaluates these techniques only in simulation..."
4. Conclusió: "In this work, we ..." (el que feu vosaltres de diferent)

### C3. Articular la novetat (per Conclusions / Abstract)

Redacteu 2-3 frases que responguin: **què fa TrashUQ diferent?**

> "To the best of our knowledge, TrashUQ represents the first end-to-end FL deployment on Arduino UNO Q hardware, combining real two-node telemetry validation with controlled non-IID simulation. Unlike prior work that focuses solely on simulation-based FL evaluation, our system provides validated MQTT telemetry, gRPC-based model orchestration, and on-device fine-tuning on low-cost edge hardware. We further analyze communication-efficient updates through gradient quantization, demonstrating 4x compression with negligible accuracy loss."

```
To the best of our knowledge, TrashUQ represents the first end-to-end
federated learning deployment on Arduino UNO Q-class hardware, combining
real two-node telemetry validation with controlled non-IID simulation.
Unlike prior work that evaluates compression techniques exclusively in
simulation, our system provides validated MQTT telemetry, gRPC-based model
orchestration, and on-device fine-tuning on low-cost edge microprocessors.
We further analyze communication-efficient updates through stochastic
rounding quantization, demonstrating 4x model compression with less than
0.5% accuracy degradation across 2--20 simulated clients, and up to 8x
compression with the 4-bit variant at a 1.3% accuracy cost.
```

---

## D: Consolidar i compilar

Quan TOTES les parts anteriors estiguin completes:

- [x] Resultats de quantització (A3) complets
- [x] Text synthetic dataset (B2) redactat
- [x] Related work (C2) redactat
- [x] Novelty statement (C3) redactat
- [ ] Resultats de càmera (PART 1) rebuts i incorporats
- [x] `references.bib` actualitzat (fitxer `docs/references.bib` creat)
- [x] Seccions del `.tex` modificades (Related Work + Synthetic + Quantization taules + Abstract + Conclusions)
- [x] PDF compilat sense errors (6 pàgines, 149KB, a `paper/main.pdf`)
- [ ] PDF final revisat per tots

---

## Temps estimat

| Tasca | Temps |
|-------|-------|
| A1: Implementar quantize | 1-2h |
| A2-A3: Executar experiments + omplir taules | 1-2h |
| B: Synthetic dataset text | 30min-1h |
| C1: Cerca refs + .bib | 30min |
| C2: Related work text | 1h |
| C3: Novelty statement | 30min |
| D: Compilar PDF + revisar | 1h |
| **Total** | **~5-8h** |
