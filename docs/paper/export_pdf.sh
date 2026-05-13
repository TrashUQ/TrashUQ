#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INPUT="${SCRIPT_DIR}/TrashUQ_Technical_Report.md"
OUTPUT="${SCRIPT_DIR}/TrashUQ_Technical_Report.pdf"

if [ ! -f "${INPUT}" ]; then
  echo "Input Markdown not found: ${INPUT}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

try_pandoc() {
  local engine="$1"
  local args=( "${INPUT}" -o "${OUTPUT}" --toc --number-sections )
  if [ -n "${engine}" ]; then
    args+=( "--pdf-engine=${engine}" )
  fi
  pandoc "${args[@]}"
}

if command -v pandoc >/dev/null 2>&1; then
  for engine in xelatex lualatex ""; do
    if [ -n "${engine}" ] && ! command -v "${engine}" >/dev/null 2>&1; then
      continue
    fi
    if try_pandoc "${engine}"; then
      echo "PDF exported with pandoc${engine:+ using ${engine}}: ${OUTPUT}"
      exit 0
    fi
    echo "pandoc${engine:+ using ${engine}} failed; trying next exporter..." >&2
  done
fi

if command -v npx >/dev/null 2>&1; then
  if npx --yes md-to-pdf --version >/dev/null 2>&1; then
    npx --yes md-to-pdf "${INPUT}" --dest "${SCRIPT_DIR}"
    echo "PDF exported with md-to-pdf in: ${SCRIPT_DIR}"
    exit 0
  fi
fi

cat <<'MSG'
No PDF export tool was found.

Install one of these tools and rerun:

  pandoc:
    sudo apt-get install pandoc texlive-xetex
    bash docs/paper/export_pdf.sh

  md-to-pdf:
    npm install -g md-to-pdf
    bash docs/paper/export_pdf.sh

Manual fallback:
  Open docs/paper/TrashUQ_Technical_Report.md in a Markdown viewer that supports Mermaid
  and export/print to PDF from the viewer.
MSG
