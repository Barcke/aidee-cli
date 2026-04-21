"""HTTP backend for AIDEE REST API."""

import json
import os
from typing import Any, Optional

import requests


def get_default_base_url() -> str:
    return os.environ.get("AIDEE_BASE_URL", "https://api.aidee.me/aidee-server")


def get_default_token() -> Optional[str]:
    return os.environ.get("AIDEE_TOKEN")


def get_default_api_key() -> Optional[str]:
    return os.environ.get("AIDEE_API_KEY")


def _request_timeout_sec() -> float:
    raw = os.environ.get("AIDEE_REQUEST_TIMEOUT", "30")
    try:
        return float(raw)
    except ValueError:
        return 30.0


def api_request(
    method: str,
    path: str,
    base_url: str,
    token: Optional[str] = None,
    api_key: Optional[str] = None,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
) -> dict[str, Any]:
    """Execute HTTP request to AIDEE API."""
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    effective_api_key = api_key or get_default_api_key()
    if token:
        # Token 鉴权使用 IM-TOKEN；ApiKey 走 X-Api-Key，两者可并存以兼容不同接口。
        headers["IM-TOKEN"] = token
    if effective_api_key:
        headers["X-Api-Key"] = effective_api_key

    try:
        resp = requests.request(
            method=method,
            url=url,
            json=json_body,
            params=params,
            headers=headers,
            timeout=_request_timeout_sec(),
        )
        resp.raise_for_status()
        if not resp.content:
            return {}
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"raw": resp.text}
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"AIDEE service unreachable at {url}. "
            "Ensure the service is running (e.g. mvn spring-boot:run). "
            f"Error: {e}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"Request timeout after {_request_timeout_sec()}s: {method} {url}. "
            "Set AIDEE_REQUEST_TIMEOUT to increase."
        ) from e
    except requests.exceptions.HTTPError as e:
        r = getattr(e, "response", None)
        msg = str(e)
        if r is not None:
            try:
                err_body = r.json()
                msg = err_body.get("msg") or err_body.get("message") or msg
            except Exception:
                if r.text:
                    msg = r.text[:500]
        raise RuntimeError(f"API error: {msg}") from e
