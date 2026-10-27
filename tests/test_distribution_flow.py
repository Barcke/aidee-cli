"""Approved installation/upgrade obligations beyond command existence."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from cli_anything.aidee import skills, updates
from cli_anything.aidee.errors import CLIError
from cli_anything.aidee.settings import Settings


def test_each_user_edited_skill_can_be_recovered(tmp_path):
    skill = tmp_path / "aidee-user" / "SKILL.md"
    skill.parent.mkdir()
    skill.write_text("first local edit", encoding="utf-8")
    skills.sync(tmp_path)
    skill.write_text("second local edit 中文🙂", encoding="utf-8")
    result = skills.sync(tmp_path)
    assert result["backedUp"] == ["aidee-user"]
    recovered = [
        p.read_text(encoding="utf-8") for p in skill.parent.glob("SKILL.md.pre-aidee*")
    ]
    assert "first local edit" in recovered and "second local edit 中文🙂" in recovered


def test_skill_sync_is_utf8_with_windows_locale_defaults(tmp_path, monkeypatch):
    real_fdopen = os.fdopen

    def windows(fd, mode, **kwargs):
        kwargs.setdefault("encoding", "cp1252")
        kwargs.setdefault("newline", "\r\n")
        return real_fdopen(fd, mode, **kwargs)

    monkeypatch.setattr(skills.os, "fdopen", windows)
    skills.sync(tmp_path)
    assert (tmp_path / "aidee-user/SKILL.md").read_text(
        encoding="utf-8"
    ) == skills.read("aidee-user")


def test_update_explicitly_reports_unrequested_skills_without_running_them(
    tmp_path, monkeypatch
):
    old = {
        "filename": "old.whl",
        "url": "https://example.com/old.whl",
        "sha256": "0" * 64,
        "size": 3,
    }
    receipt = {
        "manager": "uv",
        "version": updates.__version__,
        "artifact": old,
        "environment": str(tmp_path),
        "distribution": "cli-anything-aidee",
    }
    manifest = {
        "updateAvailable": True,
        "version": "2.1.0",
        "commit": "a" * 40,
        "channel": "stable",
        "artifacts": [{**old, "filename": "new.whl"}],
    }
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    with (
        patch.object(updates, "installation", return_value=(receipt, "/known/uv")),
        patch.object(
            updates, "verified_wheel", side_effect=lambda a, t: Path(t) / a["filename"]
        ),
        patch.object(
            updates.subprocess,
            "run",
            side_effect=[
                Mock(returncode=0),
                Mock(returncode=0, stdout="aidee, version 2.1.0"),
            ],
        ) as run,
    ):
        result = updates.install_update(Settings(), manifest)
    assert result["skillsSync"]["status"] == "not_requested"
    assert run.call_count == 2


def test_midpage_truncation_can_resume_without_losing_remaining_rows():
    from cli_anything.aidee.client import pages

    def fetch(query, deadline):
        return {
            "records": [{"id": i} for i in range(1, 6)],
            "current": 1,
            "size": 5,
            "total": 5,
        }

    first, meta = pages(fetch, {"page": 1, "limit": 5}, all_pages=True, max_items=2)
    next_ = meta["next"]
    resumed, tail = pages(fetch, next_["query"], offset=next_["offset"], all_pages=True)
    assert [x["id"] for x in first + resumed] == [1, 2, 3, 4, 5]
    assert tail["truncated"] is False


@pytest.mark.parametrize("state", ["FAILED", "FAILURE"])
def test_paid_fulfillment_failure_finishes_wait_without_new_order(state):
    from click.testing import CliRunner
    from cli_anything.aidee.aidee_cli import cli

    with (
        patch(
            "cli_anything.aidee.client.Client.request",
            return_value={"status": "PAID", "fulfillmentStatus": state},
        ) as request,
        patch("cli_anything.aidee.aidee_cli.time.sleep") as sleep,
    ):
        result = CliRunner().invoke(cli, ["order", "wait", "test-order"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["meta"]["fulfillmentFailed"] is True
    assert data["meta"]["paymentFailed"] is False
    assert "不要重新下单" in data["meta"]["hint"]
    assert request.call_count == 1 and not sleep.called
    assert request.call_args.args[:2] == ("GET", "/memberships/orders/test-order")


def test_readonly_doctor_reports_checked_identity_and_permission_hint():
    from click.testing import CliRunner
    from cli_anything.aidee.aidee_cli import cli

    with patch(
        "cli_anything.aidee.client.Client.request",
        side_effect=[
            {
                "userCenterUserId": "person-1",
                "scopes": ["read"],
                "effectivePermissions": {
                    "read": True,
                    "redeemSelf": False,
                    "checkoutSelf": False,
                },
            },
            CLIError(
                "PERMISSION_DENIED", "denied", 4, hint="检查空间分享", upstream=1004
            ),
        ],
    ):
        result = CliRunner().invoke(cli, ["--api-key", "fake-key", "doctor"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)["data"]
    assert report["healthy"] is False
    assert report["checks"][1]["userCenterUserId"] == "person-1"
    assert report["checks"][1]["effectivePermissions"]["checkoutSelf"] is False
    assert report["checks"][2]["upstreamCode"] == 1004
    assert report["checks"][2]["hint"] == "检查空间分享"
    assert "fake-key" not in result.output


def test_register_existing_tool_requires_signed_identical_installed_files(
    tmp_path, monkeypatch
):
    import io
    import zipfile
    from cli_anything.aidee import __version__

    contents = io.BytesIO()
    with zipfile.ZipFile(contents, "w") as archive:
        archive.writestr("cli_anything/aidee/__init__.py", b"trusted-content")
    wheel = tmp_path / "signed.whl"
    wheel.write_bytes(contents.getvalue())
    installed = tmp_path / "package"
    installed.write_bytes(b"different-content")
    dist = Mock()
    dist.read_text.return_value = None
    dist.locate_file.return_value = installed
    manifest = {
        "version": __version__,
        "commit": "a" * 40,
        "channel": "preview",
        "artifacts": [{"sha256": "0" * 64}],
    }
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    with (
        patch.object(
            updates, "managed_environment", return_value=("/known/pipx", dist)
        ),
        patch.object(updates, "verify_manifest", return_value=manifest),
        patch.object(updates, "fetch", return_value=b""),
        patch.object(updates, "public_key"),
        patch.object(updates, "verified_wheel", return_value=wheel),
    ):
        with pytest.raises(CLIError, match="签名wheel不一致"):
            updates.register_installation(Settings(), "pipx")
        assert not (tmp_path / ".aidee-install.json").exists()
        installed.write_bytes(b"trusted-content")
        registered = updates.register_installation(Settings(), "pipx")
    assert registered["sourceVerified"] is True
    assert (
        json.loads((tmp_path / ".aidee-install.json").read_text())["registration"]
        == "signed-wheel-file-verification"
    )


def test_packaged_skill_source_uses_explicit_utf8(monkeypatch):
    read_text = Path.read_text

    def windows(path, encoding=None, **kwargs):
        return read_text(path, encoding=encoding or "cp1252", **kwargs)

    monkeypatch.setattr(Path, "read_text", windows)
    assert "Aidee" in skills.read("aidee-user")


def test_offset_cli_passes_only_page_limit_to_server():
    from click.testing import CliRunner
    from cli_anything.aidee.aidee_cli import cli

    with patch(
        "cli_anything.aidee.client.Client.request",
        return_value={
            "records": [{"id": 1}, {"id": 2}, {"id": 3}],
            "current": 1,
            "size": 3,
            "total": 3,
        },
    ) as request:
        result = CliRunner().invoke(
            cli, ["recording", "list", "--page", "1", "--limit", "3", "--offset", "2"]
        )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"] == [{"id": "3"}]
    assert request.call_args.kwargs["params"]["limit"] == 3
    assert "offset" not in request.call_args.kwargs["params"]


def test_paid_pending_waits_and_unknown_remains_unknown():
    from click.testing import CliRunner
    from cli_anything.aidee.aidee_cli import cli

    path = "cli_anything.aidee.aidee_cli.time"
    with (
        patch(
            "cli_anything.aidee.client.Client.request",
            side_effect=[
                {"status": "PAID", "fulfillmentStatus": "PENDING"},
                {"status": "PAID", "fulfillmentStatus": "SUCCESS"},
            ],
        ) as request,
        patch(path + ".monotonic", return_value=0),
        patch(path + ".sleep"),
    ):
        result = CliRunner().invoke(cli, ["order", "wait", "test-order"])
    assert result.exit_code == 0 and request.call_count == 2
    assert json.loads(result.output)["meta"]["fulfillmentStatus"] == "SUCCESS"
    with (
        patch(
            "cli_anything.aidee.client.Client.request",
            return_value={"status": "PAID", "fulfillmentStatus": "UNKNOWN"},
        ),
        patch(path + ".monotonic", side_effect=[0, 0, 0, 181]),
        patch(path + ".sleep"),
    ):
        result = CliRunner().invoke(cli, ["order", "wait", "test-order"])
    meta = json.loads(result.output)["meta"]
    assert meta["timedOut"] is True and meta["fulfillmentStatus"] == "UNKNOWN"
    assert meta["paymentStatus"] == "PAID" and meta["paymentFailed"] is False


@pytest.mark.parametrize("method,expected", [("GET", 3), ("POST", 1)])
def test_explicit_key_ratelimit_retries_only_reads(method, expected):
    from cli_anything.aidee.client import Client

    response = Mock(status_code=200, content=b"{}", headers={"Retry-After": "0"})
    response.json.return_value = {"code": 4292, "msg": "rate limited"}
    with (
        patch(
            "cli_anything.aidee.client.requests.request", return_value=response
        ) as request,
        patch("cli_anything.aidee.client.time.sleep"),
    ):
        with pytest.raises(CLIError) as error:
            Client(Settings(), "aidee_fake").request(method, "/example")
    assert error.value.code == "RATE_LIMITED" and error.value.exit_code == 6
    assert request.call_count == expected


def test_long_retry_after_is_never_shortened_to_retry_early():
    from cli_anything.aidee.client import Client

    response = Mock(status_code=429, content=b"{}", headers={"Retry-After": "120"})
    response.json.return_value = {"code": 4292, "msg": "rate limited"}
    with (
        patch(
            "cli_anything.aidee.client.requests.request", return_value=response
        ) as request,
        patch("cli_anything.aidee.client.time.sleep") as sleep,
    ):
        with pytest.raises(CLIError, match="rate limited"):
            Client(Settings(), "aidee_fake").request("GET", "/example")
    assert request.call_count == 1 and not sleep.called


def test_real_entrypoint_redirects_skill_as_utf8_under_non_utf8_locale(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "cli_anything.aidee", "skills", "read", "aidee-user"],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
            "PYTHONIOENCODING": "cp1252:strict",
        },
        capture_output=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stdout.decode("utf-8").rstrip("\n") == skills.read(
        "aidee-user"
    ).rstrip("\n")


@pytest.mark.parametrize(
    "week,timezone,start,end",
    [
        (
            "2020-W01",
            "America/New_York",
            "2019-12-30T13:00:00",
            "2020-01-06T12:59:59.999999",
        ),
        (
            "2020-W53",
            "Asia/Shanghai",
            "2020-12-28T00:00:00",
            "2021-01-03T23:59:59.999999",
        ),
    ],
)
def test_explicit_iso_week_crosses_calendar_year_without_network(
    week, timezone, start, end
):
    from click.testing import CliRunner
    from cli_anything.aidee.aidee_cli import cli

    with patch("cli_anything.aidee.client.requests.request") as request:
        result = CliRunner().invoke(
            cli,
            ["recording", "list", "--week", week, "--timezone", timezone, "--dry-run"],
        )
    assert result.exit_code == 0, result.output
    params = json.loads(result.output)["data"]["params"]
    assert (params["startTime"], params["endTime"]) == (start, end)
    assert not request.called


@pytest.mark.parametrize(
    "args",
    [
        ["--week", "2021-W53"],
        ["--week", "2026-W1"],
        ["--week", "2026-W01", "--period", "last_week"],
        ["--week", "2026-W01", "--from", "2026-01-01"],
        ["--week", "2026-W01", "--to", "2026-01-02"],
    ],
)
def test_invalid_or_conflicting_iso_week_is_rejected_without_network(args):
    from click.testing import CliRunner
    from cli_anything.aidee.aidee_cli import cli

    with patch("cli_anything.aidee.client.requests.request") as request:
        result = CliRunner().invoke(cli, ["recording", "list", *args, "--dry-run"])
    assert result.exit_code == 2, result.output
    message = json.loads(result.output)["error"]["message"]
    assert "ISO" in message or "week与" in message
    assert not request.called


def test_release_version_metadata_lock_and_uninstalled_fallback_agree():
    import re
    import runpy
    from importlib.metadata import PackageNotFoundError

    root = Path(__file__).parents[1]
    project_version = re.search(
        r'^version = "([^"]+)"$',
        (root / "pyproject.toml").read_text(encoding="utf-8"),
        re.MULTILINE,
    ).group(1)
    lock_version = re.search(
        r'name = "cli-anything-aidee"\nversion = "([^"]+)"',
        (root / "uv.lock").read_text(encoding="utf-8"),
    ).group(1)
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        uninstalled = runpy.run_path(str(root / "src/cli_anything/aidee/__init__.py"))
    assert (
        updates.__version__
        == project_version
        == lock_version
        == uninstalled["__version__"]
    )


def test_production_release_cdn_does_not_change_business_api_origins(monkeypatch):
    monkeypatch.delenv("AIDEE_RELEASE_BASE", raising=False)
    settings = Settings()
    assert settings.values["release_base"] == "https://ai-agent.ideamake.cn/aidee-cli"
    assert settings.values["api_base"] == "https://api.aidee.me/aidee-server"
    assert settings.values["team_base"] == "https://api.aidee.me/team-aidee-server"
    manifest = {"version": "2.1.0", "channel": "stable"}
    with (
        patch.object(updates, "fetch", return_value=b"fixture") as fetch,
        patch.object(updates, "public_key"),
        patch.object(updates, "verify_manifest", return_value=manifest),
    ):
        updates.check_update(settings)
    assert [call.args[0] for call in fetch.call_args_list] == [
        "https://ai-agent.ideamake.cn/aidee-cli/stable/manifest.json",
        "https://ai-agent.ideamake.cn/aidee-cli/stable/manifest.sig",
    ]


def test_promoter_default_uses_authorized_release_prefix(monkeypatch):
    from test_promotion import promoter

    monkeypatch.delenv("OSS_RELEASE_PREFIX", raising=False)
    monkeypatch.setenv("OSS_BUCKET", "test-bucket")
    monkeypatch.setenv("AIDEE_RELEASE_PUBLIC_KEY_PEM", "FAKE_PUBLIC_KEY_FIXTURE")
    with (
        patch.object(promoter.serialization, "load_pem_public_key"),
        patch.object(promoter, "promote", return_value={}) as promote,
    ):
        promoter.main()
    assert promote.call_args.args[3] == "oss://test-bucket/aidee-cli"
