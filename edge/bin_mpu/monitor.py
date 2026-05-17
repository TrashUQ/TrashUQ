"""
Real-time monitoring web UI for testing the trash classifier.

Endpoints:
  GET  /monitor          → HTML dashboard
  GET  /monitor/stream   → MJPEG camera feed
  WS   /monitor/ws       → real-time detection events (JSON)
  POST /monitor/trigger  → simulate PIR trigger (testing without sensor)
"""
import asyncio
import logging
from collections.abc import AsyncGenerator

import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrashNet Monitor</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0d0d0d; --surface: #161616; --border: #252525;
    --text: #e8e8e8; --muted: #555;
    --cardboard: #f59e0b; --glass: #06b6d4;
    --paper: #6366f1; --plastic: #22c55e;
    --idle: #555; --capturing: #facc15; --waiting: #f97316;
  }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif;
         display: grid; grid-template-rows: 48px 1fr 56px; height: 100dvh; overflow: hidden; }

  /* Header */
  header { display: flex; align-items: center; gap: 12px; padding: 0 20px;
            border-bottom: 1px solid var(--border); background: var(--surface); }
  header h1 { font-size: 15px; font-weight: 600; letter-spacing: 0.5px; }
  #state-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 99px;
                 letter-spacing: 1px; text-transform: uppercase;
                 background: var(--idle); color: #000; transition: background 0.3s; }
  #state-badge.capturing { background: var(--capturing); }
  #state-badge.waiting_label { background: var(--waiting); }

  /* Main grid */
  main { display: grid; grid-template-columns: 1fr 320px; overflow: hidden; }

  /* Camera */
  #cam-wrap { position: relative; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden; }
  #cam { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
  #cam-overlay { position: absolute; inset: 0; pointer-events: none; }

  /* Sidebar */
  aside { background: var(--surface); border-left: 1px solid var(--border);
          display: flex; flex-direction: column; overflow: hidden; }

  /* Result card */
  #result-card { padding: 20px; border-bottom: 1px solid var(--border); }
  #result-label { font-size: 32px; font-weight: 800; letter-spacing: 1px; min-height: 40px;
                  text-transform: uppercase; }
  #result-conf { font-size: 13px; color: var(--muted); margin-top: 4px; min-height: 18px; }

  /* Votes */
  #votes { display: flex; gap: 6px; margin-top: 14px; }
  .vote-dot { width: 22px; height: 22px; border-radius: 50%; border: 2px solid var(--border);
              transition: background 0.2s, border-color 0.2s; }
  .vote-dot.filled { border-color: transparent; }

  /* Confidence bars */
  #bars { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; }
  .bar-row { display: flex; flex-direction: column; gap: 4px; }
  .bar-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
  .bar-track { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; width: 0%; transition: width 0.3s; }
  .bar-cardboard .bar-fill { background: var(--cardboard); }
  .bar-glass    .bar-fill { background: var(--glass); }
  .bar-paper    .bar-fill { background: var(--paper); }
  .bar-plastic  .bar-fill { background: var(--plastic); }

  /* Log */
  #log-wrap { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 6px; }
  .log-entry { font-size: 12px; padding: 8px 10px; border-radius: 8px; background: var(--border);
               border-left: 3px solid var(--muted); }
  .log-entry.result { border-left-color: var(--capturing); }
  .log-time { color: var(--muted); font-size: 10px; }

  /* Footer */
  footer { display: flex; align-items: center; justify-content: center; gap: 12px;
            border-top: 1px solid var(--border); background: var(--surface); padding: 0 20px; }
  #btn-trigger { background: #facc15; color: #000; border: none; border-radius: 8px;
                 padding: 0 28px; height: 36px; font-size: 13px; font-weight: 700;
                 cursor: pointer; transition: filter 0.15s; }
  #btn-trigger:hover { filter: brightness(1.1); }
  #btn-trigger:active { filter: brightness(0.85); }
  #btn-trigger:disabled { opacity: 0.35; cursor: not-allowed; }
  #conn-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); transition: background 0.3s; }
  #conn-dot.connected { background: #22c55e; }
  #conn-label { font-size: 12px; color: var(--muted); }
</style>
</head>
<body>

<header>
  <h1>TrashNet Monitor</h1>
  <span id="state-badge">idle</span>
</header>

<main>
  <div id="cam-wrap">
    <img id="cam" src="/monitor/stream" alt="Camera feed">
  </div>

  <aside>
    <div id="result-card">
      <div id="result-label" style="color:var(--muted)">—</div>
      <div id="result-conf"></div>
      <div id="votes">
        <div class="vote-dot" id="v0"></div>
        <div class="vote-dot" id="v1"></div>
        <div class="vote-dot" id="v2"></div>
        <div class="vote-dot" id="v3"></div>
        <div class="vote-dot" id="v4"></div>
      </div>
    </div>

    <div id="bars">
      <div class="bar-row bar-cardboard">
        <div class="bar-label">Cardboard</div>
        <div class="bar-track"><div class="bar-fill" id="bar-cardboard"></div></div>
      </div>
      <div class="bar-row bar-glass">
        <div class="bar-label">Glass</div>
        <div class="bar-track"><div class="bar-fill" id="bar-glass"></div></div>
      </div>
      <div class="bar-row bar-paper">
        <div class="bar-label">Paper</div>
        <div class="bar-track"><div class="bar-fill" id="bar-paper"></div></div>
      </div>
      <div class="bar-row bar-plastic">
        <div class="bar-label">Plastic</div>
        <div class="bar-track"><div class="bar-fill" id="bar-plastic"></div></div>
      </div>
    </div>

    <div id="log-wrap"></div>
  </aside>
</main>

<footer>
  <div id="conn-dot"></div>
  <span id="conn-label">disconnected</span>
  <button id="btn-trigger" onclick="trigger()">⚡ Trigger</button>
</footer>

<script>
const CLASS_COLORS = {
  cardboard: 'var(--cardboard)', glass: 'var(--glass)',
  paper: 'var(--paper)', plastic: 'var(--plastic)'
};
const VOTE_COLORS = { cardboard: '#f59e0b', glass: '#06b6d4', paper: '#6366f1', plastic: '#22c55e' };

let ws, reconnectTimer;

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/monitor/ws`);

  ws.onopen = () => {
    document.getElementById('conn-dot').className = 'connected';
    document.getElementById('conn-label').textContent = 'connected';
    clearTimeout(reconnectTimer);
  };

  ws.onclose = () => {
    document.getElementById('conn-dot').className = '';
    document.getElementById('conn-label').textContent = 'reconnecting…';
    reconnectTimer = setTimeout(connect, 2000);
  };

  ws.onmessage = (e) => handleEvent(JSON.parse(e.data));
}

function handleEvent(ev) {
  if (ev.type === 'state') {
    const badge = document.getElementById('state-badge');
    badge.textContent = ev.state.toLowerCase().replace('_', ' ');
    badge.className = ev.state.toLowerCase();
    if (ev.state === 'CAPTURING') resetVotes();
  }

  if (ev.type === 'vote') {
    const dot = document.getElementById('v' + (ev.n - 1));
    if (dot) {
      dot.style.background = VOTE_COLORS[ev.label] || '#fff';
      dot.classList.add('filled');
    }
    // Update bars with latest frame confidences
    if (ev.probs) {
      for (const [cls, conf] of Object.entries(ev.probs)) {
        const bar = document.getElementById('bar-' + cls);
        if (bar) bar.style.width = (conf * 100).toFixed(1) + '%';
      }
    }
    addLog(`Frame ${ev.n}/5 → ${ev.label} (${(ev.confidence * 100).toFixed(0)}%)`);
  }

  if (ev.type === 'result') {
    const lbl = document.getElementById('result-label');
    lbl.textContent = ev.label.toUpperCase();
    lbl.style.color = CLASS_COLORS[ev.label] || 'var(--text)';
    document.getElementById('result-conf').textContent =
      `${(ev.confidence * 100).toFixed(1)}% confidence · votes: ${JSON.stringify(ev.votes)}`;
    addLog(`RESULT: ${ev.label.toUpperCase()} — ${(ev.confidence*100).toFixed(0)}%`, true);
  }
}

function resetVotes() {
  for (let i = 0; i < 5; i++) {
    const d = document.getElementById('v' + i);
    d.style.background = '';
    d.classList.remove('filled');
  }
  ['cardboard','glass','paper','plastic'].forEach(c => {
    const b = document.getElementById('bar-' + c);
    if (b) b.style.width = '0%';
  });
}

function addLog(msg, isResult = false) {
  const wrap = document.getElementById('log-wrap');
  const now = new Date().toLocaleTimeString();
  const el = document.createElement('div');
  el.className = 'log-entry' + (isResult ? ' result' : '');
  el.innerHTML = `<span class="log-time">${now}</span>  ${msg}`;
  wrap.prepend(el);
  // Keep last 50 entries
  while (wrap.children.length > 50) wrap.removeChild(wrap.lastChild);
}

async function trigger() {
  const btn = document.getElementById('btn-trigger');
  btn.disabled = true;
  await fetch('/monitor/trigger', { method: 'POST' }).catch(() => {});
  setTimeout(() => { btn.disabled = false; }, 2000);
}

connect();
</script>
</body>
</html>"""


class MonitorBroadcaster:
    """Thread-safe event broadcaster for WebSocket clients."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register(self, q: asyncio.Queue) -> None:
        self._queues.append(q)

    def unregister(self, q: asyncio.Queue) -> None:
        self._queues.remove(q)

    def emit(self, event: dict) -> None:
        """Call from any thread."""
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(self._emit_sync, event)

    def _emit_sync(self, event: dict) -> None:
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


broadcaster = MonitorBroadcaster()
_latest_frame: bytes | None = None
_trigger_callback = None


def set_trigger_callback(fn) -> None:
    global _trigger_callback
    _trigger_callback = fn


def push_frame(frame_bgr) -> None:
    global _latest_frame
    ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if ok:
        _latest_frame = buf.tobytes()


def create_router() -> APIRouter:
    router = APIRouter(prefix="/monitor")

    @router.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(_HTML)

    @router.get("/stream")
    def stream() -> StreamingResponse:
        return StreamingResponse(
            _mjpeg_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @router.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        broadcaster.set_loop(asyncio.get_event_loop())
        q: asyncio.Queue = asyncio.Queue(maxsize=32)
        broadcaster.register(q)
        try:
            while True:
                event = await q.get()
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass
        finally:
            broadcaster.unregister(q)

    @router.post("/trigger")
    def trigger() -> JSONResponse:
        if _trigger_callback:
            import threading
            threading.Thread(target=_trigger_callback, daemon=True).start()
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "reason": "no trigger callback set"}, status_code=503)

    return router


async def _mjpeg_generator() -> AsyncGenerator[bytes, None]:
    import asyncio
    while True:
        frame = _latest_frame
        if frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        await asyncio.sleep(0.05)  # ~20 fps
