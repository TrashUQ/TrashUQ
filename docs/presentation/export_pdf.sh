#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$DIR/TrashUQ-final-presentation.pdf"
URL="file://$DIR/index.html"

if command -v chromium-browser >/dev/null 2>&1; then
  CHROME="chromium-browser"
elif command -v chromium >/dev/null 2>&1; then
  CHROME="chromium"
elif command -v google-chrome >/dev/null 2>&1; then
  CHROME="google-chrome"
elif command -v google-chrome-stable >/dev/null 2>&1; then
  CHROME="google-chrome-stable"
else
  echo "Chrome/Chromium not found. Open index.html and print to PDF from the browser." >&2
  exit 1
fi

"$CHROME" \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="$OUT" \
  --print-to-pdf-no-header \
  "$URL"

echo "$OUT"
