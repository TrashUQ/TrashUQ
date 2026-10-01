# TrashUQ — two-minute presentation

Three slides using the standard LaTeX Beamer Madrid theme. `main.pdf` is ready to present. Build from this directory:

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The diagram and chart are editable TikZ vectors. `qr.tex` reproduces the poster QR. No external images are required.

## Speaking script — approximately 100–115 seconds

### Slide 1 — 15 seconds

“Hello, we are presenting TrashUQ, a project that combines waste classification on Arduino devices with federated learning. We focused on how these devices can learn together and how to reduce the communication needed to do that.”

### Slide 2 — 75–85 seconds

“Each Arduino classifies waste locally. When a user corrects a prediction, the device can use that correction to improve its model. Instead of sending its images to a server, it sends a model update.

The server combines updates from the devices using federated averaging, or FedAvg, and sends the improved shared model back. This cycle allows the devices to learn together while keeping images local.

We also compared different ways to compress the updates. Stochastic rounding, or SR, represents model values using fewer bits. Top-k sparsification sends only selected values.

Among the methods we tested, four-bit stochastic rounding gave the best communication savings while preserving accuracy. The graph shows communication falling from about 3.92 to 2.21 megabytes compared with the uncompressed baseline. That is roughly forty-four percent less traffic, with no loss of accuracy in our synthetic-data simulation. More aggressive sparsification could save slightly more traffic, but reduced accuracy.”

### Slide 3 — 10 seconds

“Thank you for listening. Do you have any questions? You can scan the QR code to explore our project.”

## Evidence and scope

- Learning cycle: `../poster/main.tex` and `../paper/sections/02_architecture.tex`.
- Compression comparison: `../paper/sections/04_fl_simulation.tex`, table `tab:comparison`. FP32: 3.922 MB; SR-4bit: 2.210 MB; both 93.75% accuracy. Savings: 43.65%, rounded to 44%.
- SR 4-bit is the best tested trade-off for reducing traffic while preserving baseline accuracy, not the smallest payload at any accuracy.
- Results are means across three seeds, with synthetic data, 20 clients and 25 rounds. They do not establish real-world waste classification accuracy.
- QR destination: https://trashuq.vercel.app. The address is intentionally not printed on the slide.
