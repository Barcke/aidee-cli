"""Membership module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def levels(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get membership levels."""
    return api_request("GET", "/memberships/levels", base_url, token)


def purchase(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Purchase membership."""
    return api_request("POST", "/memberships/purchase", base_url, token, json_body=kwargs)


def order(base_url: str, token: Optional[str], order_no: str) -> dict[str, Any]:
    """Get order by order no."""
    return api_request("GET", f"/memberships/orders/{order_no}", base_url, token)


def order_status(base_url: str, token: Optional[str], order_no: str) -> dict[str, Any]:
    """Get order status."""
    return api_request("GET", f"/memberships/orders/{order_no}/status", base_url, token)


def orders(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """List orders."""
    return api_request("GET", "/memberships/orders", base_url, token, params=params)


def upgrade_price(base_url: str, token: Optional[str], target_membership_level_id: str) -> dict[str, Any]:
    """Get upgrade price."""
    return api_request("GET", f"/memberships/upgrade-price/{target_membership_level_id}", base_url, token)
