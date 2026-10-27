"""Exercise promotion and failed recovery with signed offline object-store doubles."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

spec = importlib.util.spec_from_file_location(
    "aidee_promote", Path(__file__).parents[1] / "scripts/promote.py"
)
promoter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promoter)


def release_fixture(tmp_path, channel="stable"):
    key = Ed25519PrivateKey.generate()
    base = "https://release.example/cli"
    root = "oss://bucket/cli"
    wheel = b"immutable-wheel"

    def pair(version):
        data = {
            "version": version,
            "channel": channel,
            "artifacts": [
                {
                    "url": base + "/versions/" + version + "/cli.whl",
                    "size": len(wheel),
                    "sha256": hashlib.sha256(wheel).hexdigest(),
                }
            ],
        }
        raw = json.dumps(data).encode()
        return raw, base64.b64encode(key.sign(raw))

    old = pair("2.0.0")
    new = pair("2.1.0")
    objects = {
        base + "/" + channel + "/manifest.json": old[0],
        base + "/" + channel + "/manifest.sig": old[1],
        base + "/versions/2.1.0/cli.whl": wheel,
    }
    dist = tmp_path / "dist"
    dist.mkdir()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name, raw in zip(("manifest.json", "manifest.sig"), new):
        (dist / name).write_bytes(raw)
    (dist / "install.py").write_bytes(b"installer")
    for name in ("install.sh", "install.ps1"):
        (scripts / name).write_bytes(b"wrapper")

    def put(source, target):
        objects[target.replace(root, base)] = source.read_bytes()

    def remove(target):
        objects.pop(target.replace(root, base), None)

    return key, base, root, old, new, objects, dist, scripts, put, remove


def test_half_promotion_failure_restores_verified_old_pair(tmp_path):
    key, base, root, old, new, objects, dist, scripts, put, remove = release_fixture(
        tmp_path
    )
    writes = []

    def flaky(source, target):
        writes.append(target)
        if target.endswith("stable/manifest.sig") and len(writes) == 5:
            raise OSError("upload failed")
        put(source, target)

    with pytest.raises(RuntimeError, match="restored and public read-back verified"):
        promoter.promote(
            dist,
            scripts,
            key.public_key(),
            root,
            read=objects.get,
            put=flaky,
            delete=remove,
        )
    assert (
        objects[base + "/stable/manifest.json"],
        objects[base + "/stable/manifest.sig"],
    ) == old


def test_restore_failure_never_claims_channel_recovered(tmp_path):
    key, base, root, old, new, objects, dist, scripts, put, remove = release_fixture(
        tmp_path
    )

    def flaky(source, target):
        if target.endswith("manifest.sig") or (
            target.endswith("manifest.json") and source.parent != dist
        ):
            raise OSError("object write unavailable")
        put(source, target)

    with pytest.raises(RuntimeError, match="restoration UNCONFIRMED"):
        promoter.promote(
            dist,
            scripts,
            key.public_key(),
            root,
            read=objects.get,
            put=flaky,
            delete=remove,
        )


def test_public_readback_tampering_causes_restore(tmp_path):
    key, base, root, old, new, objects, dist, scripts, put, remove = release_fixture(
        tmp_path
    )

    def tamper(source, target):
        put(source, target)
        if target.endswith("manifest.sig") and source.parent == dist:
            objects[base + "/stable/manifest.json"] = b"tampered"

    with pytest.raises(RuntimeError, match="restored and public read-back verified"):
        promoter.promote(
            dist,
            scripts,
            key.public_key(),
            root,
            read=objects.get,
            put=tamper,
            delete=remove,
        )
    assert objects[base + "/stable/manifest.json"] == old[0]


def test_preview_installers_cannot_change_stable_entrypoints(tmp_path):
    key, base, root, old, new, objects, dist, scripts, put, remove = release_fixture(
        tmp_path, "preview"
    )
    objects[base + "/install.py"] = b"stable-installer"
    report = promoter.promote(
        dist, scripts, key.public_key(), root, read=objects.get, put=put, delete=remove
    )
    assert report["publicReadBackVerified"] is True
    assert objects[base + "/install.py"] == b"stable-installer"
    assert objects[base + "/preview/install.py"] == b"installer"


def test_stale_tag_does_not_upload_any_mutable_files(tmp_path):
    key, base, root, old, new, objects, dist, scripts, put, remove = release_fixture(
        tmp_path
    )
    objects[base + "/stable/manifest.json"], objects[base + "/stable/manifest.sig"] = (
        new
    )
    with pytest.raises(RuntimeError, match="stale channel"):
        promoter.promote(
            dist,
            scripts,
            key.public_key(),
            root,
            read=objects.get,
            put=lambda *_: pytest.fail("stale publish mutated channel"),
            delete=remove,
        )


def test_bootstrap_upload_failure_restores_all_original_entrypoints(tmp_path):
    key, base, root, old, new, objects, dist, scripts, put, remove = release_fixture(
        tmp_path
    )
    original = {
        base + "/" + name: ("old-" + name).encode()
        for name in ("install.py", "install.sh", "install.ps1")
    }
    objects.update(original)
    failed = False

    def once(source, target):
        nonlocal failed
        if target.endswith("install.sh") and not failed:
            failed = True
            raise OSError("bootstrap upload failed")
        put(source, target)

    with pytest.raises(RuntimeError, match="bootstrap restored too"):
        promoter.promote(
            dist,
            scripts,
            key.public_key(),
            root,
            read=objects.get,
            put=once,
            delete=remove,
        )
    assert all(objects[url] == raw for url, raw in original.items())
    assert objects[base + "/stable/manifest.json"] == old[0]
