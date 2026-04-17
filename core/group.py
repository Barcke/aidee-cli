"""Recording group module — create, update, delete, list."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def create(base_url: str, token: Optional[str], group_name: str, **kwargs) -> dict[str, Any]:
    """Create recording group."""
    return api_request("POST", "/recording-groups", base_url, token, json_body={"groupName": group_name, **kwargs})


def update(base_url: str, token: Optional[str], id: int = None, group_name: str = None, **kwargs) -> dict[str, Any]:
    """Update recording group."""
    body = {}
    if id is not None:
        body["id"] = id
    if group_name is not None:
        body["groupName"] = group_name
    body.update(kwargs)
    return api_request("PUT", "/recording-groups", base_url, token, json_body=body)


def delete(base_url: str, token: Optional[str], code: str) -> dict[str, Any]:
    """Delete recording group."""
    return api_request("DELETE", f"/recording-groups/{code}", base_url, token)


def list_all(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """List all recording groups."""
    return api_request("GET", "/recording-groups/user/all", base_url, token)


def sort(base_url: str, token: Optional[str], codes: list[str]) -> dict[str, Any]:
    """Sort recording groups."""
    return api_request("POST", "/recording-groups/sort", base_url, token, json_body={"codes": codes})
