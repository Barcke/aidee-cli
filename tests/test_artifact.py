"""Run this wheel in an isolated environment against the same loopback fixture."""

import json
import os
from pathlib import Path
import subprocess
import venv
import shutil
import pytest
from test_full_e2e import server  # noqa: F401, F811


def test_current_wheel_console_entries_and_http_contract(tmp_path, server):  # noqa: F811
    wheel_dir = Path(__file__).resolve().parents[1] / "dist"
    wheels = list(wheel_dir.glob("*.whl"))
    if not wheels:
        pytest.skip("Build the current wheel before artifact acceptance")
    assert len(wheels) == 1
    environment = tmp_path / "venv"
    venv.EnvBuilder(
        with_pip=False, system_site_packages=False, symlinks=os.name != "nt"
    ).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    installed = subprocess.run(
        [
            shutil.which("uv") or "uv",
            "pip",
            "install",
            "--python",
            str(python),
            str(wheels[0]),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    base, calls = server
    env = {
        **os.environ,
        "AIDEE_CONFIG_DIR": str(tmp_path / "config"),
        "AIDEE_BASE_URL": base,
        "AIDEE_TEAM_BASE_URL": base,
        "AIDEE_API_KEY": "aidee_artifact_test",
        "AIDEE_KEYRING_DISABLED": "1",
        "AIDEE_NO_UPDATE": "1",
    }
    env.pop("PYTHONPATH", None)
    env.pop("AIDEE_TOKEN", None)

    def execute(*args):
        return subprocess.run(
            [str(python), "-m", "cli_anything.aidee", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=tmp_path,
            timeout=15,
        )

    version = execute("--version")
    assert version.returncode == 0 and wheels[0].name.split("-")[1] in version.stdout
    result = execute("recording", "list", "--all", "--limit", "1")
    assert result.returncode == 0, result.stderr
    assert len(json.loads(result.stdout)["data"]) == 2
    result = execute("membership", "checkout", "--plan", "p1", "--yes")
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["orderNo"] == "o1" and "购买确认" in result.stderr
    for name in ("aidee", "cli-anything-aidee"):
        executable = environment / (
            "Scripts/" + name + ".exe" if os.name == "nt" else "bin/" + name
        )
        help_result = subprocess.run(
            [str(executable), "schema"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=tmp_path,
            timeout=15,
        )
        assert help_result.returncode == 0 and json.loads(help_result.stdout)["ok"]
    where = subprocess.run(
        [
            str(python),
            "-c",
            "import cli_anything.aidee;print(cli_anything.aidee.__file__)",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=tmp_path,
        check=True,
    )
    assert str(environment) in where.stdout
