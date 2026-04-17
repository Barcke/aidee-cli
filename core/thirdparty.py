"""Third party module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def convert_summary_to_document(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Convert summary to cloud document."""
    return api_request("POST", "/third-party/convert-summary-to-document", base_url, token, json_body=kwargs)
