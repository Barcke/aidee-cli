"""Existing resource wrappers delegate to the selected profile HTTP adapter."""

import os
from typing import Any, Optional
import requests
from cli_anything.aidee.client import active_client
from cli_anything.aidee.errors import CLIError, from_upstream


def api_request(
    method,
    path,
    base_url,
    token: Optional[str] = None,
    api_key: Optional[str] = None,
    json_body: Any = None,
    params=None,
):
    current = active_client.get()
    if current:
        # Core functions retain their source contract; CLI chooses the identity once.
        return {
            "code": 200,
            "data": current.request(method, path, body=json_body, params=params),
        }
    headers = {"Content-Type": "application/json"}
    key = api_key or (None if token else os.environ.get("AIDEE_API_KEY"))
    if token and api_key:
        raise CLIError("VALIDATION_FAILED", "一次请求只能选择一种凭据", 2)
    if token:
        headers["IM-TOKEN"] = token
    elif key:
        headers["X-Api-Key"] = key
    try:
        response = requests.request(
            method,
            base_url.rstrip("/") + path,
            json=json_body,
            params=params,
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )
        payload = response.json()
        if response.status_code >= 300 or str(payload.get("code", 200)) not in (
            "0",
            "200",
        ):
            raise from_upstream(
                payload.get("code", response.status_code),
                payload.get("msg", "服务拒绝请求"),
                status=response.status_code,
            )
        return payload
    except requests.exceptions.RequestException:
        raise CLIError("NETWORK_ERROR", "服务请求失败", 6) from None
