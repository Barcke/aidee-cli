"""Template category module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def list_categories(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """List template categories."""
    return api_request("GET", "/recordings/template/category/list", base_url, token)


def get(base_url: str, token: Optional[str], code: str) -> dict[str, Any]:
    """Get template category by code."""
    return api_request("GET", f"/recordings/template/category/{code}", base_url, token)
