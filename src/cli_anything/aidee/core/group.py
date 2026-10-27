"""Existing personal folder reads."""

from cli_anything.aidee.utils.aidee_backend import api_request


def list_all(base_url, token):
    return api_request("GET", "/recording-groups/user/all", base_url, token)


def tree(base_url, token):
    return api_request("GET", "/recording-groups/tree/all", base_url, token)
