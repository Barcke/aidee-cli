"""Exercise the actual release entrypoint with ephemeral keys and a stubbed wheel build."""

import base64
import json
from pathlib import Path
import runpy
import subprocess
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

RELEASE = Path(__file__).parents[1] / "scripts/release.py"


def release_fixture(tmp_path, monkeypatch):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "AIDEE_RELEASE_SIGNING_KEY_PEM",
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii"),
    )
    monkeypatch.setenv("AIDEE_RELEASE_BASE", "https://ai-agent.ideamake.cn/aidee-cli")
    monkeypatch.setenv("GITHUB_SHA", "1" * 40)
    monkeypatch.setattr("sys.argv", [str(RELEASE), "v2.0.0-rc.2"])
    (tmp_path / "src/cli_anything/aidee").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/install.py").write_text(
        'PUBLIC_KEY_PEM = "UNCONFIGURED"\n', encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "2.0.0"\n', encoding="utf-8"
    )

    def build(command, *, check):
        assert command == ["uv", "build", "--wheel", "--out-dir", "dist"] and check
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist/cli_anything_aidee-2.0.0rc2-py3-none-any.whl").write_bytes(
            b"fixture-wheel"
        )

    stub = Mock(side_effect=build)
    monkeypatch.setattr(subprocess, "run", stub)
    return private, public, stub


@pytest.mark.parametrize("newline", ["LF", "CRLF"])
def test_release_accepts_same_public_key_with_pem_line_endings(
    tmp_path, monkeypatch, newline
):
    private, public, build = release_fixture(tmp_path, monkeypatch)
    configured = public.replace(b"\n", b"\r\n") if newline == "CRLF" else public
    monkeypatch.setenv("AIDEE_RELEASE_PUBLIC_KEY_PEM", configured.decode("ascii"))
    runpy.run_path(str(RELEASE), run_name="__main__")
    build.assert_called_once()
    raw = (tmp_path / "dist/manifest.json").read_bytes()
    private.public_key().verify(
        base64.b64decode((tmp_path / "dist/manifest.sig").read_bytes()), raw
    )
    manifest = json.loads(raw)
    assert manifest["version"] == "2.0.0rc2" and manifest["channel"] == "preview"
    assert manifest["commit"] == "1" * 40
    assert manifest["artifacts"][0]["url"].startswith(
        "https://ai-agent.ideamake.cn/aidee-cli/versions/2.0.0rc2/"
    )
    emitted = serialization.load_pem_public_key(
        (tmp_path / "src/cli_anything/aidee/release-public-key.pem").read_bytes()
    )
    assert emitted.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    ) == private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assert "UNCONFIGURED" not in (tmp_path / "dist/install.py").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("configured", ["other-root", "invalid-pem", "missing"])
def test_release_rejects_untrusted_key_before_build_or_source_mutation(
    tmp_path, monkeypatch, configured
):
    _, _, build = release_fixture(tmp_path, monkeypatch)
    if configured == "other-root":
        value = (
            Ed25519PrivateKey.generate()
            .public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("ascii")
        )
        monkeypatch.setenv("AIDEE_RELEASE_PUBLIC_KEY_PEM", value)
    elif configured == "invalid-pem":
        monkeypatch.setenv("AIDEE_RELEASE_PUBLIC_KEY_PEM", "not a public key")
    else:
        monkeypatch.delenv("AIDEE_RELEASE_PUBLIC_KEY_PEM", raising=False)
    with pytest.raises(SystemExit, match="protected trusted public key"):
        runpy.run_path(str(RELEASE), run_name="__main__")
    build.assert_not_called()
    assert not (tmp_path / "dist").exists()
    assert not (tmp_path / "src/cli_anything/aidee/release-public-key.pem").exists()
    assert not (tmp_path / "src/cli_anything/aidee/build.json").exists()
    assert (tmp_path / "pyproject.toml").read_text(
        encoding="utf-8"
    ) == '[project]\nversion = "2.0.0"\n'
