"""Minimal ASGI adapter for BackendApiApp.

The adapter avoids a runtime web-framework dependency while giving the project
a real ASGI-shaped boundary for future FastAPI/Starlette/Uvicorn integration.
It delegates all route behavior to BackendApiApp.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from backend.app import BackendApiApp, BackendAppResponse


ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]

DEFAULT_MAX_BODY_BYTES = 1024 * 1024


class BackendAsgiApp:
    def __init__(
        self,
        *,
        backend_app: BackendApiApp | None = None,
        store_path: Path | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        self.backend_app = backend_app or BackendApiApp(store_path=store_path)
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend) -> None:
        scope_type = str(scope.get("type") or "")
        if scope_type == "lifespan":
            await self._handle_lifespan(receive, send)
            return
        if scope_type != "http":
            await self._send_response(
                send,
                self.backend_app.handle("GET", "/api/missing"),
                override_status=404,
            )
            return

        method = str(scope.get("method") or "GET").upper()
        path = _scope_path_with_query(scope)
        headers = _scope_headers(scope)
        body_payload: dict[str, Any] | None = {}
        if method in {"POST", "PUT", "PATCH"}:
            raw_body = await _read_body(receive, max_body_bytes=self.max_body_bytes)
            if raw_body is None:
                await self._send_response(send, self.backend_app.invalid_json_response())
                return
            if raw_body:
                body_payload = _decode_json_object(raw_body)
                if body_payload is None:
                    await self._send_response(send, self.backend_app.invalid_json_response())
                    return

        response = self.backend_app.handle(method, path, body=body_payload, headers=headers)
        await self._send_response(send, response)

    async def _handle_lifespan(self, receive: ASGIReceive, send: ASGISend) -> None:
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message_type == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def _send_response(
        self,
        send: ASGISend,
        response: BackendAppResponse,
        *,
        override_status: int | None = None,
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": override_status or response.status,
                "headers": [
                    (b"content-type", response.content_type.encode("utf-8")),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": response.body})


def create_asgi_app(
    *,
    store_path: Path | None = None,
    backend_app: BackendApiApp | None = None,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> BackendAsgiApp:
    return BackendAsgiApp(
        backend_app=backend_app,
        store_path=store_path,
        max_body_bytes=max_body_bytes,
    )


app = create_asgi_app()


def _scope_path_with_query(scope: dict[str, Any]) -> str:
    path = str(scope.get("path") or "/")
    raw_query = scope.get("query_string") or b""
    if raw_query:
        query = raw_query.decode("latin-1")
        return f"{path}?{query}"
    return path


def _scope_headers(scope: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw_name, raw_value in scope.get("headers") or []:
        name = raw_name.decode("latin-1")
        value = raw_value.decode("latin-1")
        if name.lower() == "authorization":
            headers["Authorization"] = value
        elif name.lower() == "content-type":
            headers["Content-Type"] = value
    return headers


async def _read_body(receive: ASGIReceive, *, max_body_bytes: int) -> bytes | None:
    body = bytearray()
    while True:
        message = await receive()
        if message.get("type") != "http.request":
            return None
        chunk = message.get("body") or b""
        body.extend(chunk)
        if len(body) > max_body_bytes:
            return None
        if not message.get("more_body", False):
            return bytes(body)


def _decode_json_object(raw_body: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
