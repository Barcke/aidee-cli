#!/usr/bin/env python3
"""Disposable signed install/update rehearsal. No production keys, endpoints or publication."""

import base64
import argparse
import sys
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from packaging.version import Version
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--manager", choices=("uv", "pipx"), default="uv")
manager = parser.parse_args().manager
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="aidee-release-rehearsal-") as task:
    task = Path(task)
    public = task / "public"
    public.mkdir()
    key = Ed25519PrivateKey.generate()
    pub = task / "test-public.pem"
    pub.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(public), **kwargs)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    env = {
        **os.environ,
        "UV_TOOL_DIR": str(task / "tools"),
        "UV_TOOL_BIN_DIR": str(task / "bin"),
        "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(task / "cache")),
        "AIDEE_RELEASE_BASE": base,
        "AIDEE_RELEASE_PUBLIC_KEY": str(pub),
        "AIDEE_CONFIG_DIR": str(task / "config"),
        "AIDEE_SKILLS_DIR": str(task / "skills"),
        "AIDEE_NO_UPDATE": "1",
        "AIDEE_KEYRING_DISABLED": "1",
    }
    for secret in ("AIDEE_API_KEY", "AIDEE_TOKEN", "PYTHONPATH"):
        env.pop(secret, None)

    if manager == "pipx":
        manager_env = {
            **env,
            "UV_TOOL_DIR": str(task / "manager-tools"),
            "UV_TOOL_BIN_DIR": str(task / "manager-bin"),
        }
        subprocess.run(
            ["uv", "tool", "install", "pipx==1.8.0"], env=manager_env, check=True
        )
        env.update(
            {
                "PATH": str(task / "manager-bin") + os.pathsep + env["PATH"],
                "PIPX_HOME": str(task / "pipx"),
                "PIPX_BIN_DIR": str(task / "bin"),
                "PIPX_DEFAULT_PYTHON": str(
                    task
                    / "manager-tools/pipx"
                    / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                ),
                "PIP_CONFIG_FILE": os.devnull,
                "PIP_NO_CACHE_DIR": "1",
            }
        )
        for build_setting in (
            "PIP_PLATFORM",
            "PIP_TARGET",
            "PIP_PYTHON_VERSION",
            "ARCHFLAGS",
            "_PYTHON_HOST_PLATFORM",
            "_PYTHON_SYSCONFIGDATA_NAME",
        ):
            env.pop(build_setting, None)
        managed_root = task / "pipx/venvs/cli-anything-aidee"
    else:
        managed_root = task / "tools/cli-anything-aidee"

    def manifest(version, wheel):
        artifact = {
            "filename": wheel.name,
            "url": base + "/" + wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "size": wheel.stat().st_size,
        }
        value = {
            "schemaVersion": 1,
            "version": version,
            "channel": "preview",
            "commit": "0" * 40,
            "pythonRequires": ">=3.10",
            "publishedAt": "2026-10-27T00:00:00Z",
            "releaseNotesUrl": "https://github.com/Barcke/aidee-cli/releases",
            "artifacts": [artifact],
        }
        raw = json.dumps(value, separators=(",", ":")).encode()
        channel = public / "preview"
        channel.mkdir(exist_ok=True)
        (channel / "manifest.json").write_bytes(raw)
        (channel / "manifest.sig").write_bytes(base64.b64encode(key.sign(raw)))
        immutable = public / "versions" / version
        immutable.mkdir(parents=True, exist_ok=True)
        (immutable / "manifest.json").write_bytes(raw)
        (immutable / "manifest.sig").write_bytes(base64.b64encode(key.sign(raw)))

    try:
        first = next((root / "dist").glob("*.whl"))
        current = Version(first.name.split("-")[1])
        first_version = str(current)
        next_version = f"{current.major}.{current.minor}.{current.micro + 1}"
        broken_version = f"{current.major}.{current.minor}.{current.micro + 2}"
        shutil.copy(first, public / first.name)
        manifest(first_version, public / first.name)
        subprocess.run(
            [
                sys.executable,
                str(root / "scripts/install.py"),
                "--base",
                base,
                "--channel",
                "preview",
                "--manager",
                manager,
                "--public-key-file",
                str(pub),
            ],
            check=True,
            env=env,
        )
        executable = managed_root / (
            "Scripts/aidee.exe" if os.name == "nt" else "bin/aidee"
        )
        subprocess.run(
            [str(executable), "update", "--check", "--channel", "preview"],
            check=True,
            env=env,
        )
        # Existing direct wheel installs have no official receipt. Explicit registration must
        # prove exact installed bytes against the signed immutable current-version manifest.
        (managed_root / ".aidee-install.json").unlink()
        registered = subprocess.check_output(
            [
                str(executable),
                "update",
                "--register-manager",
                manager,
                "--channel",
                "preview",
                "--sync-skills",
            ],
            env=env,
            text=True,
            encoding="utf-8",
        )
        registered = json.loads(registered)["data"]
        assert registered["registration"]["sourceVerified"] is True
        assert registered["skillsSync"]["status"] == "ok"
        skill = task / "skills/aidee-user/SKILL.md"
        skill.write_text("rehearsal local edit 中文🙂", encoding="utf-8")
        second = task / "second"
        second.mkdir()
        shutil.copy(root / "pyproject.toml", second / "pyproject.toml")
        shutil.copy(root / "README.md", second / "README.md")
        shutil.copytree(
            root / "src",
            second / "src",
            ignore=shutil.ignore_patterns("*.egg-info", "__pycache__"),
        )
        config = second / "pyproject.toml"
        config.write_text(
            config.read_text().replace(
                f'version = "{first_version}"', f'version = "{next_version}"'
            )
        )
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(task / "second-dist")],
            cwd=second,
            check=True,
            env=env,
            capture_output=True,
        )
        new = next((task / "second-dist").glob("*.whl"))
        shutil.copy(new, public / new.name)
        manifest(next_version, public / new.name)
        # Exercise a real uv reinstall and version validation using only disposable tool directories.
        subprocess.run(
            [str(executable), "update", "--channel", "preview", "--sync-skills"],
            check=True,
            env=env,
        )
        checked = subprocess.check_output(
            [str(executable), "--version"], env=env, text=True, encoding="utf-8"
        )
        assert next_version in checked
        assert "rehearsal local edit 中文🙂" in (
            skill.parent / "SKILL.md.pre-aidee"
        ).read_text(encoding="utf-8")
        # A correctly signed but unhealthy build must be restored by the same real manager.
        config.write_text(
            config.read_text().replace(
                f'version = "{next_version}"', f'version = "{broken_version}"'
            )
        )
        (second / "src/cli_anything/aidee/__main__.py").write_text(
            "raise SystemExit(19)\n"
        )
        shutil.rmtree(second / "build", ignore_errors=True)
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(task / "broken-dist")],
            cwd=second,
            check=True,
            env=env,
            capture_output=True,
        )
        broken = next((task / "broken-dist").glob("*.whl"))
        shutil.copy(broken, public / broken.name)
        manifest(broken_version, public / broken.name)
        rejected = subprocess.run(
            [str(executable), "update", "--channel", "preview"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        assert rejected.returncode == 7, rejected.stdout + rejected.stderr
        assert json.loads(rejected.stdout)["meta"]["rolledBack"] is True
        checked = subprocess.check_output(
            [str(executable), "--version"], env=env, text=True, encoding="utf-8"
        )
        assert next_version in checked
        print(
            f"Signed install -> explicit {manager} source registration -> Skills sync -> real {manager} update -> unhealthy signed build rejected -> real {manager} rollback to {next_version} verified; disposable environment removed"
        )
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
