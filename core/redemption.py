"""兑换码相关 API（与后端 RedemptionController 对齐）。"""

from __future__ import annotations

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def create_code(base_url: str, token: Optional[str], body: dict[str, Any]) -> dict[str, Any]:
    """新增单条兑换码（需登录）：POST /recordings/redemption/codes"""
    return api_request("POST", "/recordings/redemption/codes", base_url, token, json_body=body)


def code_detail(base_url: str, token: Optional[str], code: str) -> dict[str, Any]:
    """查询兑换码详情：GET /recordings/redemption/code-detail"""
    return api_request(
        "GET",
        "/recordings/redemption/code-detail",
        base_url,
        token,
        params={"code": code},
    )


def list_records(
    base_url: str,
    token: Optional[str],
    redeem_source: Optional[str] = None,
) -> dict[str, Any]:
    """当前用户兑换记录：GET /recordings/redemption/records"""
    params: dict[str, str] = {}
    if redeem_source:
        params["redeemSource"] = redeem_source
    return api_request("GET", "/recordings/redemption/records", base_url, token, params=params or None)
