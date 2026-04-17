"""Summary template module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def create(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Create summary template."""
    return api_request("POST", "/recordings/template", base_url, token, json_body=kwargs)


def update(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Update summary template."""
    return api_request("PUT", "/recordings/template", base_url, token, json_body=kwargs)


def delete(base_url: str, token: Optional[str], template_id: str) -> dict[str, Any]:
    """Delete summary template."""
    return api_request("DELETE", f"/recordings/template/{template_id}", base_url, token)


def list_templates(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """List summary templates."""
    return api_request("GET", "/recordings/template/list", base_url, token, params=params)


def get(base_url: str, token: Optional[str], template_id: str) -> dict[str, Any]:
    """Get template by ID."""
    return api_request("GET", f"/recordings/template/{template_id}", base_url, token)


def redeem(base_url: str, token: Optional[str], code: str) -> dict[str, Any]:
    """Redeem code."""
    return api_request("POST", "/recordings/redemption/redeem", base_url, token, json_body={"code": code})


def redeem_by_user(base_url: str, token: Optional[str], code: str, user_id: str) -> dict[str, Any]:
    """Redeem code by user (no token)."""
    return api_request("POST", "/recordings/redemption/redeem-by-user", base_url, token, json_body={"code": code, "userId": user_id})


def usage_bill(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get usage bill."""
    return api_request("GET", "/recordings/template/usage-bill", base_url, token, params=params)


def quota(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get quota."""
    return api_request("GET", "/recordings/template/quota", base_url, token)
