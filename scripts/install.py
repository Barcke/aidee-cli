#!/usr/bin/env python3
"""Verify a release before invoking an installed tool manager; no business credentials."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packaging.version import Version
from packaging.specifiers import SpecifierSet

PUBLIC_KEY_PEM = "UNCONFIGURED"
DEFAULT_BASE = "https://ai-agent.ideamake.cn/aidee-cli"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def download(url, maximum):
    parsed = urlsplit(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")
    ):
        raise ValueError("HTTPS required")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Invalid download URL")
    with build_opener(NoRedirect).open(Request(url), timeout=30) as response:
        data = response.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("Oversized download")
        return data


def main():
    parser = argparse.ArgumentParser(
        description="Install signed Aidee wheel into uv tool or pipx"
    )
    parser.add_argument(
        "--base", default=os.environ.get("AIDEE_RELEASE_BASE", DEFAULT_BASE)
    )
    parser.add_argument("--channel", choices=("stable", "preview"), default="stable")
    parser.add_argument("--manager", choices=("uv", "pipx"), default="uv")
    parser.add_argument(
        "--public-key-file", help="Explicitly trust the specified release public key"
    )
    parser.add_argument(
        "--sync-skills",
        action="store_true",
        help="Explicitly sync this CLI skill after installation",
    )
    args = parser.parse_args()
    raw = download(
        args.base.rstrip("/") + "/" + args.channel + "/manifest.json", 256 * 1024
    )
    sig = download(args.base.rstrip("/") + "/" + args.channel + "/manifest.sig", 2048)
    keydata = (
        Path(args.public_key_file).read_bytes()
        if args.public_key_file
        else PUBLIC_KEY_PEM.encode()
    )
    key = serialization.load_pem_public_key(keydata)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Ed25519 trust key required")
    key.verify(base64.b64decode(sig, validate=True), raw)
    manifest = json.loads(raw)
    version = Version(manifest["version"])
    if (
        manifest["schemaVersion"] != 1
        or manifest["channel"] != args.channel
        or (args.channel == "stable" and version.is_prerelease)
    ):
        raise ValueError("Invalid manifest channel")
    if not SpecifierSet(manifest["pythonRequires"]).contains(
        ".".join(map(str, sys.version_info[:3]))
    ):
        raise ValueError("Unsupported Python")
    if len(manifest["artifacts"]) != 1:
        raise ValueError("Expected one universal wheel")
    artifact = manifest["artifacts"][0]
    name = artifact["filename"]
    if (
        Path(name).name != name
        or name != f"cli_anything_aidee-{version}-py3-none-any.whl"
    ):
        raise ValueError("Invalid wheel name")
    if (
        not isinstance(artifact["size"], int)
        or not 0 < artifact["size"] <= 64 * 1024 * 1024
    ):
        raise ValueError("Invalid artifact size")
    binary = shutil.which(args.manager)
    if not binary:
        raise ValueError("Install uv or pipx before installing Aidee")
    data = download(artifact["url"], 64 * 1024 * 1024)
    if (
        len(data) != artifact["size"]
        or hashlib.sha256(data).hexdigest() != artifact["sha256"]
    ):
        raise ValueError("Wheel integrity mismatch")
    with tempfile.TemporaryDirectory(prefix="aidee-install-") as temp:
        wheel = Path(temp) / name
        wheel.write_bytes(data)
        # Do not force-overwrite an existing tool; update uses its registered manager.
        command = (
            [binary, "tool", "install", "--from", str(wheel), "cli-anything-aidee"]
            if args.manager == "uv"
            else [binary, "install", str(wheel)]
        )
        subprocess.run(command, check=True)
    if args.manager == "uv":
        root = (
            Path(subprocess.check_output([binary, "tool", "dir"], text=True).strip())
            / "cli-anything-aidee"
        )
    else:
        listing = json.loads(
            subprocess.check_output([binary, "list", "--json"], text=True)
        )
        entry = listing["venvs"]["cli-anything-aidee"]
        if entry["metadata"]["main_package"]["package_version"] != str(version):
            raise ValueError("Installed version mismatch")
        home = subprocess.check_output(
            [binary, "environment", "--value", "PIPX_LOCAL_VENVS"], text=True
        ).strip()
        root = Path(home) / "cli-anything-aidee"
    python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    result = subprocess.check_output(
        [
            str(python),
            "-c",
            "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey;import sys,runpy;sys.argv=['aidee','--version'];runpy.run_module('cli_anything.aidee',run_name='__main__')",
        ],
        text=True,
    )
    if not result.strip().endswith("version " + str(version)):
        raise ValueError("Installed executable version mismatch")
    receipt = {
        "manager": args.manager,
        "environment": str(root.resolve()),
        "distribution": "cli-anything-aidee",
        "version": str(version),
        "commit": manifest["commit"],
        "channel": args.channel,
        "artifact": artifact,
        "installedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = root / ".aidee-install.json"
    path.write_text(json.dumps(receipt, indent=2))
    path.chmod(0o600)
    skills_result = {"status": "not_requested", "hint": "aidee skills sync"}
    if args.sync_skills:
        try:
            synced = subprocess.run(
                [str(python), "-m", "cli_anything.aidee", "skills", "sync"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                env={**os.environ, "AIDEE_NO_UPDATE": "1"},
            )
            response = json.loads(synced.stdout) if synced.returncode == 0 else {}
            skills_result = (
                {"status": "ok", "result": response.get("data")}
                if response.get("ok")
                else {
                    "status": "warning",
                    "hint": "安装已完成；请单独运行 aidee skills sync",
                }
            )
        except (ValueError, OSError, subprocess.SubprocessError):
            skills_result = {
                "status": "warning",
                "hint": "安装已完成；请单独运行 aidee skills sync",
            }
    print(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "installed": True,
                    "version": str(version),
                    "manager": args.manager,
                    "skillsSync": skills_result,
                    "next": "aidee auth login",
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"安装失败：{type(error).__name__}；未执行未验签的产物。", file=sys.stderr
        )
        raise SystemExit(1)
