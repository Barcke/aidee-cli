"""Read previously generated summaries."""

from cli_anything.aidee.utils.aidee_backend import api_request
from cli_anything.aidee.client import segment


def list_by_recording(base_url, token, recording_code):
    return api_request(
        "GET",
        f"/recordings/summaries/recording/{segment(recording_code)}",
        base_url,
        token,
    )


def get(base_url, token, summary_id):
    return api_request(
        "GET", f"/recordings/summaries/{segment(summary_id)}", base_url, token
    )
