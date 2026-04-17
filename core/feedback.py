"""Feedback usage record module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def create(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Create feedback."""
    return api_request("POST", "/feedback", base_url, token, json_body=kwargs)


def get(base_url: str, token: Optional[str], id: str) -> dict[str, Any]:
    """Get feedback by ID."""
    return api_request("GET", f"/feedback/{id}", base_url, token)


def update(base_url: str, token: Optional[str], id: str, **kwargs) -> dict[str, Any]:
    """Update feedback."""
    return api_request("PUT", f"/feedback/{id}", base_url, token, json_body=kwargs)


def list_all(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """List feedback."""
    return api_request("GET", "/feedback", base_url, token, params=params)


def delete(base_url: str, token: Optional[str], id: str) -> dict[str, Any]:
    """Delete feedback."""
    return api_request("DELETE", f"/feedback/{id}", base_url, token)
