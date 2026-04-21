"""Unit tests for AIDEE CLI core modules."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Use tmp dir for session in tests
SESSION_DIR = Path(tempfile.gettempdir()) / "cli_anything_aidee_test"
SESSION_FILE = SESSION_DIR / "session.json"


@pytest.fixture(autouse=True)
def mock_session_path(monkeypatch):
    """Use temp dir for session in tests."""
    import cli_anything.aidee.core.session as session_mod
    monkeypatch.setattr(session_mod, "SESSION_DIR", SESSION_DIR)
    monkeypatch.setattr(session_mod, "SESSION_FILE", SESSION_FILE)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
    yield
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def test_load_session_empty():
    """No file returns {}."""
    from cli_anything.aidee.core.session import load_session
    assert load_session() == {}


def test_save_and_load_session():
    """Save base_url, token, api_key; load matches."""
    from cli_anything.aidee.core.session import load_session, save_session
    save_session(base_url="http://test:8080", token="abc123", api_key="aidee_key_1234")
    sess = load_session()
    assert sess["base_url"] == "http://test:8080"
    assert sess["token"] == "abc123"
    assert sess["api_key"] == "aidee_key_1234"


def test_clear_session():
    """Clear removes file."""
    from cli_anything.aidee.core.session import save_session, clear_session, load_session
    save_session(base_url="http://x")
    assert SESSION_FILE.exists()
    clear_session()
    assert not SESSION_FILE.exists()
    assert load_session() == {}


def test_get_base_url_default():
    """Returns default when empty."""
    from cli_anything.aidee.core.session import get_base_url
    with patch.dict(os.environ, {}, clear=False):
        assert get_base_url() == "https://api.aidee.me/aidee-server"


def test_get_token_default():
    """Returns None when empty."""
    from cli_anything.aidee.core.session import get_token
    with patch.dict(os.environ, {"AIDEE_TOKEN": ""}, clear=False):
        pass
    # Without token in session or env
    assert get_token() is None or get_token() == ""


def test_get_api_key_default():
    """Returns None when API key is empty."""
    from cli_anything.aidee.core.session import get_api_key
    with patch.dict(os.environ, {"AIDEE_API_KEY": ""}, clear=False):
        pass
    assert get_api_key() is None or get_api_key() == ""


def test_set_base_url():
    """Config set_base_url persists."""
    from cli_anything.aidee.core.config import set_base_url
    r = set_base_url("http://test:9000")
    assert r["base_url"] == "http://test:9000"
    assert r["status"] == "ok"


def test_set_token():
    """Config set_token persists."""
    from cli_anything.aidee.core.config import set_token
    r = set_token("secret")
    assert r["status"] == "ok"


def test_set_api_key():
    """Config set_api_key persists."""
    from cli_anything.aidee.core.config import set_api_key
    r = set_api_key("aidee_secret")
    assert r["status"] == "ok"


def test_show():
    """Config show returns dict."""
    from cli_anything.aidee.core.config import show, set_api_key, set_base_url
    set_base_url("http://test:8000")
    set_api_key("aidee_key_1234")
    r = show()
    assert "base_url" in r
    assert "token" in r
    assert "api_key" in r
    assert "session_file" in r


def test_recording_create_calls_api():
    """Recording create calls POST /recordings."""
    from cli_anything.aidee.core.recording import create
    with patch("cli_anything.aidee.core.recording.api_request") as m:
        m.return_value = {"code": 200, "data": {"code": "r1"}}
        r = create("http://x", "tok", title="Test")
        m.assert_called_once()
        call = m.call_args
        assert call[0][0] == "POST"
        assert "/recordings" in call[0][1]
        assert call[1]["json_body"]["title"] == "Test"


def test_recording_get_calls_api():
    """Recording get calls GET /recordings/{code}."""
    from cli_anything.aidee.core.recording import get
    with patch("cli_anything.aidee.core.recording.api_request") as m:
        m.return_value = {"code": 200, "data": {}}
        get("http://x", "tok", "RC001")
        m.assert_called_once()
        assert m.call_args[0][:4] == ("GET", "/recordings/RC001", "http://x", "tok")


def test_recording_list_calls_api():
    """Recording list calls GET /recordings with params."""
    from cli_anything.aidee.core.recording import list_recordings
    with patch("cli_anything.aidee.core.recording.api_request") as m:
        m.return_value = {"code": 200, "data": []}
        list_recordings("http://x", "tok", page=2, size=10)
        m.assert_called_once()
        call = m.call_args
        assert call[1]["params"]["page"] == 2
        assert call[1]["params"]["size"] == 10


def test_api_request_sends_api_key_header():
    """API key is sent as X-Api-Key when configured via env."""
    from cli_anything.aidee.utils.aidee_backend import api_request

    class _Response:
        content = b'{"code":200}'
        text = '{"code":200}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 200}

    with patch.dict(os.environ, {"AIDEE_API_KEY": "aidee_test_key"}, clear=False):
        with patch("cli_anything.aidee.utils.aidee_backend.requests.request", return_value=_Response()) as m:
            r = api_request("GET", "/users/information", "http://x", token="tok")
            assert r["code"] == 200
            headers = m.call_args.kwargs["headers"]
            assert headers["IM-TOKEN"] == "tok"
            assert headers["X-Api-Key"] == "aidee_test_key"


def test_print_result_json_mode():
    """JSON 模式输出为合法 JSON 文本。"""
    from cli_anything.aidee.utils.output import dumps_json
    s = dumps_json({"a": 1, "b": "中文"})
    assert "中文" in s
    assert '"a"' in s
