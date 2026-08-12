"""Shared agent API HTTP adapter for explicit import send/status calls."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


AGENT_API_BASE_URL_ENV = "AGENT_API_BASE_URL"
AGENT_API_TOKEN_ENV = "AGENT_API_TOKEN"


class AgentApiAdapterError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        errors: list[dict[str, str]],
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors
        self.context = context or {}


@dataclass(frozen=True)
class AgentApiRuntimeConfig:
    base_url: str
    token: str
    env: dict[str, Any]


def require_agent_api_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentApiAdapterError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": field, "reason": "缺少参数"}],
        )
    return normalized


def normalize_agent_api_max_retries(value: int | str | None) -> int:
    try:
        max_retries = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise AgentApiAdapterError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "maxRetries", "reason": "必须是整数"}],
        ) from exc
    if max_retries < 0:
        raise AgentApiAdapterError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "maxRetries", "reason": "必须大于等于 0"}],
        )
    return max_retries


def redacted_agent_api_env_summary(base_url: str | None, token: str | None) -> dict[str, Any]:
    return {
        AGENT_API_BASE_URL_ENV: {
            "present": bool(base_url),
            "valueReturned": bool(base_url),
            "value": base_url or None,
        },
        AGENT_API_TOKEN_ENV: {
            "present": bool(token),
            "valueReturned": False,
        },
    }


def build_agent_api_runtime_config(
    *,
    base_url: str | None = None,
    base_url_env: str = AGENT_API_BASE_URL_ENV,
    token_env: str = AGENT_API_TOKEN_ENV,
) -> AgentApiRuntimeConfig:
    configured_base_url = base_url or os.environ.get(base_url_env, "")
    token = os.environ.get(token_env, "")
    return AgentApiRuntimeConfig(
        base_url=configured_base_url,
        token=token,
        env=redacted_agent_api_env_summary(configured_base_url, token),
    )


def build_agent_api_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _extract_response_body(raw: bytes, content_type: str | None) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    parsed: Any = None
    if content_type and "json" in content_type.lower():
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
    return {
        "json": parsed if isinstance(parsed, (dict, list)) else None,
        "textPreview": None if isinstance(parsed, (dict, list)) else text[:1000],
        "bytes": len(raw),
    }


def _response_from_http_error(exc: HTTPError) -> dict[str, Any]:
    raw = exc.read()
    content_type = exc.headers.get("Content-Type") if exc.headers else None
    return {
        "ok": False,
        "statusCode": exc.code,
        "reason": exc.reason,
        "headers": {"keys": sorted(exc.headers.keys()) if exc.headers else []},
        "body": _extract_response_body(raw, content_type),
        "errorType": "HTTPError",
    }


def _send_once(
    *,
    method: str,
    url: str,
    token: str,
    body: dict[str, Any] | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type")
            return {
                "ok": 200 <= response.status < 300,
                "statusCode": response.status,
                "reason": response.reason,
                "headers": {"keys": sorted(response.headers.keys())},
                "body": _extract_response_body(raw, content_type),
                "errorType": None,
            }
    except HTTPError as exc:
        return _response_from_http_error(exc)


def request_agent_api_json(
    *,
    method: str,
    base_url: str,
    path: str,
    token: str,
    body: dict[str, Any] | None = None,
    timeout_seconds: int = 30,
    max_retries: int | str | None = 0,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise AgentApiAdapterError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "timeoutSeconds", "reason": "必须大于 0"}],
        )
    max_retries = normalize_agent_api_max_retries(max_retries)
    method = require_agent_api_text(method, "method").upper()
    url = build_agent_api_url(base_url, path)
    attempts: list[dict[str, Any]] = []
    for attempt_index in range(max_retries + 1):
        attempt = attempt_index + 1
        try:
            response = _send_once(
                method=method,
                url=url,
                token=token,
                body=body,
                timeout_seconds=timeout_seconds,
            )
        except (TimeoutError, URLError, OSError) as exc:
            attempts.append({"attempt": attempt, "errorType": type(exc).__name__})
            if attempt_index < max_retries:
                continue
            raise AgentApiAdapterError(
                "PLATFORM_API_REQUEST_FAILED",
                "真实平台 API 请求失败",
                [{"field": "platformApi", "reason": type(exc).__name__}],
                context={"attempts": attempts, "maxRetries": max_retries, "url": url},
            ) from exc
        retryable_http_error = response.get("errorType") == "HTTPError" and int(response.get("statusCode") or 0) >= 500
        attempts.append(
            {
                "attempt": attempt,
                "statusCode": response.get("statusCode"),
                "errorType": response.get("errorType"),
                "retryable": bool(retryable_http_error),
            }
        )
        response["attempts"] = attempt
        response["maxRetries"] = max_retries
        response["attemptLog"] = attempts
        response["url"] = url
        if retryable_http_error and attempt_index < max_retries:
            continue
        return response
    raise AgentApiAdapterError(
        "PLATFORM_API_REQUEST_FAILED",
        "真实平台 API 请求失败",
        [{"field": "platformApi", "reason": "exhausted retries"}],
        context={"attempts": attempts, "maxRetries": max_retries, "url": url},
    )


def send_agent_api_post_json(
    *,
    base_url: str,
    path: str,
    token: str,
    body: dict[str, Any],
    timeout_seconds: int = 30,
    max_retries: int | str | None = 0,
) -> dict[str, Any]:
    return request_agent_api_json(
        method="POST",
        base_url=base_url,
        path=path,
        token=token,
        body=body,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def send_agent_api_get_json(
    *,
    base_url: str,
    path: str,
    token: str,
    timeout_seconds: int = 30,
    max_retries: int | str | None = 0,
) -> dict[str, Any]:
    return request_agent_api_json(
        method="GET",
        base_url=base_url,
        path=path,
        token=token,
        body=None,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
