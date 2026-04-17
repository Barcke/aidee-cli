"""User module — register, info, membership, update."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def register(base_url: str, **kwargs) -> dict[str, Any]:
    """Register user (no token required)."""
    return api_request("POST", "/users/register", base_url, token=None, json_body=kwargs)


def info(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get user information."""
    return api_request("GET", "/users/information", base_url, token)


def membership_current(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get current membership."""
    return api_request("GET", "/users/membership/current", base_url, token)


def update_user(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Update user."""
    return api_request("PUT", "/users/updateUser", base_url, token, json_body=kwargs)


def industry_position(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Update industry position."""
    return api_request("PUT", "/users/industry-position", base_url, token, json_body=kwargs)


def delete(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Delete user (logout)."""
    return api_request("DELETE", "/users/delete", base_url, token)
