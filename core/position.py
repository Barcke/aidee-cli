"""Position module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def list_all(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """List positions."""
    return api_request("GET", "/positions", base_url, token, params=params)
