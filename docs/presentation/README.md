# TrashUQ Presentation

This directory contains the formal academic presentation for the TrashUQ project.

## Files

- `index.html`: The interactive HTML presentation (built with Reveal.js).
- `TrashUQ_presentation.pdf`: The exported PDF version for offline viewing.
- `assets/`: Contains screenshots and visual artifacts.
- `export_pdf.sh`: A script to re-generate the PDF from the HTML.

## How to View

### Interactive HTML
Simply open `index.html` in any modern web browser.
- **Navigation:** Use arrow keys or click the controls in the bottom right.
- **Overview:** Press 'O' to see a slide overview.
- **Search:** Press 'Ctrl + F' to search within the slides.

### PDF Version
Open `TrashUQ_presentation.pdf` with any PDF viewer.

## How to Export PDF Manually

If you need to update the presentation and re-export the PDF:

1. Open `index.html` in Chrome or Edge.
2. Append `?print-pdf` to the URL in the address bar (e.g., `file:///path/to/index.html?print-pdf`).
3. Press `Ctrl + P` (Print).
4. Select **Save as PDF** as the destination.
5. Set **Layout** to **Landscape**.
6. Under **More settings**, ensure **Background graphics** is checked.
7. Click **Save**.

## Design Philosophy

- **Style:** Clean, formal, academic engineering.
- **Color Palette:**
  - Navy (#0f172a): Headers and primary text.
  - Teal (#0f766e): Accents, charts, and progress.
  - Slate (#475569): Subheaders and secondary text.
  - Light Gray (#f8fafc): Background containers.
- **Visuals:** Uses Mermaid.js for architecture diagrams and Chart.js for result visualizations.
- **Content:** Focuses on the edge-to-cloud pipeline, MQTT telemetry, and Federated Learning validation results.
