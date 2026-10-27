#!/usr/bin/env python3
"""Verify public immutable bytes, then promote a recoverable two-object channel pair."""

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from packaging.version import Version
from cryptography.hazmat.primitives import serialization


def read_public(url):
    try:
        with urlopen(
            Request(url, headers={"Cache-Control": "no-cache"}), timeout=60
        ) as response:
            return response.read(64 * 1024 * 1024 + 1)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise


def upload(source, target):
    subprocess.run(
        [
            "ossutil",
            "cp",
            str(source),
            target,
            "--force",
            "--cache-control",
            "no-cache",
        ],
        check=True,
    )


def remove(target):
    subprocess.run(["ossutil", "rm", target, "--force"], check=True)


def verified_pair(key, raw, signature):
    if raw is None or signature is None:
        raise ValueError("Channel manifest/signature pair incomplete")
    key.verify(base64.b64decode(signature, validate=True), raw)
    return json.loads(raw)


def promote(dist, scripts, key, root, *, read=read_public, put=upload, delete=remove):
    manifest = (dist / "manifest.json").read_bytes()
    signature = (dist / "manifest.sig").read_bytes()
    data = verified_pair(key, manifest, signature)
    artifact = data["artifacts"][0]
    wheel = read(artifact["url"])
    if (
        wheel is None
        or len(wheel) != artifact["size"]
        or hashlib.sha256(wheel).hexdigest() != artifact["sha256"]
    ):
        raise RuntimeError("Public wheel verification failed; channel unchanged")
    base = artifact["url"].rsplit("/versions/", 1)[0]
    channel_url = base + "/" + data["channel"]
    names = ("manifest.json", "manifest.sig")
    previous_raw = read(channel_url + "/manifest.json")
    previous_sig = read(channel_url + "/manifest.sig")
    if previous_raw is not None or previous_sig is not None:
        previous = verified_pair(key, previous_raw, previous_sig)
        if Version(previous["version"]) >= Version(data["version"]):
            raise RuntimeError(
                "Refuse stale channel promotion; current release is not older"
            )
    # Preview installers remain in preview; they cannot replace the stable bootstrap.
    installer_root = root if data["channel"] == "stable" else root + "/preview"
    installer_url = base if data["channel"] == "stable" else channel_url
    mutable = []
    for name in ("install.py", "install.sh", "install.ps1"):
        source = dist / name if name == "install.py" else scripts / name
        mutable.append(
            (
                source,
                installer_root + "/" + name,
                installer_url + "/" + name,
                read(installer_url + "/" + name),
            )
        )
    channel_root = root + "/" + data["channel"]
    for name, raw in zip(names, (previous_raw, previous_sig)):
        mutable.append(
            (dist / name, channel_root + "/" + name, channel_url + "/" + name, raw)
        )
    try:
        for source, target, _, _ in mutable:
            put(source, target)
        actual = (
            read(channel_url + "/manifest.json"),
            read(channel_url + "/manifest.sig"),
        )
        verified_pair(key, *actual)
        if actual != (manifest, signature) or any(
            read(url) != source.read_bytes() for source, _, url, _ in mutable
        ):
            raise ValueError(
                "Public channel/bootstrap read-back differs from uploaded release"
            )
    except Exception as failure:
        # A mixed pair fails signature checks. Restore and publicly verify the old pair.
        # Separate OSS objects cannot provide a globally atomic transaction.
        try:
            with tempfile.TemporaryDirectory(prefix="aidee-channel-restore-") as temp:
                for index, (_, target, _, previous) in enumerate(mutable):
                    try:
                        if previous is None:
                            delete(target)
                        else:
                            source = Path(temp) / str(index)
                            source.write_bytes(previous)
                            put(source, target)
                    except Exception:
                        # Try every object; only a complete public read-back can confirm recovery.
                        pass
            if any(read(url) != previous for _, _, url, previous in mutable):
                raise ValueError("Restored channel/bootstrap public bytes differ")
            restored = (
                read(channel_url + "/manifest.json"),
                read(channel_url + "/manifest.sig"),
            )
            if restored != (previous_raw, previous_sig):
                raise ValueError("Restored public bytes differ")
            if previous_raw is not None:
                verified_pair(key, *restored)
        except Exception as restore_failure:
            raise RuntimeError(
                "Promotion failed; previous channel/bootstrap restoration UNCONFIRMED. Stop publishing and inspect channel objects."
            ) from restore_failure
        raise RuntimeError(
            "Promotion failed; previous channel pair restored and public read-back verified; bootstrap restored too"
        ) from failure
    return {
        "promoted": data["version"],
        "channel": data["channel"],
        "publicReadBackVerified": True,
    }


def main():
    key = serialization.load_pem_public_key(
        os.environ["AIDEE_RELEASE_PUBLIC_KEY_PEM"].encode()
    )
    root = f"oss://{os.environ['OSS_BUCKET']}/{os.environ.get('OSS_RELEASE_PREFIX', 'aidee-cli')}"
    print(json.dumps(promote(Path("dist"), Path("scripts"), key, root)))


if __name__ == "__main__":
    main()
