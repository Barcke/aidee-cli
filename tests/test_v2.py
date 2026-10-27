"""Safety and engineering contracts independent of service reachability."""

import base64
import json
import os
from pathlib import Path
import sys
import subprocess
from unittest.mock import patch, Mock
import pytest
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cli_anything.aidee.aidee_cli import cli
from cli_anything.aidee import __version__
from cli_anything.aidee.errors import CLIError
from cli_anything.aidee.output import normalize
from cli_anything.aidee.settings import (
    Settings,
    credentials_set,
    credentials_delete,
    directory,
    atomic_json,
)
from cli_anything.aidee.client import Client, pages
from cli_anything.aidee.updates import verify_manifest, update_lock


@pytest.mark.parametrize(
    "key", ["id", "keyId", "cursorId", "nextCursorId", "priceMinor"]
)
def test_snowflake_id_is_exact(key):
    assert normalize({key: 2102281458272997376})[key] == "2102281458272997376"


def test_booleans_and_counters_are_not_stringified():
    assert normalize({"hasMore": True, "total": 20, "size": 20}) == {
        "hasMore": True,
        "total": 20,
        "size": 20,
    }


def test_credentials_file_permissions_and_origin_binding(tmp_path):
    settings = Settings()
    assert credentials_set(settings, "aidee_test") == "file"
    assert settings.credential() == "aidee_test"
    if os.name != "nt":
        assert (directory() / "credentials.json").stat().st_mode & 0o777 == 0o600
    settings.values["team_base"] = "https://other.example"
    with pytest.raises(CLIError) as error:
        settings.credential()
    assert error.value.exit_code == 3
    credentials_delete(settings.name)
    assert not Settings().credential()


def test_env_wins_selected_profile_without_mutating_process(monkeypatch):
    settings = Settings("test")
    credentials_set(settings, "aidee_stored")
    monkeypatch.setenv("AIDEE_API_KEY", "aidee_env")
    assert settings.credential() == "aidee_env"
    assert Settings(api_key="aidee_explicit").credential() == "aidee_explicit"
    assert os.environ["AIDEE_API_KEY"] == "aidee_env"


@pytest.mark.parametrize(
    "url",
    [
        "http://public.example",
        "https://user:secret@example.com",
        "https://example.com?key=x",
        "file:///tmp/secret",
    ],
)
def test_invalid_origins_rejected(url):
    with pytest.raises(CLIError):
        Settings(api_base=url)


def test_token_mode_never_sends_api_key(monkeypatch):
    monkeypatch.setenv("AIDEE_API_KEY", "aidee_env")
    settings = Settings(auth_mode="token", token="explicit-token")
    response = Mock(status_code=200, content=b"{}")
    response.json.return_value = {"code": 200, "data": {}}
    with patch(
        "cli_anything.aidee.client.requests.request", return_value=response
    ) as request:
        Client(settings).request("GET", "/users/information")
        assert request.call_args.kwargs["headers"]["IM-TOKEN"] == "explicit-token"
        assert "X-Api-Key" not in request.call_args.kwargs["headers"]


def test_authenticated_redirects_never_follow():
    response = Mock(status_code=302)
    with patch(
        "cli_anything.aidee.client.requests.request", return_value=response
    ) as request:
        with pytest.raises(CLIError):
            Client(Settings(), "aidee_test").request("GET", "/users/information")
        assert request.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "status,code,exit_code",
    [
        (200, 1003, 3),
        (200, 1004, 4),
        (200, 1005, 4),
        (200, 4030, 4),
        (200, 4031, 4),
        (200, 4032, 4),
        (200, 4033, 4),
        (200, 4290, 6),
        (200, 4291, 6),
        (200, 4292, 6),
        (200, 4293, 6),
        (200, 4299, 6),
        (404, 404, 5),
        (500, 500, 6),
        (200, 8123, 5),
    ],
)
def test_explicit_business_failure_mapping(status, code, exit_code):
    response = Mock(status_code=status, content=b"{}", headers={})
    response.json.return_value = {"code": code, "msg": "test failure", "data": None}
    with (
        patch("cli_anything.aidee.client.requests.request", return_value=response),
        patch("cli_anything.aidee.client.time.sleep"),
    ):
        with pytest.raises(CLIError) as error:
            Client(Settings(), "aidee_test").request("GET", "/users/information")
        assert error.value.exit_code == exit_code


def test_write_network_failure_is_not_retried():
    import requests

    with patch(
        "cli_anything.aidee.client.requests.request", side_effect=requests.Timeout
    ) as request:
        with pytest.raises(CLIError):
            Client(Settings(), "aidee_test").request(
                "POST", "/memberships/checkout", body={}
            )
        assert request.call_count == 1


def test_paging_limit_reports_resume_and_truncation():
    calls = []

    def fetch(query, deadline):
        calls.append(query)
        return {"records": [{"id": 1}], "current": query["page"], "size": 1, "total": 3}

    rows, meta = pages(fetch, {"page": 1, "limit": 1}, all_pages=True, max_pages=2)
    assert len(rows) == 2 and meta["truncated"] and meta["next"]["page"] == 3


def test_paging_error_is_partial_not_success():
    def fetch(query, deadline):
        if query["page"] == 2:
            raise CLIError("NETWORK_ERROR", "offline", 6)
        return {"records": [{"id": 1}], "current": 1, "size": 1, "total": 3}

    with pytest.raises(CLIError) as error:
        pages(fetch, {"page": 1, "limit": 1}, all_pages=True)
    assert error.value.meta["partial"]["pages"] == 1


def test_cursor_must_advance():
    def fetch(query, deadline):
        return {
            "records": [{"id": 1}],
            "hasMore": True,
            "nextCursorId": 1,
            "nextCursorSortTime": "2026-01-01T00:00:00",
        }

    with pytest.raises(CLIError):
        pages(fetch, {"cursor": True}, cursor=True, all_pages=True)


def test_invalid_jq_is_nonzero():
    result = CliRunner().invoke(cli, ["--jq", ".[", "config", "show"])
    assert (
        result.exit_code == 2
        and json.loads(result.stdout)["error"]["code"] == "QUERY_FAILED"
    )


def test_schema_has_only_approved_operations():
    result = CliRunner().invoke(cli, ["schema"])
    data = json.loads(result.stdout)["data"]
    assert any(row["id"] == "membership.checkout" for row in data)
    assert all(
        row["path"]
        not in ("/recordings/redemption/codes", "/recordings/redemption/redeem-by-user")
        for row in data
    )
    assert not any("/ops/" in row["path"] for row in data)


def fixture_manifest(key, version="2.1.0", channel="stable"):
    name = f"cli_anything_aidee-{version}-py3-none-any.whl"
    value = {
        "schemaVersion": 1,
        "version": version,
        "channel": channel,
        "commit": "a" * 40,
        "pythonRequires": ">=3.10",
        "publishedAt": "2026-10-27T00:00:00Z",
        "releaseNotesUrl": "https://github.com/Barcke/aidee-cli/releases/tag/v"
        + version,
        "artifacts": [
            {
                "filename": name,
                "url": "https://download.example/" + name,
                "sha256": "a" * 64,
                "size": 20,
            }
        ],
    }
    raw = json.dumps(value).encode()
    return raw, base64.b64encode(key.sign(raw))


def test_manifest_signature_verifies_original_bytes():
    private = Ed25519PrivateKey.generate()
    raw, sig = fixture_manifest(private)
    assert verify_manifest(raw, sig, private.public_key())["version"] == "2.1.0"
    with pytest.raises(CLIError):
        verify_manifest(raw + b" ", sig, private.public_key())
    with pytest.raises(CLIError):
        verify_manifest(raw, sig, Ed25519PrivateKey.generate().public_key())


@pytest.mark.parametrize(
    "field,value",
    [("channel", "other"), ("schemaVersion", 2), ("pythonRequires", ">99")],
)
def test_signed_but_invalid_manifest_rejected(field, value):
    key = Ed25519PrivateKey.generate()
    raw, _ = fixture_manifest(key)
    data = json.loads(raw)
    data[field] = value
    raw = json.dumps(data).encode()
    with pytest.raises(CLIError):
        verify_manifest(raw, base64.b64encode(key.sign(raw)), key.public_key())


def test_update_lock_is_exclusive():
    with update_lock():
        with pytest.raises(CLIError):
            with update_lock():
                pass
    assert not (directory() / "update.lock").exists()


def test_skills_sync_never_touches_other_products(tmp_path):
    from cli_anything.aidee.skills import sync

    other = tmp_path / "aidee-ops" / "SKILL.md"
    other.parent.mkdir()
    other.write_text("keep")
    local = tmp_path / "aidee-user" / "SKILL.md"
    local.parent.mkdir()
    local.write_text("my edit")
    report = sync(tmp_path)
    assert report["backedUp"] == ["aidee-user"] and other.read_text() == "keep"
    assert Path(str(local) + ".pre-aidee").read_text() == "my edit"


def test_auto_update_disabled_in_noninteractive_and_explicit_json(monkeypatch):
    from cli_anything.aidee import updates

    settings = Settings()
    settings.profile["update.auto"] = True
    monkeypatch.delenv("AIDEE_NO_UPDATE")
    with patch.object(updates, "check_update") as check:
        assert updates.startup_check(settings) is None
        check.assert_not_called()


def test_unknown_install_origin_never_invokes_manager():
    from cli_anything.aidee.updates import installation

    with pytest.raises(CLIError):
        installation()


def test_checked_manifest_never_downgrades(monkeypatch):
    from cli_anything.aidee import updates

    private = Ed25519PrivateKey.generate()
    raw, sig = fixture_manifest(private, version="1.0.0")
    with (
        patch.object(updates, "public_key", return_value=private.public_key()),
        patch.object(updates, "fetch", side_effect=[raw, sig]),
    ):
        assert updates.check_update(Settings())["updateAvailable"] is False


def test_invalid_wheel_hash_fails_before_manager(tmp_path):
    from cli_anything.aidee import updates

    with patch.object(updates, "fetch", return_value=b"wrong"):
        with pytest.raises(CLIError):
            updates.verified_wheel(
                {
                    "url": "https://example.com/w.whl",
                    "size": 5,
                    "sha256": "0" * 64,
                    "filename": "w.whl",
                },
                tmp_path,
            )


def test_update_uses_original_manager_and_restores_failed_upgrade(
    tmp_path, monkeypatch
):
    from cli_anything.aidee import updates

    old = {
        "filename": "old.whl",
        "url": "https://example.com/old.whl",
        "sha256": "0" * 64,
        "size": 3,
    }
    receipt = {
        "manager": "uv",
        "version": __version__,
        "artifact": old,
        "environment": str(tmp_path),
        "distribution": "cli-anything-aidee",
    }
    new = {
        "updateAvailable": True,
        "version": "2.1.0",
        "commit": "a" * 40,
        "channel": "stable",
        "artifacts": [{**old, "filename": "new.whl"}],
    }
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    completed = [
        Mock(returncode=1),
        Mock(returncode=0),
        Mock(returncode=0, stdout=f"aidee, version {__version__}"),
    ]
    with (
        patch.object(updates, "installation", return_value=(receipt, "/known/uv")),
        patch.object(
            updates, "verified_wheel", side_effect=lambda a, t: Path(t) / a["filename"]
        ),
        patch.object(updates.subprocess, "run", side_effect=completed) as run,
    ):
        with pytest.raises(CLIError) as error:
            updates.install_update(Settings(), new)
    assert error.value.meta["rolledBack"] is True
    assert run.call_args_list[0].args[0][:4] == [
        "/known/uv",
        "tool",
        "install",
        "--force",
    ]
    assert "old.whl" in " ".join(run.call_args_list[1].args[0])


def test_update_success_writes_verified_receipt(tmp_path, monkeypatch):
    from cli_anything.aidee import updates

    old = {
        "filename": "old.whl",
        "url": "https://example.com/old.whl",
        "sha256": "0" * 64,
        "size": 3,
    }
    receipt = {
        "manager": "pipx",
        "version": __version__,
        "artifact": old,
        "environment": str(tmp_path),
        "distribution": "cli-anything-aidee",
    }
    new = {
        "updateAvailable": True,
        "version": "2.1.0",
        "commit": "a" * 40,
        "channel": "stable",
        "artifacts": [{**old, "filename": "new.whl"}],
    }
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    with (
        patch.object(updates, "installation", return_value=(receipt, "/known/pipx")),
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
        assert updates.install_update(Settings(), new)["updated"] is True
    saved = json.loads((tmp_path / ".aidee-install.json").read_text())
    assert saved["version"] == "2.1.0" and saved["artifact"]["filename"] == "new.whl"
    assert run.call_args_list[0].args[0][0:3] == ["/known/pipx", "install", "--force"]


def test_auto_update_is_opt_in_and_skips_current_business(monkeypatch):
    from cli_anything.aidee import updates

    settings = Settings()
    settings.profile["update.auto"] = True
    monkeypatch.delenv("AIDEE_NO_UPDATE")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with (
        patch.object(
            updates,
            "check_update",
            return_value={"version": "2.1.0", "updateAvailable": True},
        ),
        patch.object(
            updates, "install_update", return_value={"updated": True}
        ) as install,
    ):
        assert updates.startup_check(settings) == {"updated": True}
        install.assert_called_once()


def test_auto_update_does_not_replace_in_explicit_json_mode(monkeypatch):
    from cli_anything.aidee import updates

    settings = Settings()
    settings.profile["update.auto"] = True
    monkeypatch.delenv("AIDEE_NO_UPDATE")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with (
        patch.object(
            updates,
            "check_update",
            return_value={"version": "2.1.0", "updateAvailable": True},
        ),
        patch.object(updates, "install_update") as install,
    ):
        assert updates.startup_check(settings, explicit_json=True) is None
        install.assert_not_called()


def test_manager_timeout_after_partial_install_still_restores(tmp_path, monkeypatch):
    from cli_anything.aidee import updates

    old = {
        "filename": "old.whl",
        "url": "https://example.com/old.whl",
        "sha256": "0" * 64,
        "size": 3,
    }
    receipt = {
        "manager": "uv",
        "version": __version__,
        "artifact": old,
        "environment": str(tmp_path),
        "distribution": "cli-anything-aidee",
    }
    new = {
        "updateAvailable": True,
        "version": "2.1.0",
        "commit": "a" * 40,
        "channel": "stable",
        "artifacts": [{**old, "filename": "new.whl"}],
    }
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    outcome = [
        subprocess.TimeoutExpired("uv", 180),
        Mock(returncode=0),
        Mock(returncode=0, stdout=f"aidee, version {__version__}"),
    ]
    with (
        patch.object(updates, "installation", return_value=(receipt, "/known/uv")),
        patch.object(
            updates, "verified_wheel", side_effect=lambda a, t: Path(t) / a["filename"]
        ),
        patch.object(updates.subprocess, "run", side_effect=outcome) as run,
    ):
        with pytest.raises(CLIError) as error:
            updates.install_update(Settings(), new)
    assert error.value.meta["rolledBack"] is True
    assert run.call_count == 3


def test_auto_attempt_failure_cannot_fall_through_to_business(monkeypatch):
    from cli_anything.aidee import updates

    settings = Settings()
    settings.profile["update.auto"] = True
    monkeypatch.delenv("AIDEE_NO_UPDATE")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with (
        patch.object(
            updates,
            "check_update",
            return_value={"version": "2.1.0", "updateAvailable": True},
        ),
        patch.object(
            updates,
            "install_update",
            side_effect=CLIError("UPDATE_FAILED", "failure", 7),
        ),
    ):
        with pytest.raises(CLIError):
            updates.startup_check(settings)


def test_keyring_authority_never_falls_back_to_old_file(monkeypatch):
    from cli_anything.aidee import settings as module

    state = {}
    ring = Mock()
    ring.set_password.side_effect = lambda service, name, value: state.update(
        {name: value}
    )
    ring.get_password.side_effect = lambda service, name: state.get(name)
    config = Settings()
    with patch.object(module, "_keyring", return_value=None):
        credentials_set(config, "aidee_old_A")
    with patch.object(module, "_keyring", return_value=ring):
        credentials_set(config, "aidee_new_B")
    ring.get_password.side_effect = RuntimeError("locked")
    with patch.object(module, "_keyring", return_value=ring):
        with pytest.raises(CLIError):
            module.credentials_get(config.name)
    with patch.object(module, "_keyring", return_value=None):
        with pytest.raises(CLIError):
            module.credentials_get(config.name)


def test_file_authority_never_reverts_to_stale_keyring():
    from cli_anything.aidee import settings as module

    state = {}
    ring = Mock()
    ring.set_password.side_effect = lambda service, name, value: state.update(
        {name: value}
    )
    ring.get_password.side_effect = lambda service, name: state.get(name)
    config = Settings()
    with patch.object(module, "_keyring", return_value=ring):
        credentials_set(config, "aidee_old_A")
    ring.set_password.side_effect = RuntimeError("locked")
    with patch.object(module, "_keyring", return_value=ring):
        credentials_set(config, "aidee_new_B")
        assert module.credentials_get(config.name)["secret"] == "aidee_new_B"
        ring.get_password.assert_not_called()


def test_failed_keyring_delete_cannot_resurrect_logout():
    from cli_anything.aidee import settings as module

    state = {}
    ring = Mock()
    ring.set_password.side_effect = lambda service, name, value: state.update(
        {name: value}
    )
    ring.get_password.side_effect = lambda service, name: state.get(name)
    ring.delete_password.side_effect = RuntimeError("locked")
    config = Settings()
    with patch.object(module, "_keyring", return_value=ring):
        credentials_set(config, "aidee_account_A")
        assert credentials_delete(config.name)["credentialCleanupPending"] is True
        assert module.credentials_get(config.name) is None
        assert state[
            config.name
        ]  # The stale ring value still exists but is no longer authoritative.


@pytest.mark.parametrize(
    "value,zone,expected",
    [
        ("2026-10-27T00:00:00-04:00", "America/New_York", "2026-10-27T12:00:00"),
        ("2026-10-27T00:00:00", "Asia/Taipei", "2026-10-27T00:00:00"),
        ("2026-11-01T01:30:00-04:00", "America/New_York", "2026-11-01T13:30:00"),
        ("2026-11-01T01:30:00-05:00", "America/New_York", "2026-11-01T14:30:00"),
        ("2026-10-27T00:00:00Z", "UTC", "2026-10-27T08:00:00"),
    ],
)
def test_time_filters_convert_to_api_wall_clock(value, zone, expected):
    result = CliRunner().invoke(
        cli, ["recording", "list", "--from", value, "--timezone", zone, "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["params"]["startTime"] == expected


def test_no_key_authority_marker_means_no_implicit_legacy_login():
    atomic_json(
        directory() / "credentials.json", {"default": {"secret": "aidee_stale"}}
    )
    assert Settings().credential() is None


@pytest.mark.parametrize(
    "bad_metadata",
    [None, {}, [], {"userCenterUserId": None}, {"userCenterUserId": 123}],
)
def test_login_never_stores_key_on_200_without_real_identity(bad_metadata):
    with patch("cli_anything.aidee.client.Client.request", return_value=bad_metadata):
        result = CliRunner().invoke(cli, ["auth", "login", "--key", "aidee_fake"])
    assert result.exit_code == 3, result.output
    assert Settings().credential() is None


@pytest.mark.parametrize("mode", ["table", "markdown"])
def test_readable_output_escapes_terminal_controls_in_titles_and_column_names(
    mode, capsys
):
    from cli_anything.aidee.output import emit

    title = "会议\x1b]52;c;clipboard\x07\x1b[31m红色\x9b2J\x85下一行"
    column = "标\x1b[2J题\x9d52;c;bad\x07|列"
    original = {"ok": True, "data": [{column: title}]}
    emit(original, mode=mode)
    displayed = capsys.readouterr().out
    assert not any(
        ord(char) < 32 and char != "\n" or 127 <= ord(char) <= 159 for char in displayed
    )
    assert "\\x1b" in displayed and "\\x9b" in displayed and "\\x9d" in displayed
    assert "\\|列" in displayed
    assert original["data"][0][column] == title
    emit(original, mode="json")
    assert json.loads(capsys.readouterr().out) == original


@pytest.mark.parametrize("mode", ["table", "markdown"])
def test_readable_scalar_and_metadata_cannot_emit_c1_controls(mode, capsys):
    from cli_anything.aidee.output import emit

    emit({"ok": True, "data": "标题\x9b2J\x1b]52;c;x\x07"}, mode=mode)
    assert "\x9b" not in capsys.readouterr().out
    emit(
        {"ok": True, "data": [{"title": "安全"}], "meta": {"hint": "\x9d52;c;x\x07"}},
        mode=mode,
    )
    assert "\x9d" not in capsys.readouterr().out


def test_export_is_utf8_and_lf_even_with_non_utf8_windows_defaults(
    tmp_path, monkeypatch
):
    from cli_anything.aidee import export

    original_fdopen = os.fdopen
    calls = []

    def windows_locale_fdopen(fd, mode, **kwargs):
        calls.append(dict(kwargs))
        kwargs.setdefault("encoding", "cp1252")
        kwargs.setdefault("newline", "\r\n")
        return original_fdopen(fd, mode, **kwargs)

    monkeypatch.setattr(export.os, "fdopen", windows_locale_fdopen)
    source = "中文与emoji🙂\n原文\x1b[31m\x9b2J\n"
    target = tmp_path / "recording.txt"
    result = export.write(source, target)
    assert target.read_bytes() == source.encode("utf-8")
    assert result["bytes"] == len(target.read_bytes())
    assert calls == [{"encoding": "utf-8", "newline": "\n"}]
    assert export.render([{"text": source}], "txt") == source + "\n"
