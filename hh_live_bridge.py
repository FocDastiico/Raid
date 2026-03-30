from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "hh_live_feed"
OUTPUT_DIR.mkdir(exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
      body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
      self.send_response(status)
      self.send_header("Content-Type", "application/json; charset=utf-8")
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Access-Control-Allow-Origin", "*")
      self.send_header("Access-Control-Allow-Headers", "Content-Type")
      self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      self.end_headers()
      self.wfile.write(body)

    def do_OPTIONS(self) -> None:
      self._send_json(200, {"ok": True})

    def do_GET(self) -> None:
      if self.path != "/health":
        self._send_json(404, {"ok": False, "error": "Not found"})
        return

      latest_path = OUTPUT_DIR / "latest_snapshot.json"
      latest = None
      if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))

      self._send_json(
        200,
        {
          "ok": True,
          "timestamp": utc_now(),
          "output_dir": str(OUTPUT_DIR),
          "latest": latest,
        },
      )

    def do_POST(self) -> None:
      if self.path != "/snapshot":
        self._send_json(404, {"ok": False, "error": "Not found"})
        return

      content_length = int(self.headers.get("Content-Length", "0"))
      raw_body = self.rfile.read(content_length)
      payload = json.loads(raw_body.decode("utf-8"))

      saved_at = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
      screenshot_data = payload.pop("screenshot", "")
      screenshot_path = None

      if screenshot_data.startswith("data:image/png;base64,"):
        encoded = screenshot_data.split(",", 1)[1]
        screenshot_bytes = base64.b64decode(encoded)
        screenshot_path = OUTPUT_DIR / f"{saved_at}.png"
        screenshot_path.write_bytes(screenshot_bytes)

      payload["savedAt"] = utc_now()
      payload["screenshotPath"] = str(screenshot_path) if screenshot_path else None

      snapshot_path = OUTPUT_DIR / f"{saved_at}.json"
      snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
      (OUTPUT_DIR / "latest_snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
      )

      self._send_json(
        200,
        {
          "ok": True,
          "saved_json": str(snapshot_path),
          "saved_screenshot": str(screenshot_path) if screenshot_path else None,
        },
      )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print(f"[{utc_now()}] HH Live Bridge ouvindo em http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
    finally:
        server.server_close()
