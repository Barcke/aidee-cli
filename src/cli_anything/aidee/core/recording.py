"""Personal recording reads; no upload, deletion or new AI tasks."""

from cli_anything.aidee.utils.aidee_backend import api_request
from cli_anything.aidee.client import segment


def get(base_url, token, code):
    return api_request("GET", f"/recordings/{segment(code)}", base_url, token)


def list_recordings(base_url, token, page=1, size=20, **params):
    return api_request(
        "GET",
        "/recordings",
        base_url,
        token,
        params={"page": page, "limit": size, **params},
    )


def text_page(base_url, token, **params):
    return api_request("GET", "/recordings/text/page", base_url, token, params=params)


def usage_statistics(base_url, token):
    return api_request("GET", "/recordings/usage-statistics", base_url, token)
