"""Small HTTP adapter: one credential, one selected service, no authenticated redirects."""

from __future__ import annotations
import time
from contextvars import ContextVar
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import requests
from .errors import CLIError, from_upstream

active_client = ContextVar("aidee_client", default=None)


def segment(value):
    value = str(value)
    if (
        not value
        or value in (".", "..")
        or "/" in value
        or "\\" in value
        or any(ord(c) < 32 for c in value)
    ):
        raise CLIError("VALIDATION_FAILED", "资源标识不能包含路径分隔符或控制字符", 2)
    return quote(value, safe="")


class Client:
    def __init__(self, settings, secret=None):
        self.settings, self.secret = settings, secret

    def request(
        self,
        method,
        path,
        *,
        service="aidee",
        params=None,
        body=None,
        auth=True,
        team=False,
        raw=False,
        timeout=30,
        deadline=None,
    ):
        secret = (
            self.secret
            if self.secret is not None
            else (self.settings.credential() if auth else None)
        )
        if auth and not secret:
            raise CLIError(
                "MISSING_CREDENTIALS",
                "尚未配置本人凭据",
                3,
                hint="运行 aidee auth login",
            )
        if (
            secret
            and self.settings.auth_mode == "key"
            and not secret.startswith("aidee_")
        ):
            raise CLIError("AUTH_INVALID", "API Key 格式不正确", 3)
        base = self.settings.values["team_base" if service == "team" else "api_base"]
        headers = {"Accept": "application/json", "User-Agent": "aidee-cli/2"}
        if auth:
            headers[
                "IM-TOKEN" if self.settings.auth_mode == "token" else "X-Api-Key"
            ] = secret
        if team:
            team_id = self.settings.profile.get("team_id")
            if not team_id:
                raise CLIError("VALIDATION_FAILED", "请先执行 team use <team-id>", 2)
            headers["X-Team-Id"] = str(team_id)
        for attempt in range(3 if method == "GET" else 1):
            remaining = deadline - time.monotonic() if deadline else timeout
            if remaining <= 0:
                raise CLIError("REQUEST_TIMEOUT", "查询达到总耗时上限", 6)
            try:
                response = requests.request(
                    method,
                    base + path,
                    params=params,
                    json=body,
                    headers=headers,
                    timeout=min(timeout, remaining),
                    allow_redirects=False,
                )
            except requests.exceptions.Timeout:
                failure = CLIError(
                    "REQUEST_TIMEOUT",
                    "服务请求超时",
                    6,
                    hint="只读查询可重试；下单请使用 order recover",
                )
                if method == "GET" and attempt < 2:
                    continue
                raise failure from None
            except requests.exceptions.RequestException:
                if method == "GET" and attempt < 2:
                    continue
                raise CLIError(
                    "NETWORK_ERROR",
                    "无法连接所选服务",
                    6,
                    hint="运行 doctor 检查服务地址与网络",
                ) from None
            if 300 <= response.status_code < 400:
                raise CLIError(
                    "NETWORK_ERROR",
                    "服务返回重定向，未转发凭据",
                    6,
                    hint="核对服务基础地址",
                )
            if len(response.content) > 32 * 1024 * 1024:
                raise CLIError("NETWORK_ERROR", "服务响应超过32MiB上限", 6)
            try:
                payload = response.json()
            except ValueError:
                raise CLIError("BUSINESS_REJECTED", "服务未返回合法 JSON", 5) from None
            code = payload.get("code") if isinstance(payload, dict) else None
            retryable = response.status_code in (429, 502, 503, 504) or str(code) in (
                "429",
                "4290",
                "4291",
                "4292",
                "4293",
                "4299",
                "503",
            )
            if method == "GET" and retryable and attempt < 2:
                header = response.headers.get("Retry-After")
                try:
                    delay = max(0, float(header)) if header is not None else 2**attempt
                except (ValueError, TypeError):
                    try:
                        delay = max(
                            0, parsedate_to_datetime(header).timestamp() - time.time()
                        )
                    except (ValueError, TypeError, OverflowError, AttributeError):
                        delay = 2**attempt
                # Never retry sooner than the service asks. Long waits return the original
                # rate-limit result so the user can retry later, rather than blocking indefinitely.
                if delay <= 10:
                    if deadline and time.monotonic() + delay >= deadline:
                        raise CLIError("REQUEST_TIMEOUT", "查询达到总耗时上限", 6)
                    time.sleep(delay)
                    continue
            if response.status_code >= 400 or (
                code is not None and str(code) not in ("0", "200")
            ):
                message = (
                    payload.get("msg") or payload.get("message") or "服务拒绝请求"
                    if isinstance(payload, dict)
                    else "服务拒绝请求"
                )
                for private in (
                    secret,
                    (body or {}).get("code"),
                    (params or {}).get("code"),
                ):
                    if private:
                        message = str(message).replace(str(private), "***")
                raise from_upstream(
                    code or response.status_code, message, status=response.status_code
                )
            return (
                payload
                if raw
                else payload.get("data")
                if isinstance(payload, dict) and code is not None
                else payload
            )


def _page_payload(data):
    """Accept the verified IPage and IdeamakePage contracts, with at most one Result."""
    if isinstance(data, dict) and "code" in data:
        if str(data["code"]) not in ("0", "200"):
            raise from_upstream(data["code"], "分页接口返回失败")
        if data.get("success") is False or data.get("ok") is False:
            raise CLIError("BUSINESS_REJECTED", "分页接口返回失败", 5)
        data = data.get("data")
    if (
        not isinstance(data, dict)
        or data.get("success") is False
        or data.get("ok") is False
    ):
        raise CLIError("BUSINESS_REJECTED", "分页响应不是约定的页面对象", 5)
    if "code" in data:
        raise CLIError("BUSINESS_REJECTED", "分页响应包含未处理的嵌套信封", 5)
    if "records" in data:
        if not isinstance(data["records"], list):
            raise CLIError("BUSINESS_REJECTED", "分页响应缺少约定的 records 数组", 5)
        return data, data["records"]
    # Aidee's actual IdeamakePage is list/total/size/current/pages, not MyBatis IPage.
    fields = ("total", "size", "current", "pages")
    if isinstance(data.get("list"), list) and all(
        isinstance(data.get(key), int) and not isinstance(data.get(key), bool)
        for key in fields
    ):
        if (
            data["total"] >= 0
            and data["pages"] >= 0
            and data["current"] >= 1
            and data["size"] >= 1
        ):
            return data, data["list"]
    raise CLIError(
        "BUSINESS_REJECTED", "分页响应不符合 records 或 IdeamakePage 契约", 5
    )


def pages(
    fetch,
    params,
    *,
    all_pages=False,
    max_pages=100,
    max_items=5000,
    max_seconds=120,
    cursor=False,
    offset=0,
):
    started = time.monotonic()
    deadline = started + max_seconds
    query = dict(params)
    records = []
    meta = {"pages": 0, "truncated": False}
    seen = set()
    for index in range(max_pages if all_pages else 1):
        try:
            data, rows = _page_payload(fetch(query, deadline))
        except CLIError as error:
            error.meta = (
                {"partial": {"records": records, "pages": meta["pages"], "next": query}}
                if records
                else None
            )
            raise
        page_offset = offset if index == 0 else 0
        if page_offset > len(rows):
            raise CLIError(
                "VALIDATION_FAILED", "offset超过当前页条数，请重新获取该页", 2
            )
        rows = rows[page_offset:]
        meta["pages"] += 1
        if cursor:
            if not isinstance(data.get("hasMore"), bool):
                raise CLIError(
                    "BUSINESS_REJECTED", "游标页缺少约定的 hasMore 布尔值", 5
                )
            more = data["hasMore"]
            next_query = {
                **query,
                "cursor": True,
                "cursorSortTime": data.get("nextCursorSortTime"),
                "cursorId": data.get("nextCursorId"),
            }
            if more and (
                next_query["cursorSortTime"] is None or next_query["cursorId"] is None
            ):
                raise CLIError("BUSINESS_REJECTED", "服务声明仍有下一页但缺少游标", 5)
            marker = (
                str(next_query.get("cursorSortTime")),
                str(next_query.get("cursorId")),
            )
            if more and marker in seen:
                raise CLIError("BUSINESS_REJECTED", "服务返回重复游标，已停止翻页", 5)
            seen.add(marker)
        else:
            current = int(data.get("current", query.get("page", 1)))
            size = int(data.get("size", query.get("limit", 20)))
            if "total" not in data:
                raise CLIError("BUSINESS_REJECTED", "分页响应缺少 total", 5)
            more = current * size < int(data["total"])
            next_query = {**query, "page": current + 1}
        available = max_items - len(records)
        records.extend(rows[:available])
        limit_reason = (
            "items"
            if len(rows) > available or len(records) >= max_items
            else "pages"
            if index + 1 >= max_pages
            else "timeout"
            if time.monotonic() >= deadline
            else None
        )
        if len(rows) > available:
            meta.update(
                truncated=True,
                reason="items",
                next={"query": query, "offset": page_offset + available},
            )
        elif more and (limit_reason or not all_pages):
            meta.update(
                truncated=bool(all_pages),
                reason=limit_reason or "single_page",
                next=next_query,
            )
        if not all_pages or not more or limit_reason or meta["truncated"]:
            break
        if not rows and not page_offset:
            raise CLIError("BUSINESS_REJECTED", "服务返回空页但声明仍有内容", 5)
        query = next_query
    return records, meta
