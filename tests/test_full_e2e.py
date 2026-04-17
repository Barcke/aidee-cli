"""E2E tests for AIDEE CLI. Require AIDEE service or skip."""

import json
import pytest
import os
import subprocess
import sys
from pathlib import Path


def _resolve_cli(name: str) -> list:
    """Resolve installed CLI; fallback to python -m for dev."""
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    # Fallback: python -m cli_anything.aidee
    module = "cli_anything.aidee.aidee_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    """Test CLI via subprocess."""

    CLI_BASE = _resolve_cli("cli-anything-aidee")

    def _run(self, args: list, check: bool = True, session_dir: Path | None = None):
        env = os.environ.copy()
        if session_dir is not None:
            env["AIDEE_SESSION_DIR"] = str(session_dir)
        else:
            # Use temp dir for tests that don't pass session_dir
            import tempfile
            env["AIDEE_SESSION_DIR"] = str(Path(tempfile.gettempdir()) / "cli_aidee_test")
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            env=env,
        )

    def test_help(self):
        """Test --help."""
        result = self._run(["--help"], session_dir=None)
        assert result.returncode == 0
        assert "AIDEE" in result.stdout or "aidee" in result.stdout

    def test_config_show_json(self, tmp_path):
        """Test config show --json."""
        session_dir = tmp_path / "session"
        result = self._run(["--json", "config", "show"], session_dir=session_dir)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "base_url" in data
        assert "token" in data

    def test_config_set_base_url(self, tmp_path):
        """Test config set-base-url (uses session file)."""
        session_dir = tmp_path / "session"
        result = self._run(
            ["--json", "config", "set-base-url", "http://localhost:8945/aidee-server"],
            session_dir=session_dir,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("base_url") == "http://localhost:8945/aidee-server"

    def test_recording_list_requires_service(self):
        """Test recording list — runs; may fail if service not running."""
        result = self._run(["--json", "recording", "list"], check=False)
        # If success, stdout is JSON; if fail, stderr has error
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert "code" in data or "data" in data or "message" in data
        else:
            # Connection/auth error expected when service down
            assert result.stderr or result.stdout


@pytest.mark.skipif(
    os.environ.get("AIDEE_E2E") != "1",
    reason="Set AIDEE_E2E=1 and AIDEE_TOKEN to run E2E against real service",
)
class TestE2ERealService:
    """E2E tests against running AIDEE service."""

    def test_user_info(self):
        """Test user info with real token."""
        token = os.environ.get("AIDEE_TOKEN")
        if not token:
            pytest.skip("AIDEE_TOKEN not set")
        result = subprocess.run(
            [sys.executable, "-m", "cli_anything.aidee.aidee_cli", "--json", "user", "info"],
            env={**os.environ, "AIDEE_TOKEN": token},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "code" in data or "data" in data
