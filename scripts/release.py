#!/usr/bin/env python3
"""Build/sign locally; uploading and channel promotion are separate validated steps."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from packaging.version import Version

parser = argparse.ArgumentParser()
parser.add_argument("version")
parser.add_argument(
    "--base",
    default=os.environ.get(
        "AIDEE_RELEASE_BASE", "https://ai-agent.ideamake.cn/aidee-cli"
    ),
)
args = parser.parse_args()
if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-rc\.\d+)?", args.version):
    raise SystemExit("tag must be vX.Y.Z or vX.Y.Z-rc.N")
version = Version(args.version[1:])
channel = "preview" if version.is_prerelease else "stable"
private = serialization.load_pem_private_key(
    os.environ["AIDEE_RELEASE_SIGNING_KEY_PEM"].encode(), password=None
)
if not isinstance(private, Ed25519PrivateKey):
    raise SystemExit("Ed25519 signing key required")
public = (
    private.public_key()
    .public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    .decode()
)
trusted = os.environ.get("AIDEE_RELEASE_PUBLIC_KEY_PEM")
if not trusted or trusted.strip() != public.strip():
    raise SystemExit("Signing key does not match the protected trusted public key")
commit = (
    os.environ.get("GITHUB_SHA")
    or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
)
package = Path("src/cli_anything/aidee")
(package / "release-public-key.pem").write_text(public)
(package / "build.json").write_text(
    json.dumps({"version": str(version), "commit": commit})
)
project = Path("pyproject.toml")
text = project.read_text()
project.write_text(re.sub(r'(?m)^version = ".*"$', f'version = "{version}"', text))
shutil.rmtree("build", ignore_errors=True)
subprocess.run(["uv", "build", "--wheel", "--out-dir", "dist"], check=True)
wheels = list(Path("dist").glob(f"cli_anything_aidee-{version}-*.whl"))
if len(wheels) != 1:
    raise SystemExit("Expected exactly one release wheel")
wheel = wheels[0]
raw = wheel.read_bytes()
manifest = {
    "schemaVersion": 1,
    "version": str(version),
    "channel": channel,
    "commit": commit,
    "pythonRequires": ">=3.10",
    "publishedAt": datetime.now(timezone.utc).isoformat(),
    "releaseNotesUrl": f"https://github.com/Barcke/aidee-cli/releases/tag/{args.version}",
    "artifacts": [
        {
            "filename": wheel.name,
            "url": args.base.rstrip("/") + f"/versions/{version}/" + wheel.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }
    ],
}
encoded = json.dumps(
    manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
).encode()
Path("dist/manifest.json").write_bytes(encoded)
Path("dist/manifest.sig").write_bytes(base64.b64encode(private.sign(encoded)))
installer = (
    Path("scripts/install.py")
    .read_text()
    .replace('PUBLIC_KEY_PEM = "UNCONFIGURED"', f"PUBLIC_KEY_PEM = {public!r}")
)
Path("dist/install.py").write_text(installer)
Path("dist/release-channel").write_text(channel)
print(f"Signed {version} {channel}; promotion has not occurred")
