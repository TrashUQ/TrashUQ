# TrashUQ Final Presentation

Interactive HTML presentation for the final TrashUQ project.

## Open

From the repository root:

```bash
cd TrashUQ/docs/presentation
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

You can also open `index.html` directly in a browser.

## Controls

- `Right Arrow`, `Space`, or `PageDown`: next slide
- `Left Arrow`, `Backspace`, or `PageUp`: previous slide
- `N`: toggle presenter notes
- `F`: fullscreen

## Export To PDF

Run:

```bash
./export_pdf.sh
```

The script uses Chrome/Chromium headless if installed and writes `TrashUQ-final-presentation.pdf` in this directory. If Chrome/Chromium is not available, open the presentation in a browser and print to PDF.

## Assets Included

- `assets/dashboard_overview.png`: real TrashUQ dashboard screenshot
- `assets/architecture.svg`: system architecture diagram copied from the paper assets
- `assets/mqtt_flow.svg`: MQTT flow diagram copied from the paper assets
- `assets/dashboard_data_flow.svg`: dashboard/backend data-flow diagram copied from the paper assets
- `assets/grpc_fl_sequence.svg`: gRPC FL sequence diagram copied from the paper assets
- `assets/deployment_topology.svg`: deployment topology diagram copied from the paper assets
- `assets/part_b_accuracy_vs_rounds.png`: Part B accuracy figure copied from experiment artifacts
- `assets/part_b_comm_cost_vs_clients.png`: Part B communication-cost figure copied from experiment artifacts

Most presentation charts are inline SVG inside `index.html` so they remain crisp in browsers and PDF exports.

## Speaker Split

- Speaker 1: motivation, problem, architecture overview
- Speaker 2: edge devices, MQTT pipeline, backend/database
- Speaker 3: dashboard and Part A real deployment validation
- Speaker 4: FL/gRPC, Part B scalability results, limitations and conclusion
