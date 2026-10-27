"""Personal plans and original owned order reads."""

from cli_anything.aidee.utils.aidee_backend import api_request
from cli_anything.aidee.client import segment


def plans(base_url, token):
    return api_request("GET", "/memberships/plans", base_url, token)


def quota(base_url, token):
    return api_request("GET", "/memberships/quota/overview", base_url, token)


def orders(base_url, token, **params):
    return api_request("GET", "/memberships/orders", base_url, token, params=params)


def order(base_url, token, order_no):
    return api_request(
        "GET", f"/memberships/orders/{segment(order_no)}", base_url, token
    )


def recover(base_url, token, request_id):
    return api_request(
        "GET", f"/memberships/orders/by-request/{segment(request_id)}", base_url, token
    )
