# Synthetic Dataset Clarification + Conclusions - Workbook

Ompliu aquest fitxer mentre analitzeu el codi i redacteu les explicacions.
Quan estigui complet, en traiem el text definitiu per al paper.

---

## 1. Responsable

**Executor**: _________________________

**Data**: _________________________

---

## 2. Anàlisi del Synthetic Dataset

Llegiu `experiments/part_b/run_part_b.py`, funcions:
- `make_synthetic_prototypes()` (línia 216)
- `generate_synthetic_dataset()` (línia 244)
- `maybe_load_real_dataset()` (línia 284)
- `load_dataset_bundle()` (línia 358)

### 2a. Per què es va fer servir synthetic?

Raó real (context del repositori):

El dataset TrashNet original no està disponible a la ruta `--dataset-root` del simulador. El codi de `load_dataset_bundle()` intenta carregar TrashNet real primer; si no troba els directoris de classes, cau automàticament al generador sintètic (`generate_synthetic_dataset()`). Això permet que qualsevol persona pugui executar els experiments sense necessitat de descarregar i preprocessar TrashNet.

### 2b. Descripció del dataset

Ompliu aquesta taula:

| Propietat | Valor |
|-----------|-------|
| Classes | cardboard, glass, paper, plastic |
| Samples/class | 220 (configurable via `--synthetic-samples-per-class`) |
| Mida imatge | 16 x 16 píxels |
| Canal | 1 (escala de grisos) |
| Tipus de patró | cardboard = franges horitzontals; glass = línies diagonals centrals; paper = rectangle central amb densitats diferents; plastic = franges verticals |
| Sorra afegida | Gaussiana (std=0.30) |
| Augmentacions | Variació de brillantor (8%), desplazament aleatori (35%), barreja entre classes (12% veí, 5% alterna), combinació lineal dels prototips (52% classe principal + 23% següent + 10% alterna + 15% patró compartit) |
| Seed de generació | 42 (defecte) |
| Total samples train (80%) | 704 (176 per classe) |
| Total samples test (20%) | 176 (44 per classe) |

### 2c. Limitacions del synthetic dataset (respecte a TrashNet real)

1. Les imatges sintètiques (16x16, grises) no capturen la variabilitat visual del món real (il·luminació, textures, perspectives).
2. Les distribucions no-IID es generen artificialment via Dirichlet, no reflecteixen patrons de deixalles reals per ubicació.
3. No hi ha sorra de sensor real (compression JPEG, sorra CCD, etc.).
4. L'accuracy absoluta obtinguda (~93%) pot no ser representativa del rendiment en dades reals.

### 2d. Per què és suficient per validar FL convergence?

L'objectiu dels experiments no és mesurar l'accuracy en el món real, sinó **validar que l'algorisme FedAvg convergeix sota condicions no-IID controlades i reproduïbles**. El dataset sintètic permet:
- **Ground truth conegut**: sabem exactament quines classes i distribucions hi ha.
- **Reproducibilitat**: qualsevol pot generar el mateix dataset amb la mateixa seed.
- **Control de no-IID**: el paràmetre alpha de Dirichlet permet variar el grau d'heterogeneïtat.
- **Aïllament de variables**: separem l'avaluació de l'algorisme de la complexitat del domini visual.

---

## 3. Redacció - Text ampliat per Section 4.1

> **Actual (al paper)**:
> _"The dataset used in this campaign was a documented synthetic TrashNet-style fallback (4 classes, 220 samples per class) because a local real TrashNet corpus was unavailable at execution time."_

**Text proposat** (~150-200 paraules):
_incloure: per què synthetic, com es genera, limitacions, per què és suficient per l'objectiu_

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
if the corresponding directory structure is provided. While synthetic data cannot
replace real-world visual diversity, it provides known ground truth and controlled
heterogeneity for validating FL convergence behavior.
```

---

## 4. Conclusions generals - input per al paper

Un cop l'altre membre de l'equip hagi completat el quantization workbook:

### 4a. Main findings (resum 3-5 bullets)

- FedAvg amb 8-bit stochastic rounding quantization manté accuracy idèntica al baseline float32 (93.75%) amb compressió 4x dels pesos.
- La quantització 4-bit amb packing uint8 ofereix compressió 8x amb una degradació màxima d'1.33% (a 2 clients), que es redueix a 0% en augmentar el nombre de clients.
- El dataset sintètic de 16x16 proporciona un entorn controlat i reproduïble per validar la convergència de FL sota particions no-IID.
- La combinació de quantització + FedAvg és efectiva en entorns amb recursos limitats sense comprometre la qualitat del model.

### 4b. Canvis a la Conclusions section

**Current** (al paper):
> _"The key takeaway is that FL is feasible on this embedded stack, while communication overhead is the main scaling bottleneck. Code is available at...; future work will focus on camera-in-the-loop latency and communication-efficient FL updates."_

**Proposed update** (afegir quantization finding, actualitzar future work):

```
The key takeaway is that FL is feasible on this embedded stack, while
communication overhead is the main scaling bottleneck. We further demonstrate
that stochastic rounding quantization provides up to 4--8x model compression
with negligible accuracy loss (0--1.33%), effectively mitigating the communication
bottleneck. Code is available at...; future work will focus on camera-in-the-loop
latency validation and deployment of quantized models on Arduino UNO Q hardware.
```

### 4c. Actualització de l'Abstract (si cal)

**Current**:
> _"Results indicate that FL orchestration is feasible on this embedded stack, while communication growth is the main scaling cost."_

**Proposed update**:

```
Results indicate that FL orchestration is feasible on this embedded stack, while
communication growth is the main scaling cost. We show that stochastic rounding
quantization reduces communication by 4--8x with negligible accuracy degradation,
enabling efficient FL on resource-constrained edge hardware.
```

---

## 5. Checklist final (abans de donar per tancat)

- [x] `make_synthetic_prototypes()` entès i documentat al workbook
- [x] Synthetic section 4.1 ampliada amb explicació completa
- [x] Conclusions actualitzades amb els resultats de quantització
- [x] Abstract actualitzat (si escau)
- [x] Introduction actualitzada (si escau)
- [x] Referències actualitzades (si cal, per quantization)
- [ ] PDF compilat i revisat
