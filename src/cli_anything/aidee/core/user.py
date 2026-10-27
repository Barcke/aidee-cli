"""Current user only."""

from cli_anything.aidee.utils.aidee_backend import api_request


def info(base_url, token):
    return api_request("GET", "/users/information", base_url, token)


def membership_current(base_url, token):
    return api_request("GET", "/users/membership/current", base_url, token)
