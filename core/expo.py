"""Expo updates module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def check_update(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Check update."""
    return api_request("GET", "/expo/check-update", base_url, token, params=params)


def manifest(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get manifest."""
    return api_request("GET", "/expo/manifest", base_url, token, params=params)


def asset(base_url: str, token: Optional[str], hash: str) -> dict[str, Any]:
    """Get asset by hash."""
    return api_request("GET", f"/expo/assets/{hash}", base_url, token)
