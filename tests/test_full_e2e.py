"""Integration uses a loopback HTTP fixture and exact module/installed wheel, never real accounts."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import urlsplit, parse_qs
import pytest
from click.testing import CliRunner
from cli_anything.aidee.aidee_cli import cli


@pytest.fixture
def server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data, code=200, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "code": code,
                        "msg": "rejected" if code != 200 else "success",
                        "data": data,
                    }
                ).encode()
            )

        def do_GET(self):
            path = urlsplit(self.path).path
            query = parse_qs(urlsplit(self.path).query)
            calls.append(("GET", path, query, dict(self.headers), None))
            if path == "/integration/keys/current":
                return self.send(
                    {
                        "userCenterUserId": "u1",
                        "aideeUserId": 2102281458272997376,
                        "keyPrefix": "aidee_test",
                        "scopes": ["read", "write"],
                        "effectivePermissions": {
                            "read": True,
                            "checkoutSelf": True,
                            "redeemSelf": True,
                        },
                    }
                )
            if path == "/users/information":
                return self.send({"id": 2102281458272997376, "nickname": "本人"})
            if path == "/recordings/bad":
                return self.send(None, 1004)
            if path == "/recordings":
                page = int(query.get("page", [1])[0])
                return self.send(
                    {
                        "records": [
                            {"id": 2102281458272997376 + page, "code": "r" + str(page)}
                        ],
                        "current": page,
                        "size": 1,
                        "total": 2,
                    }
                )
            if path == "/recordings/text/page":
                return self.send(
                    {
                        "records": [{"id": 1, "text": "原文"}],
                        "current": 1,
                        "size": 20,
                        "total": 1,
                    }
                )
            if path == "/team/aidee/teams/joined":
                return self.send([{"teamId": "11", "name": "团队"}])
            if path == "/team/aidee/spaces/21":
                return self.send({"spaceId": "21", "teamId": "11", "spaceType": "TEAM"})
            if path == "/team/aidee/spaces":
                return self.send(
                    [
                        {"spaceId": "21", "teamId": "11", "spaceType": "TEAM"},
                        {"spaceId": "99", "teamId": "11", "spaceType": "PERSONAL"},
                    ]
                )
            if path == "/team/aidee/spaces/21/recordings":
                next_page = "cursorId" in query
                return self.send(
                    {
                        "records": [
                            {"id": 2102281458272997376, "entryType": "RECORDING"}
                        ],
                        "hasMore": not next_page,
                        "nextCursorId": None if next_page else 2102281458272997376,
                        "nextCursorSortTime": None
                        if next_page
                        else "2026-10-26T15:01:02.123456",
                        "current": 1,
                        "size": 1,
                        "total": 0,
                    }
                )
            if path == "/team/aidee/spaces/21/recordings/merge/text":
                return self.send(None, 400)
            if path == "/recordings/redemption/code-detail":
                return self.send({"name": "会员30天", "durationDays": 30})
            if path == "/memberships/plans":
                return self.send(
                    [
                        {
                            "packageVersionId": "p1",
                            "priceMinor": "1000",
                            "currency": "CNY",
                            "purchasable": True,
                            "name": "月度套餐",
                        }
                    ]
                )
            if path.startswith("/memberships/orders/by-request/"):
                return self.send(
                    {
                        "requestId": path.rsplit("/", 1)[1],
                        "orderNo": "o1",
                        "requestState": "READY",
                        "payment": {"codeUrl": "weixin://wxpay/mock"},
                    }
                )
            if path == "/memberships/orders/o1":
                return self.send(
                    {"orderNo": "o1", "status": "PAID", "fulfillmentStatus": "SUCCESS"}
                )
            return self.send({"code": "r1", "title": "本人录音"})

        def do_POST(self):
            body = json.loads(
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
            )
            calls.append(("POST", self.path, {}, dict(self.headers), body))
            if self.path == "/memberships/checkout":
                return self.send(
                    {
                        "orderNo": "o1",
                        "codeUrl": "weixin://wxpay/mock",
                        "amount": "10.00",
                    }
                )
            if self.path == "/integration/cli-auth/token":
                return self.send({"apiKey": "aidee_browser_key", "scopes": ["read"]})
            return self.send("兑换成功")

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=http.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{http.server_port}", calls
    http.shutdown()
    http.server_close()
    worker.join()


@pytest.fixture
def invoke(server, monkeypatch):
    base, calls = server
    monkeypatch.setenv("AIDEE_BASE_URL", base)
    monkeypatch.setenv("AIDEE_TEAM_BASE_URL", base)
    monkeypatch.setenv("AIDEE_WEB_BASE", base)
    monkeypatch.setenv("AIDEE_API_KEY", "aidee_test_secret")

    def run(*args, input=None):
        return CliRunner(mix_stderr=False).invoke(cli, list(args), input=input)

    return run, calls


def payload(result):
    assert result.exception is None or result.exit_code != 0, (
        result.output,
        result.exception,
    )
    return json.loads(result.stdout)


def test_actual_personal_paging_and_exact_id(invoke):
    run, calls = invoke
    result = run("recording", "list", "--all", "--limit", "1")
    data = payload(result)
    assert result.exit_code == 0, result.output
    assert len(data["data"]) == 2 and data["data"][0]["id"] == "2102281458272997377"
    assert all("IM-TOKEN" not in x[3] for x in calls)


def test_200_permission_failure_exits_four(invoke):
    run, _ = invoke
    result = run("recording", "get", "bad")
    assert result.exit_code == 4 and payload(result)["error"]["upstreamCode"] == "1004"


def test_personal_export_complete_and_nonoverwrite(invoke, tmp_path):
    run, _ = invoke
    target = tmp_path / "recording.md"
    result = run("recording", "export", "r1", "--output-file", str(target))
    assert result.exit_code == 0, result.output
    assert target.read_text() == "原文\n"
    second = run("recording", "export", "r1", "--output-file", str(target))
    assert second.exit_code == 7 and target.read_text() == "原文\n"


def test_team_discovery_context_and_exact_cursor(invoke):
    run, calls = invoke
    assert run("team", "list").exit_code == 0
    assert "X-Team-Id" not in calls[-1][3]
    assert run("team", "use", "11").exit_code == 0
    assert len(payload(run("space", "list"))["data"]) == 1
    result = run("space", "recording", "list", "--space", "21", "--all")
    assert result.exit_code == 0, result.output
    assert len(payload(result)["data"]) == 2
    assert calls[-1][2]["cursorId"] == ["2102281458272997376"]
    assert calls[-1][2]["cursorSortTime"] == ["2026-10-26T15:01:02.123456"]
    assert calls[-1][3]["X-Team-Id"] == "11"


def test_dryrun_writes_do_not_read_or_write_server(invoke):
    run, calls = invoke
    for args in [
        ("membership", "checkout", "--plan", "p1", "--dry-run"),
        ("redemption", "redeem", "--dry-run"),
    ]:
        assert run(*args).exit_code == 0
    assert calls == []


def test_checkout_confirms_and_persists_request_before_single_post(invoke):
    run, calls = invoke
    refused = run("membership", "checkout", "--plan", "p1")
    assert refused.exit_code == 4, refused.output
    assert not any(x[0] == "POST" for x in calls)
    result = run("membership", "checkout", "--plan", "p1", "--yes")
    assert result.exit_code == 0, result.output
    assert payload(result)["data"]["checkoutUrl"].endswith("/cli/checkout/o1")
    assert "aidee_test_secret" not in payload(result)["data"]["checkoutUrl"]
    rid = payload(result)["data"]["requestId"]
    from cli_anything.aidee.settings import directory

    stored = json.loads(
        (directory() / "requests/default" / (rid + ".json")).read_text()
    )
    assert stored["orderNo"] == "o1"
    assert (
        run(
            "membership", "checkout", "--plan", "p1", "--request-id", rid, "--yes"
        ).exit_code
        == 0
    )
    posts = [x for x in calls if x[0] == "POST"]
    assert len(posts) == 1 and posts[0][4]["expectedPriceMinor"] == "1000"
    assert set(posts[0][4]) == {"packageVersionId", "expectedPriceMinor", "requestId"}


def test_owned_order_wait_and_recover(invoke):
    run, _ = invoke
    assert (
        payload(run("order", "wait", "o1", "--timeout", "1"))["data"][
            "fulfillmentStatus"
        ]
        == "SUCCESS"
    )
    assert payload(run("order", "recover", "rid1"))["data"]["payment"][
        "codeUrl"
    ].startswith("weixin:")


def test_redemption_is_self_only_and_confirmation_required(invoke):
    run, calls = invoke
    assert run("redemption", "redeem", "REDEEM-TEST").exit_code == 4
    result = run("redemption", "redeem", "REDEEM-TEST", "--yes")
    assert result.exit_code == 0, result.output
    post = next(x for x in calls if x[0] == "POST")
    assert post[4] == {"code": "REDEEM-TEST", "redeemSource": "aideeApp"}
    assert "REDEEM-TEST" not in result.stdout


def test_existing_key_import_and_logout_do_not_create_or_revoke(invoke, monkeypatch):
    run, calls = invoke
    assert run("auth", "login").exit_code == 0
    monkeypatch.delenv("AIDEE_API_KEY")
    assert payload(run("auth", "status", "--verify"))["data"]["verified"] is True
    assert run("auth", "logout").exit_code == 0
    assert not payload(run("auth", "status"))["data"]["configured"]
    assert not any(x[0] == "POST" for x in calls)


def test_browser_pkce_state_binding_and_no_stdout_key(invoke, monkeypatch):
    run, calls = invoke
    import requests

    def browser(url):
        q = parse_qs(urlsplit(url).query)
        redirect = q["redirect_uri"][0]
        wrong = requests.get(
            redirect, params={"code": "abc", "state": "wrong"}, timeout=5
        )
        assert wrong.status_code == 400
        assert q["code_challenge_method"] == ["S256"]
        assert q["scope"] == ["read write"]
        correct = requests.get(
            redirect, params={"code": "abc", "state": q["state"][0]}, timeout=5
        )
        assert correct.status_code == 200
        return True

    monkeypatch.setattr("cli_anything.aidee.auth.webbrowser.open", browser)
    result = run("auth", "login", "--browser", "--scope", "write")
    assert result.exit_code == 0, result.output
    assert "aidee_browser_key" not in result.stdout
    exchange = next(x for x in calls if x[0] == "POST")
    assert set(exchange[4]) == {"code", "codeVerifier", "clientId", "redirectUri"}
    assert "X-Api-Key" not in exchange[3] and "IM-TOKEN" not in exchange[3]


def test_safe_legacy_query_aliases(invoke):
    run, _ = invoke
    for args in [
        ("user", "info"),
        ("session", "status"),
        ("recording", "list", "--size", "1"),
        ("membership", "order-status", "o1"),
    ]:
        result = run(*args)
        assert result.exit_code == 0, (args, result.output)


@pytest.mark.parametrize(
    "args",
    [
        ("recording", "delete", "r1"),
        ("redemption", "create"),
        ("api", "GET", "/admin"),
        ("team", "members"),
        ("user", "delete"),
    ],
)
def test_excluded_operations_are_unavailable(invoke, args):
    run, calls = invoke
    result = run(*args)
    assert result.exit_code == 2 and calls == []


def test_local_dry_run_never_enters_startup_updater(invoke, monkeypatch):
    run, calls = invoke
    from unittest.mock import Mock

    mock = Mock(side_effect=AssertionError("dry-run cannot update"))
    monkeypatch.setattr("cli_anything.aidee.updates.startup_check", mock)
    result = run("membership", "checkout", "--plan", "p1", "--dry-run")
    assert result.exit_code == 0, result.output
    mock.assert_not_called()
    assert calls == []


def test_explicit_command_json_disables_auto_install(invoke, monkeypatch):
    run, _ = invoke
    captured = []
    monkeypatch.setattr(
        "cli_anything.aidee.updates.startup_check",
        lambda settings, explicit_json: captured.append(explicit_json),
    )
    assert run("recording", "list", "--json").exit_code == 0
    assert captured == [True]


def test_space_detail_uses_path_route_accepted_by_key_allowlist(invoke):
    run, calls = invoke
    assert run("team", "use", "11").exit_code == 0
    result = run("space", "get", "21")
    assert result.exit_code == 0, result.output
    assert calls[-1][1] == "/team/aidee/spaces/21"
    assert calls[-1][2] == {} and calls[-1][3]["X-Team-Id"] == "11"


def test_team_summary_namespaced_id_is_encoded_without_precision_loss(invoke):
    run, calls = invoke
    assert run("team", "use", "11").exit_code == 0
    result = run(
        "space",
        "recording",
        "summary",
        "r1",
        "team:2102281458272997376",
        "--space",
        "21",
    )
    assert result.exit_code == 0, result.output
    assert (
        calls[-1][1]
        == "/team/aidee/spaces/21/recordings/r1/summaries/team%3A2102281458272997376"
    )
