# TrashUQ Technical Paper

This folder contains the project technical report and diagram sources.

## Files

- `TrashUQ_Technical_Report.md`: main Spanish technical paper.
- `assets/*.mmd`: Mermaid diagram sources.
- `export_pdf.sh`: optional PDF export helper.

## Read The Paper

From the fullstack repository:

```sh
cd ~/Documents/TrashNet/TrashUQ
less docs/paper/TrashUQ_Technical_Report.md
```

Or open it in any Markdown viewer that supports Mermaid diagrams.

## Export PDF

```sh
cd ~/Documents/TrashNet/TrashUQ
bash docs/paper/export_pdf.sh
```

The script tries:

- `pandoc` with table of contents and numbered sections.
- `npx md-to-pdf` if available.

If neither tool is installed, the script prints manual export instructions.

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
