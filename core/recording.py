"""Recording module — create, get, update, delete, list recordings."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def create(base_url: str, token: Optional[str], title: str, **kwargs) -> dict[str, Any]:
    """Create a recording."""
    body = {"title": title, **kwargs}
    return api_request("POST", "/recordings", base_url, token, json_body=body)


def get(base_url: str, token: Optional[str], code: str) -> dict[str, Any]:
    """Get recording by code."""
    return api_request("GET", f"/recordings/{code}", base_url, token)


def update(base_url: str, token: Optional[str], code: str, **kwargs) -> dict[str, Any]:
    """Update recording."""
    return api_request("PUT", f"/recordings/{code}", base_url, token, json_body=kwargs)


def delete(base_url: str, token: Optional[str], code: str) -> dict[str, Any]:
    """Delete recording."""
    return api_request("DELETE", f"/recordings/{code}", base_url, token)


def list_recordings(
    base_url: str,
    token: Optional[str],
    page: int = 1,
    size: int = 20,
    **params,
) -> dict[str, Any]:
    """List recordings with pagination."""
    p = {"page": page, "size": size, **params}
    return api_request("GET", "/recordings", base_url, token, params=p)


def get_speakers(base_url: str, token: Optional[str], recording_code: str) -> dict[str, Any]:
    """Get speakers for a recording."""
    return api_request("GET", f"/recordings/{recording_code}/speakers", base_url, token)


def update_ai_summary(
    base_url: str,
    token: Optional[str],
    code: str,
    **kwargs,
) -> dict[str, Any]:
    """Update AI summary for recording."""
    return api_request("PUT", f"/recordings/{code}/ai-summary", base_url, token, json_body=kwargs)


def get_summary_templates(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get available summary templates."""
    return api_request("GET", "/recordings/summary-templates", base_url, token)


def get_by_file_name(base_url: str, token: Optional[str], file_name: str) -> dict[str, Any]:
    """Get recording by file name."""
    return api_request("GET", f"/recordings/by-file-name/{file_name}", base_url, token)


def update_by_file_name(base_url: str, token: Optional[str], file_name: str, **kwargs) -> dict[str, Any]:
    """Update recording by file name."""
    return api_request("PUT", f"/recordings/by-file-name/{file_name}", base_url, token, json_body=kwargs)


def batch_delete(base_url: str, token: Optional[str], codes: list[str]) -> dict[str, Any]:
    """Batch delete recordings."""
    return api_request("DELETE", "/recordings/batch", base_url, token, json_body=codes)


def text_page(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get recording text pagination."""
    return api_request("GET", "/recordings/text/page", base_url, token, params=params)


def update_speaker(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Update speaker."""
    return api_request("POST", "/recordings/update-speaker", base_url, token, json_body=kwargs)


def update_summary_template(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Update summary template for recording."""
    return api_request("POST", "/recordings/update-summary-template", base_url, token, json_body=kwargs)


def like_or_feedback(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Like or feedback."""
    return api_request("POST", "/recordings/like-or-feedback", base_url, token, json_body=kwargs)


def batch_move_group(base_url: str, token: Optional[str], recording_codes: list[str], group_code: str) -> dict[str, Any]:
    """Batch move recordings to group."""
    return api_request("POST", "/recordings/batch-move-group", base_url, token, json_body={"recordingCodes": recording_codes, "groupCode": group_code})


def usage_statistics(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get usage statistics."""
    return api_request("GET", "/recordings/usage-statistics", base_url, token)


def update_status(base_url: str, token: Optional[str], code: str, status: str) -> dict[str, Any]:
    """Update recording status."""
    return api_request("PUT", f"/recordings/{code}/status", base_url, token, json_body={"status": status})


def speakers_batch(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Batch query speakers."""
    return api_request("POST", "/recordings/speakers/batch", base_url, token, json_body=kwargs)


def speakers_search(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Search speakers."""
    return api_request("GET", "/recordings/speakers/search", base_url, token, params=params)


def batch_abstract(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Batch abstract."""
    return api_request("POST", "/recordings/batch-abstract", base_url, token, json_body=kwargs)
