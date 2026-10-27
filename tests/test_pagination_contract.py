"""Anonymous fixtures for the real IdeamakePage wire contract, never recorded user content."""

import json
from unittest.mock import Mock, patch

import pytest

from cli_anything.aidee.client import Client, pages
from cli_anything.aidee.errors import CLIError
from cli_anything.aidee.settings import Settings


def ideamake_page(current=1, size=2, total=5):
    start = (current - 1) * size
    return {
        "list": [
            {"id": str(number)}
            for number in range(start + 1, min(start + size, total) + 1)
        ],
        "total": total,
        "size": size,
        "current": current,
        "pages": (total + size - 1) // size,
    }


@pytest.mark.parametrize("wrapped", [False, True])
def test_real_ideamake_page_through_client_can_resume_midpage_without_loss(wrapped):
    client = Client(Settings(), "aidee_anonymous_fixture")
    requested = []

    def response(method, url, **kwargs):
        query = kwargs["params"]
        requested.append(dict(query))
        body = ideamake_page(query["page"], query["limit"])
        if wrapped:
            body = {"code": 200, "msg": "success", "data": body}
        value = Mock(status_code=200, headers={}, content=json.dumps(body).encode())
        value.json.return_value = body
        return value

    def fetch(query, deadline):
        return client.request("GET", "/recordings", params=query, deadline=deadline)

    with patch("cli_anything.aidee.client.requests.request", side_effect=response):
        first, meta = pages(fetch, {"page": 1, "limit": 2}, all_pages=True, max_items=3)
        assert meta["truncated"] is True and meta["reason"] == "items"
        assert meta["next"] == {"query": {"page": 2, "limit": 2}, "offset": 1}
        rest, tail = pages(
            fetch, meta["next"]["query"], offset=meta["next"]["offset"], all_pages=True
        )
    assert [item["id"] for item in first + rest] == ["1", "2", "3", "4", "5"]
    assert tail["truncated"] is False
    assert requested == [
        {"page": 1, "limit": 2},
        {"page": 2, "limit": 2},
        {"page": 2, "limit": 2},
        {"page": 3, "limit": 2},
    ]


@pytest.mark.parametrize("code", [0, 200, "200"])
def test_explicit_success_wrapped_page_and_page_bound(code):
    def fetch(query, deadline):
        return {"code": code, "msg": "success", "data": ideamake_page(query["page"])}

    result, meta = pages(fetch, {"page": 1, "limit": 2}, all_pages=True, max_pages=1)
    assert len(result) == 2 and meta["truncated"] is True
    assert meta["reason"] == "pages" and meta["next"] == {"page": 2, "limit": 2}
    resumed, _ = pages(fetch, meta["next"])
    assert [item["id"] for item in resumed] == ["3", "4"]


@pytest.mark.parametrize(
    "body",
    [
        {"list": [], "total": 0},
        {"list": {}, "total": 0, "size": 2, "current": 1, "pages": 0},
        {"list": [], "total": False, "size": 2, "current": 1, "pages": 0},
        {"list": [], "total": 0, "size": 0, "current": 1, "pages": 0},
        {"records": None, **ideamake_page()},
        {"code": 200, "data": None},
        {"code": None, "data": ideamake_page()},
        {"success": False, **ideamake_page()},
        {"code": 200, "success": False, "data": ideamake_page()},
        {"code": 200, "data": {"code": 1004, "data": ideamake_page()}},
        {"code": 200, "data": {"code": 1004, **ideamake_page()}},
        {"code": 200, "data": {"code": 1004, "records": [], "total": 0}},
    ],
)
def test_invalid_or_failed_envelope_never_becomes_successful_page(body):
    with pytest.raises(CLIError):
        pages(lambda query, deadline: body, {"page": 1, "limit": 2}, all_pages=True)


@pytest.mark.parametrize("wrapped", [False, True])
def test_error_envelope_with_lookalike_page_is_permission_failure(wrapped):
    page = ideamake_page()
    body = (
        {"code": 1004, "msg": "anonymous denied", "data": page}
        if wrapped
        else {"code": 1004, **page}
    )
    with pytest.raises(CLIError) as error:
        pages(lambda query, deadline: body, {"page": 1, "limit": 2})
    assert error.value.exit_code == 4 and str(error.value.upstream) == "1004"


def test_known_empty_ideamake_page_is_complete():
    result, meta = pages(
        lambda query, deadline: ideamake_page(total=0),
        {"page": 1, "limit": 2},
        all_pages=True,
    )
    assert result == [] and meta["truncated"] is False and meta["pages"] == 1


@pytest.mark.parametrize("wrapped", [False, True])
def test_real_list_cursor_metadata_resumes_without_count_based_termination(wrapped):
    identifiers = ["2102281458272997377", "2102281458272997378", "2102281458272997379"]
    timestamp = "2026-10-27T09:10:11.123456"
    queries = []

    def fetch(query, deadline):
        queries.append(dict(query))
        start = identifiers.index(query["cursorId"]) + 1 if query.get("cursorId") else 0
        rows = [
            {"id": identifier}
            for identifier in identifiers[start : start + query["limit"]]
        ]
        more = start + len(rows) < len(identifiers)
        data = {
            "list": rows,
            "total": len(rows),
            "size": query["limit"],
            "current": 1,
            "pages": 1,
            "orders": [],
            "hasMore": more,
            "searchCount": False,
            "hitCount": False,
            "nextCursorSortTime": timestamp if more else None,
            "nextCursorId": rows[-1]["id"] if more else None,
        }
        return {"code": 200, "msg": "success", "data": data} if wrapped else data

    first, meta = pages(
        fetch,
        {"page": 1, "limit": 2, "cursor": True},
        cursor=True,
        all_pages=True,
        max_items=1,
    )
    assert meta["next"] == {
        "query": {"page": 1, "limit": 2, "cursor": True},
        "offset": 1,
    }
    rest, tail = pages(
        fetch,
        meta["next"]["query"],
        cursor=True,
        offset=meta["next"]["offset"],
        all_pages=True,
    )
    assert [row["id"] for row in first + rest] == identifiers
    assert tail["truncated"] is False and tail["pages"] == 2
    assert queries[-1]["cursorId"] == identifiers[1]
    assert isinstance(queries[-1]["cursorId"], str)
    assert queries[-1]["cursorSortTime"] == timestamp


def test_cursor_list_page_bound_exposes_true_next_cursor():
    data = {
        **ideamake_page(size=1, total=1),
        "hasMore": True,
        "nextCursorId": "2102281458272997377",
        "nextCursorSortTime": "2026-01-01T00:00:00",
    }
    rows, meta = pages(
        lambda query, deadline: data,
        {"page": 1, "limit": 1},
        cursor=True,
        all_pages=True,
        max_pages=1,
    )
    assert len(rows) == 1 and meta["truncated"] is True and meta["reason"] == "pages"
    assert meta["next"]["cursorId"] == "2102281458272997377"


def test_cursor_without_boolean_has_more_cannot_claim_complete():
    with pytest.raises(CLIError):
        pages(
            lambda query, deadline: ideamake_page(),
            {"limit": 2},
            cursor=True,
            all_pages=True,
        )


def test_failed_wrapped_next_page_reports_partial_instead_of_success():
    def fetch(query, deadline):
        if query["page"] == 1:
            return ideamake_page()
        return {
            "code": 1004,
            "msg": "anonymous denied",
            "data": ideamake_page(current=2),
        }

    with pytest.raises(CLIError) as error:
        pages(fetch, {"page": 1, "limit": 2}, all_pages=True)
    assert error.value.exit_code == 4
    assert error.value.meta["partial"] == {
        "records": [{"id": "1"}, {"id": "2"}],
        "pages": 1,
        "next": {"page": 2, "limit": 2},
    }
