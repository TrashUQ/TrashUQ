"""HTTP server for iPad-based trash labeling UI."""
import logging
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <title>TrashNet</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #0f0f0f;
      color: #fff;
      font-family: -apple-system, system-ui, sans-serif;
      height: 100dvh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    #image-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px 20px 0;
      min-height: 0;
    }
    #trash-img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    }
    #hint {
      padding: 10px 20px;
      font-size: 13px;
      color: #666;
      text-align: center;
      letter-spacing: 0.3px;
    }
    #waiting {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 20px;
      color: #444;
    }
    #waiting-icon {
      width: 72px;
      height: 72px;
      border: 2px solid #333;
      border-top-color: #555;
      border-radius: 50%;
      animation: spin 1.4s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    #waiting-text { font-size: 16px; }
    #buttons {
      display: flex;
      gap: 10px;
      padding: 16px;
      background: #171717;
      border-top: 1px solid #222;
      flex-shrink: 0;
    }
    .btn {
      flex: 1;
      border: none;
      border-radius: 18px;
      padding: 0;
      height: 96px;
      font-size: 17px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.1s, filter 0.1s;
      letter-spacing: 0.4px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }
    .btn-icon { font-size: 28px; }
    .btn:active { transform: scale(0.95); filter: brightness(0.85); }
    .btn:disabled { opacity: 0.3; cursor: not-allowed; }
    .btn:disabled:active { transform: none; filter: none; }
    .btn-paper  { background: #2563eb; color: #fff; }
    .btn-carton { background: #d97706; color: #fff; }
    .btn-glass  { background: #059669; color: #fff; }
    #flash {
      position: fixed;
      inset: 0;
      background: rgba(255,255,255,0.35);
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.35s;
    }
  </style>
</head>
<body>
  <div id="flash"></div>

  <div id="waiting">
    <div id="waiting-icon"></div>
    <span id="waiting-text">Waiting for unrecognized item&hellip;</span>
  </div>

  <div id="image-section" style="display:none">
    <img id="trash-img" src="" alt="Trash item">
  </div>
  <div id="hint" style="display:none"></div>

  <div id="buttons">
    <button class="btn btn-paper"  onclick="submitLabel('paper')"  disabled>
      <span class="btn-icon">📄</span>Paper
    </button>
    <button class="btn btn-carton" onclick="submitLabel('carton')" disabled>
      <span class="btn-icon">📦</span>Carton
    </button>
    <button class="btn btn-glass"  onclick="submitLabel('glass')"  disabled>
      <span class="btn-icon">🫙</span>Glass
    </button>
  </div>

  <script>
    let currentId = null;
    let pollTimer = null;

    function setButtons(enabled) {
      document.querySelectorAll('.btn').forEach(b => b.disabled = !enabled);
    }

    function showWaiting() {
      document.getElementById('image-section').style.display = 'none';
      document.getElementById('hint').style.display = 'none';
      document.getElementById('waiting').style.display = 'flex';
      setButtons(false);
    }

    function showItem(data) {
      document.getElementById('waiting').style.display = 'none';
      document.getElementById('trash-img').src = '/api/image/' + data.id + '?t=' + Date.now();
      document.getElementById('image-section').style.display = 'flex';
      const pct = (data.confidence * 100).toFixed(0);
      document.getElementById('hint').textContent =
        'Model guess: ' + data.model_guess + ' — ' + pct + '% confidence';
      document.getElementById('hint').style.display = 'block';
      setButtons(true);
    }

    async function poll() {
      try {
        const r = await fetch('/api/pending');
        const data = await r.json();
        if (data.pending) {
          if (data.id !== currentId) {
            currentId = data.id;
            showItem(data);
          }
        } else {
          if (currentId !== null) {
            currentId = null;
            showWaiting();
          }
        }
      } catch (_) {}
      pollTimer = setTimeout(poll, 2000);
    }

    async function submitLabel(label) {
      if (!currentId) return;
      clearTimeout(pollTimer);
      setButtons(false);

      const flash = document.getElementById('flash');
      flash.style.opacity = '1';
      setTimeout(() => { flash.style.opacity = '0'; }, 350);

      try {
        await fetch('/api/label', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: currentId, label }),
        });
      } catch (_) {}

      currentId = null;
      showWaiting();
      pollTimer = setTimeout(poll, 600);
    }

    poll();
  </script>
</body>
</html>"""


class _LabelRequest(BaseModel):
    id: str
    label: str


def create_app(
    get_pending: Callable[[], dict | None],
    submit_label: Callable[[str, str], None],
    valid_labels: list[str],
) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(_HTML)

    @app.get("/api/pending")
    def api_pending() -> JSONResponse:
        item = get_pending()
        if item is None:
            return JSONResponse({"pending": False})
        return JSONResponse({
            "pending": True,
            "id": item["id"],
            "model_guess": item["model_guess"],
            "confidence": item["confidence"],
        })

    @app.get("/api/image/{sample_id}")
    def api_image(sample_id: str) -> FileResponse:
        item = get_pending()
        if item is None or item["id"] != sample_id:
            raise HTTPException(status_code=404)
        path = Path(item["image_path"])
        if not path.exists():
            raise HTTPException(status_code=404)
        return FileResponse(str(path), media_type="image/jpeg")

    @app.post("/api/label")
    def api_label(req: _LabelRequest) -> dict:
        if req.label not in valid_labels:
            raise HTTPException(status_code=400, detail=f"invalid label, must be one of {valid_labels}")
        submit_label(req.id, req.label)
        return {"ok": True}

    return app
