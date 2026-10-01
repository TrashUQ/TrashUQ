# Presentation readiness

## Before the demo

- Use the current root README commands. The hardware-free demo uses
  `docs/demos/mockups/scripts/mock_mqtt_publisher.py`; it does not need a camera or TensorFlow.
- Keep `backend/.env` local and use credentials matching the existing PostgreSQL
  volume. Compose overrides come from the shell or a root `.env`.
- Use Python 3.11 or 3.12 for edge setup; the MPU interpreter extra targets Python 3.11.
- For real edge FL, set the backend's `FL_MODEL_SIZE=20` and configure both server
  hosts. The default 16-weight coordinator works with the standalone mock clients.
- Rehearse camera/serial access and inference on the actual UNO Q boards. Hardware,
  TensorFlow training/export, and physical lid operation require an on-device check.
- Open `paper/main.pdf` and `poster/main.pdf`, review the poster at print size,
  scan its QR, and confirm the live website, paper, repository, and author links.

## Verified during cleanup

- Both Next.js apps: production builds, TypeScript checks, HTTP responses, and
  all images referenced by the poster landing page. The dashboard backend API
  proxy also passed against the temporary backend.
- Edge: all 12 existing unit/integration tests; CLI help without a model interpreter.
- Backend: startup and schema creation against a disposable PostgreSQL instance;
  actual MQTT ingestion of all six demo message types; two online devices with
  classification labels/confidences; three successful gRPC aggregations.
- In-process API/gRPC checks: health, bootstrap contract, FL state, weighted
  aggregation, invalid client IDs, and stale update rejection.
- Both simulation scripts: short synthetic-data runs with outputs outside the repository.
- Compose configuration, shell syntax, Python syntax, Ruff undefined-name/unused-code
  checks, local documentation links, and lockfile consistency.
- Paper: full LaTeX/BibTeX build with resolved citations; poster: successful A1 build.
  The checked-in PDFs were preserved. The poster preview's QR decodes to the documented URL.
- Public poster website, repository, and paper destinations: HTTP 200 responses.
- Tracked files: no high-confidence secret-pattern matches or credential filenames
  found. This is a heuristic scan, not a guarantee about historical commits.

## Remaining issues

- After compatible npm fixes, each web app still reports two vulnerable packages:
  Next.js (critical) and its bundled PostCSS (high). npm proposes a breaking Next.js
  upgrade. Framework migration was intentionally deferred in this presentation cleanup;
  the repository should not be considered ready for unrestricted production exposure.
- The application remains a research prototype with unauthenticated APIs/gRPC and
  anonymous MQTT. `NEXT_PUBLIC_*` MQTT credentials are visible to browser users and
  must never contain private server credentials.
- Dataset provisioning is incomplete: `edge/.gitmodules` describes historical
  sources, but there are no registered dataset submodules or bundled training datasets.
  Supply datasets separately before using `setup_data.py` or training scripts.
- The paper builds with existing typography, hyperlink-anchor, and bibliography
  warnings. Its first author's affiliation marker is lowercase `a`, while the defined
  affiliation marker is uppercase `A`; review this editorial detail before submission.
  Scientific content and existing PDFs were not changed.
- Full edge Ruff style checks still report existing line-length/import-order findings;
  the correctness checks pass. A broad formatting change was deferred.

## Preserved local and submission material

Generated experiment evidence under `artifacts/`, the exact paper export
`trashuq-paper.zip`, alternate board artwork, template bibliography styles, upstream
TrashNet sources/licenses, and poster preview were retained. Installed dependencies,
built web apps, and local Vercel connection metadata remain ignored and available
for rehearsal. Old local agent continuation state was moved to
`/tmp/trashuq-agent-state-backup-20261001` for recovery; temporary files may be cleared
by the operating system.
