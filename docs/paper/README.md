# TrashUQ Technical Paper

This folder contains the final English technical report, diagram sources, the Universitat de Lleida logo asset, and the PDF export helper.

## Final Deliverables

- `TrashUQ_Technical_Report.md`: final English Markdown report.
- `TrashUQ_Technical_Report.pdf`: final exported PDF.
- `assets/*.mmd`: Mermaid diagram sources.
- `assets/udl_logo.svg`: local SVG copy of the Universitat de Lleida logo.
- `assets/udl_logo.png`: PNG rendered from the SVG for stable PDF output.
- `export_pdf.sh`: resilient PDF export script.

## Read The Paper

```sh
cd ~/Documents/TrashNet/TrashUQ
less docs/paper/TrashUQ_Technical_Report.md
```

Or open it in a Markdown viewer with Mermaid support.

## Export PDF

```sh
cd ~/Documents/TrashNet/TrashUQ
bash docs/paper/export_pdf.sh
```

The script tries:

- `pandoc` with `xelatex`, then `lualatex`, then the default PDF engine.
- `npx md-to-pdf` if pandoc export is unavailable.

If neither tool works, it prints manual export instructions.

## Optional Diagram SVG Generation

If Mermaid CLI is installed:

```sh
cd ~/Documents/TrashNet/TrashUQ
mmdc -i docs/paper/assets/architecture.mmd -o docs/paper/assets/architecture.svg
mmdc -i docs/paper/assets/mqtt_flow.mmd -o docs/paper/assets/mqtt_flow.svg
mmdc -i docs/paper/assets/grpc_fl_sequence.mmd -o docs/paper/assets/grpc_fl_sequence.svg
mmdc -i docs/paper/assets/deployment_topology.mmd -o docs/paper/assets/deployment_topology.svg
mmdc -i docs/paper/assets/dashboard_data_flow.mmd -o docs/paper/assets/dashboard_data_flow.svg
```

## Logo Source

The cover uses `File:Logo Universitat de Lleida.svg` from Wikimedia Commons. The file page identifies `www.udl.cat` as the source and describes the asset as a public-domain text/logo. The local copies are stored in `docs/paper/assets/udl_logo.svg` and `docs/paper/assets/udl_logo.png`.
