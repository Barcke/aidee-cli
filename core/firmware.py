"""Firmware module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def upgrade_info(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get user devices upgrade info."""
    return api_request("GET", "/firmware/user/devices/upgrade-info", base_url, token, params=params)


def update_upgrade_record(base_url: str, token: Optional[str], record_id: str, **kwargs) -> dict[str, Any]:
    """Update upgrade record."""
    return api_request("PUT", f"/firmware/upgrade-records/{record_id}", base_url, token, json_body=kwargs)
