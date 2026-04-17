"""Recording summary module — list, get, update, stop, delete summaries."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request
from cli_anything.aidee.core.session import get_base_url, get_token


def list_by_recording(
    base_url: str,
    token: Optional[str],
    recording_code: str,
) -> dict[str, Any]:
    """List summaries for a recording."""
    return api_request(
        "GET",
        f"/recordings/summaries/recording/{recording_code}",
        base_url,
        token,
    )


def get(
    base_url: str,
    token: Optional[str],
    summary_id: int,
) -> dict[str, Any]:
    """Get summary by ID."""
    return api_request("GET", f"/recordings/summaries/{summary_id}", base_url, token)


def update(
    base_url: str,
    token: Optional[str],
    summary_id: int,
    **kwargs,
) -> dict[str, Any]:
    """Update summary."""
    return api_request(
        "PUT",
        f"/recordings/summaries/{summary_id}",
        base_url,
        token,
        json_body=kwargs,
    )


def stop(
    base_url: str,
    token: Optional[str],
    summary_id: int,
) -> dict[str, Any]:
    """Stop summary generation."""
    return api_request("POST", f"/recordings/summaries/{summary_id}/stop", base_url, token)


def delete(
    base_url: str,
    token: Optional[str],
    summary_id: int,
) -> dict[str, Any]:
    """Delete summary."""
    return api_request("DELETE", f"/recordings/summaries/{summary_id}", base_url, token)
