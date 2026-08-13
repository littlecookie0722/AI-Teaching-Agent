"""Minimal local HTTP wrapper for the backend mock API.

This server is intended for local demos only. It serves static frontend files
and forwards /api/* requests to backend.mock_api.handle_request.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from backend.app import BackendApiApp, BackendAppResponse
from backend.mock_api import BACKEND_DEFAULT_GRADING_DB_ENV


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def is_loopback_host(host: str) -> bool:
    """Return whether a bind host is loopback-only or localhost."""
    normalized = str(host or "").strip().lower()
    if normalized in {"localhost", "ip6-localhost"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def validate_bind_auth(host: str) -> None:
    """Require an API token before exposing the mock API beyond loopback."""
    if not is_loopback_host(host) and not str(os.environ.get("LAB_BACKEND_API_TOKEN") or "").strip():
        raise ValueError(
            "Refusing to start unauthenticated backend on a non-loopback address. "
            "Set LAB_BACKEND_API_TOKEN or bind to 127.0.0.1."
        )


class MockApiRequestHandler(BaseHTTPRequestHandler):
    server_version = "LabMockHTTP/0.1"

    def _app(self) -> BackendApiApp:
        app = getattr(self.server, "backend_app", None)
        if isinstance(app, BackendApiApp):
            return app
        return BackendApiApp(store_path=None)

    def _send_bytes(self, status: int, content_type: str, content: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_app_response(self, response: BackendAppResponse) -> None:
        self._send_bytes(response.status, response.content_type, response.body)

    def _request_headers(self) -> dict[str, str]:
        return {
            "Authorization": self.headers.get("Authorization") or "",
            "Content-Type": self.headers.get("Content-Type") or "",
        }

    def _read_json_body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def do_GET(self) -> None:
        self._send_app_response(self._app().handle("GET", self.path, headers=self._request_headers()))

    def do_POST(self) -> None:
        body = self._read_json_body()
        if body is None:
            self._send_app_response(self._app().invalid_json_response())
            return
        self._send_app_response(
            self._app().handle("POST", self.path, body=body, headers=self._request_headers())
        )

    def log_message(self, format: str, *args: Any) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)


def build_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    store_path: Path | None = None,
    quiet: bool = False,
) -> ThreadingHTTPServer:
    validate_bind_auth(host)
    server = ThreadingHTTPServer((host, port), MockApiRequestHandler)
    server.store_path = store_path
    server.backend_app = BackendApiApp(store_path=store_path)
    server.quiet = quiet
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local backend mock HTTP server.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--store", type=Path, default=None)
    parser.add_argument("--grading-db", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        validate_bind_auth(args.host)
    except ValueError as exc:
        parser.error(str(exc))

    if args.grading_db is not None:
        os.environ[BACKEND_DEFAULT_GRADING_DB_ENV] = str(args.grading_db)
    server = build_server(host=args.host, port=args.port, store_path=args.store, quiet=args.quiet)
    print(f"Backend Mock HTTP listening on http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
