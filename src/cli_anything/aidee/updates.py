"""Signed wheel delivery through the original isolated tool manager."""

from __future__ import annotations
import base64
from contextlib import contextmanager
import hashlib
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from . import __version__
from .errors import CLIError
from .settings import atomic_json, directory, load_json, validate_base

DISTRIBUTION = "cli-anything-aidee"


def fetch(url, maximum):
    validate_base(url)
    try:
        response = requests.get(url, timeout=15, allow_redirects=False, stream=True)
        if response.status_code != 200:
            raise CLIError("UPDATE_FAILED", "无法获取签名发行产物", 7)
        chunks = []
        size = 0
        for chunk in response.iter_content(64 * 1024):
            size += len(chunk)
            if size > maximum:
                raise CLIError("UPDATE_FAILED", "发行产物超过大小上限", 7)
            chunks.append(chunk)
        return b"".join(chunks)
    except requests.RequestException:
        raise CLIError("UPDATE_FAILED", "发行源暂时不可用", 7) from None
    finally:
        if "response" in locals():
            response.close()


def public_key():
    override = os.environ.get("AIDEE_RELEASE_PUBLIC_KEY")
    try:
        raw = (
            Path(override).read_bytes()
            if override
            else files("cli_anything.aidee")
            .joinpath("release-public-key.pem")
            .read_bytes()
        )
        key = serialization.load_pem_public_key(raw)
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError()
        return key
    except (ValueError, OSError):
        raise CLIError(
            "UPDATE_FAILED",
            "尚未配置可信发行公钥",
            7,
            hint="维护者须完成签名发布配置；不会执行未验签的升级",
        ) from None


def verify_manifest(raw, signature, key):
    try:
        key.verify(base64.b64decode(signature, validate=True), raw)
    except (InvalidSignature, ValueError):
        raise CLIError("UPDATE_FAILED", "发行清单签名无效", 7) from None
    try:
        manifest = json.loads(raw)
    except ValueError:
        raise CLIError("UPDATE_FAILED", "发行清单不是JSON", 7) from None
    fields = (
        "schemaVersion",
        "version",
        "channel",
        "commit",
        "pythonRequires",
        "publishedAt",
        "releaseNotesUrl",
        "artifacts",
    )
    if (
        not isinstance(manifest, dict)
        or any(field not in manifest for field in fields)
        or manifest["schemaVersion"] != 1
    ):
        raise CLIError("UPDATE_FAILED", "发行清单字段或版本不受支持", 7)
    try:
        version = Version(manifest["version"])
        if not SpecifierSet(manifest["pythonRequires"]).contains(
            ".".join(map(str, sys.version_info[:3]))
        ):
            raise CLIError("UPDATE_FAILED", "新版不支持当前Python版本", 7)
        if manifest["channel"] not in ("stable", "preview") or (
            manifest["channel"] == "stable" and version.is_prerelease
        ):
            raise ValueError()
        if (
            not isinstance(manifest["artifacts"], list)
            or len(manifest["artifacts"]) != 1
        ):
            raise ValueError()
        artifact = manifest["artifacts"][0]
        if set(("filename", "url", "sha256", "size")) - artifact.keys():
            raise ValueError()
        if Path(artifact["filename"]).name != artifact["filename"] or not artifact[
            "filename"
        ].endswith("-py3-none-any.whl"):
            raise ValueError()
        if not artifact["filename"].startswith(
            "cli_anything_aidee-" + str(version) + "-"
        ):
            raise ValueError()
        if len(artifact["sha256"]) != 64 or any(
            x not in "0123456789abcdef" for x in artifact["sha256"]
        ):
            raise ValueError()
        if (
            not isinstance(artifact["size"], int)
            or isinstance(artifact["size"], bool)
            or not 0 < artifact["size"] <= 64 * 1024 * 1024
        ):
            raise ValueError()
        validate_base(artifact["url"])
    except (ValueError, TypeError, KeyError, InvalidVersion):
        raise CLIError("UPDATE_FAILED", "发行清单内容不合法", 7) from None
    return manifest


def check_update(settings, channel="stable"):
    base = settings.values["release_base"] + "/" + channel
    key = (
        public_key()
    )  # Fail before fetching an untrusted release when configuration is incomplete.
    manifest = verify_manifest(
        fetch(base + "/manifest.json", 256 * 1024),
        fetch(base + "/manifest.sig", 2048),
        key,
    )
    if manifest["channel"] != channel:
        raise CLIError("UPDATE_FAILED", "发行通道不一致", 7)
    current = Version(__version__)
    latest = Version(manifest["version"])
    manifest["updateAvailable"] = latest > current
    manifest["currentVersion"] = __version__
    return manifest


def installation():
    receipt = load_json(Path(sys.prefix) / ".aidee-install.json", {})
    # Receipt is evidence only when the actual interpreter and metadata agree.
    if (
        receipt.get("distribution") != DISTRIBUTION
        or receipt.get("environment") != str(Path(sys.prefix).resolve())
        or receipt.get("version") != __version__
    ):
        raise CLIError(
            "UPDATE_FAILED",
            "无法确认本次安装来源",
            7,
            hint="使用原 uv tool / pipx 升级；直接pip或源码环境不自动覆盖",
        )
    executable, _ = managed_environment(receipt.get("manager"))
    return receipt, executable


def managed_environment(manager):
    if Path(sys.prefix).resolve().name.casefold() != DISTRIBUTION:
        raise CLIError(
            "UPDATE_FAILED",
            "当前工具环境名称与发行包不匹配",
            7,
            hint="带后缀或共享环境请用原管理器手动升级",
        )
    if manager not in ("uv", "pipx"):
        raise CLIError("UPDATE_FAILED", "此安装来源只提供手动升级指引", 7)
    # Python metadata validates the running distribution location, rather than a PATH command.
    from importlib.metadata import distribution

    dist = distribution(DISTRIBUTION)
    if dist.version != __version__:
        raise CLIError("UPDATE_FAILED", "当前导入版本与发行元数据不一致", 7)
    if (
        not Path(dist.locate_file(""))
        .resolve()
        .is_relative_to(Path(sys.prefix).resolve())
    ):
        raise CLIError("UPDATE_FAILED", "当前包不属于安装回执环境", 7)
    if not Path(sys.executable).absolute().is_relative_to(Path(sys.prefix).absolute()):
        raise CLIError("UPDATE_FAILED", "当前解释器与工具环境不一致", 7)
    executable = shutil.which(manager)
    if not executable:
        raise CLIError(
            "UPDATE_FAILED", "原安装管理器不可用", 7, hint="安装对应uv/pipx后重试"
        )
    if manager == "uv":
        probe = subprocess.run(
            [executable, "tool", "dir"], capture_output=True, text=True, timeout=15
        )
        if probe.returncode or Path(probe.stdout.strip()).resolve() != (
            Path(sys.prefix).resolve().parent
        ):
            raise CLIError("UPDATE_FAILED", "uv工具目录与当前环境不匹配", 7)
    else:
        probe = subprocess.run(
            [executable, "list", "--json"], capture_output=True, text=True, timeout=15
        )
        try:
            entry = json.loads(probe.stdout)["venvs"][DISTRIBUTION]["metadata"][
                "main_package"
            ]
        except (ValueError, KeyError, TypeError):
            raise CLIError("UPDATE_FAILED", "pipx未管理当前发行包", 7) from None
        if probe.returncode or entry.get("package_version") != __version__:
            raise CLIError("UPDATE_FAILED", "pipx版本与当前包不匹配", 7)
        home = subprocess.run(
            [executable, "environment", "--value", "PIPX_LOCAL_VENVS"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if (
            home.returncode
            or Path(home.stdout.strip()).resolve() != Path(sys.prefix).resolve().parent
        ):
            raise CLIError("UPDATE_FAILED", "pipx工具目录与当前环境不匹配", 7)
    return executable, dist


def register_installation(settings, manager):
    """Explicitly bind an existing managed installation to identical signed wheel bytes."""
    import zipfile

    _, dist = managed_environment(manager)
    direct_url = json.loads(dist.read_text("direct_url.json") or "{}")
    if direct_url.get("dir_info", {}).get("editable"):
        raise CLIError("UPDATE_FAILED", "源码editable环境不能登记为正式发行", 7)
    base = settings.values["release_base"] + "/versions/" + __version__
    manifest = verify_manifest(
        fetch(base + "/manifest.json", 256 * 1024),
        fetch(base + "/manifest.sig", 2048),
        public_key(),
    )
    if manifest["version"] != __version__:
        raise CLIError("UPDATE_FAILED", "当前版本签名发行不匹配", 7)
    artifact = manifest["artifacts"][0]
    direct_hash = direct_url.get("archive_info", {}).get("hashes", {}).get("sha256")
    if direct_hash is not None and direct_hash != artifact["sha256"]:
        raise CLIError("UPDATE_FAILED", "已安装来源与签名wheel不一致", 7)
    with tempfile.TemporaryDirectory(prefix="aidee-register-") as temp:
        wheel = verified_wheel(artifact, temp)
        try:
            with zipfile.ZipFile(wheel) as archive:
                count = 0
                for name in archive.namelist():
                    if name.endswith("/") or name.endswith(".dist-info/RECORD"):
                        continue
                    target = Path(dist.locate_file(name)).resolve()
                    if (
                        not target.is_relative_to(Path(sys.prefix).resolve())
                        or not target.is_file()
                        or target.read_bytes() != archive.read(name)
                    ):
                        raise CLIError(
                            "UPDATE_FAILED", "当前安装文件与签名wheel不一致，未登记", 7
                        )
                    count += 1
                if not count:
                    raise CLIError("UPDATE_FAILED", "签名wheel没有可核验文件", 7)
        except zipfile.BadZipFile:
            raise CLIError("UPDATE_FAILED", "签名wheel格式无效", 7) from None
    receipt = {
        "manager": manager,
        "environment": str(Path(sys.prefix).resolve()),
        "distribution": DISTRIBUTION,
        "version": __version__,
        "commit": manifest["commit"],
        "channel": manifest["channel"],
        "artifact": artifact,
        "registration": "signed-wheel-file-verification",
    }
    atomic_json(Path(sys.prefix) / ".aidee-install.json", receipt)
    return {"registered": True, "manager": manager, "sourceVerified": True}


def verified_wheel(artifact, target):
    raw = fetch(artifact["url"], 64 * 1024 * 1024)
    if (
        len(raw) != artifact["size"]
        or hashlib.sha256(raw).hexdigest() != artifact["sha256"]
    ):
        raise CLIError("UPDATE_FAILED", "wheel大小或SHA256校验失败", 7)
    path = Path(target) / artifact["filename"]
    path.write_bytes(raw)
    return path


@contextmanager
def update_lock():
    path = directory() / "update.lock"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise CLIError(
            "UPDATE_FAILED",
            "已有升级流程，未重复执行",
            7,
            hint="若前次进程已终止，确认后清理update.lock",
        ) from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def skills_sync_result(requested=False):
    if not requested:
        return {"status": "not_requested", "hint": "aidee skills sync"}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "cli_anything.aidee", "skills", "sync"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            env={**os.environ, "AIDEE_NO_UPDATE": "1"},
        )
        output = json.loads(result.stdout) if result.returncode == 0 else {}
        if not output.get("ok"):
            return {
                "status": "warning",
                "hint": "升级已完成；请单独运行 aidee skills sync 检查目录权限",
            }
        return {"status": "ok", "result": output.get("data")}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {"status": "warning", "hint": "升级已完成；请单独运行 aidee skills sync"}


def install_update(settings, manifest, *, sync_skills=False):
    # check_update verifies before deriving these local convenience fields.
    if not manifest.get("updateAvailable"):
        return {
            "updated": False,
            "currentVersion": __version__,
            "latestVersion": manifest["version"],
            "skillsSync": skills_sync_result(sync_skills),
        }
    receipt, executable = installation()
    old = receipt.get("artifact")
    if not old:
        raise CLIError(
            "UPDATE_FAILED",
            "缺少旧版固定产物，不能保证恢复",
            7,
            hint="使用正式安装器重新登记安装来源",
        )
    with (
        update_lock(),
        tempfile.TemporaryDirectory(prefix="aidee-upgrade-") as directory_,
    ):
        old_wheel = verified_wheel(old, directory_)
        wheel = verified_wheel(manifest["artifacts"][0], directory_)

        def command(file):
            return (
                [
                    executable,
                    "tool",
                    "install",
                    "--force",
                    "--from",
                    str(file),
                    DISTRIBUTION,
                ]
                if receipt["manager"] == "uv"
                else [executable, "install", "--force", str(file)]
            )

        env = os.environ.copy()
        env["AIDEE_NO_UPDATE"] = "1"
        new_receipt = {
            **receipt,
            "version": manifest["version"],
            "commit": manifest["commit"],
            "channel": manifest["channel"],
            "artifact": manifest["artifacts"][0],
        }

        def install_and_verify(artifact_path, expected_version):
            try:
                installed = subprocess.run(
                    command(artifact_path),
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=180,
                )
                if installed.returncode:
                    return False
                tested = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey;import sys,runpy;sys.argv=['aidee','--version'];runpy.run_module('cli_anything.aidee',run_name='__main__')",
                    ],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=15,
                )
                return tested.returncode == 0 and tested.stdout.strip().endswith(
                    "version " + expected_version
                )
            except (OSError, subprocess.SubprocessError):
                # A manager can time out after changing files; always attempt the fixed old wheel.
                return False

        installed_ok = install_and_verify(wheel, manifest["version"])
        if installed_ok:
            try:
                atomic_json(Path(sys.prefix) / ".aidee-install.json", new_receipt)
            except OSError:
                installed_ok = False
        if not installed_ok:
            restored_ok = install_and_verify(old_wheel, __version__)
            if restored_ok:
                try:
                    atomic_json(Path(sys.prefix) / ".aidee-install.json", receipt)
                except OSError:
                    restored_ok = False
            raise CLIError(
                "UPDATE_FAILED",
                "升级失败",
                7,
                meta={"rolledBack": restored_ok},
                hint="保留配置；请使用原管理器检查安装",
            )
        return {
            "updated": True,
            "from": __version__,
            "to": manifest["version"],
            "manager": receipt["manager"],
            "skillsSync": skills_sync_result(sync_skills),
            "next": "请重新运行原命令",
        }


def startup_check(settings, explicit_json=False):
    if (
        os.environ.get("CI")
        or os.environ.get("AIDEE_NO_UPDATE") == "1"
        or not sys.stdin.isatty()
        or not sys.stdout.isatty()
    ):
        return None
    cache = directory() / "update-check.json"
    try:
        cached = load_json(cache, {})
        if time.time() - cached.get("checkedAt", 0) < 86400:
            return None
        manifest = check_update(settings)
        atomic_json(cache, {"checkedAt": time.time(), "version": manifest["version"]})
    except (CLIError, OSError, subprocess.SubprocessError):
        # Checks are best-effort; an actual attempted installation has a separate outcome below.
        try:
            atomic_json(cache, {"checkedAt": time.time(), "checkFailed": True})
        except (OSError, CLIError):
            pass
        return None
    if manifest["updateAvailable"]:
        if settings.profile.get("update.auto") is True and not explicit_json:
            # Once installation starts, success or failure ends this invocation before any business request.
            return install_update(settings, manifest)
        print("Aidee有新版本；运行 aidee update 升级。", file=sys.stderr)
    return None
