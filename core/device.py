"""Device module — bind, unbind, list, primary."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def bind(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Bind device."""
    return api_request("POST", "/devices/bind", base_url, token, json_body=kwargs)


def unbind(base_url: str, token: Optional[str], device_id: str) -> dict[str, Any]:
    """Unbind device."""
    return api_request("DELETE", f"/devices/unbind/{device_id}", base_url, token)


def list_devices(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """List user devices."""
    return api_request("GET", "/devices/user/devices", base_url, token)


def get_primary(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get primary device."""
    return api_request("GET", "/devices/user/primary", base_url, token)


def set_primary(base_url: str, token: Optional[str], device_id: str) -> dict[str, Any]:
    """Set primary device."""
    return api_request("PUT", "/devices/user/primary", base_url, token, json_body={"deviceId": device_id})


def get(base_url: str, token: Optional[str], identifier: str) -> dict[str, Any]:
    """Get device by identifier."""
    return api_request("GET", f"/devices/{identifier}", base_url, token)


def count(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get device count."""
    return api_request("GET", "/devices/count", base_url, token, params=params)


def update(base_url: str, token: Optional[str], device_id: str, **kwargs) -> dict[str, Any]:
    """Update device."""
    return api_request("PUT", f"/devices/{device_id}", base_url, token, json_body=kwargs)


def usage_logs(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get device usage logs."""
    return api_request("GET", "/devices/usage-logs", base_url, token, params=params)


def check_bound(base_url: str, token: Optional[str], sn: str) -> dict[str, Any]:
    """Check if device is bound."""
    return api_request("GET", f"/devices/check-bound/{sn}", base_url, token)
