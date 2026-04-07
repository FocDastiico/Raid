from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "hh_live_feed"
OUTPUT_DIR.mkdir(exist_ok=True)
LATEST_AUTH_PATH = OUTPUT_DIR / "latest_auth.json"
HH_BASE_URL = "https://raidoptimiser.hellhades.com"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_latest_auth() -> dict | None:
    if not LATEST_AUTH_PATH.exists():
        return None
    return json.loads(LATEST_AUTH_PATH.read_text(encoding="utf-8"))


def save_latest_auth(payload: dict) -> None:
    LATEST_AUTH_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_access_token() -> str:
    auth = load_latest_auth() or {}
    return str(auth.get("accessToken") or "").strip()


def public_auth_state() -> dict:
    auth = load_latest_auth() or {}
    token = str(auth.get("accessToken") or "").strip()
    return {
        "hasToken": bool(token),
        "capturedAt": auth.get("capturedAt"),
        "sourceUrl": auth.get("sourceUrl"),
        "title": auth.get("title"),
    }


def call_hh_api(path: str, payload: dict) -> dict | list:
    token = get_access_token()
    if not token:
        raise RuntimeError("Access token do HellHades nao encontrado")

    request = Request(
        f"{HH_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HellHades respondeu {error.code}: {raw[:300]}") from error
    except URLError as error:
        raise RuntimeError(f"Falha ao conectar no HellHades: {error}") from error


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
      if self.path == "/health":
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
            "auth": public_auth_state(),
          },
        )
        return

      if self.path == "/hh/auth-status":
        self._send_json(
          200,
          {
            "ok": True,
            "timestamp": utc_now(),
            **public_auth_state(),
          },
        )
        return

      self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
      if self.path == "/hh/team-suggestions":
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        try:
          result = call_hh_api("/api/TeamSuggestion/suggestions", payload)
          self._send_json(200, {"ok": True, "source": "hellhades", "data": result})
        except Exception as error:
          self._send_json(502, {"ok": False, "error": str(error)})
        return

      if self.path == "/hh/team-teams":
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        try:
          result = call_hh_api("/api/TeamSuggestion/teams", payload)
          self._send_json(200, {"ok": True, "source": "hellhades", "data": result})
        except Exception as error:
          self._send_json(502, {"ok": False, "error": str(error)})
        return

      if self.path == "/hh/team-details":
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        try:
          result = call_hh_api("/api/TeamSuggestion/details", payload)
          self._send_json(200, {"ok": True, "source": "hellhades", "data": result})
        except Exception as error:
          self._send_json(502, {"ok": False, "error": str(error)})
        return

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

      hh_auth = payload.get("hhAuth") or {}
      access_token = str(hh_auth.get("accessToken") or "").strip()
      if access_token:
        save_latest_auth(
          {
            "accessToken": access_token,
            "capturedAt": payload["savedAt"],
            "sourceUrl": payload.get("url"),
            "title": payload.get("title"),
          }
        )

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
