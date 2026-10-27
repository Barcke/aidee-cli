"""Profiles and origin-bound credentials, without reading legacy sessions implicitly."""

from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import uuid
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .errors import CLIError

DEFAULTS = {
    "api_base": "https://api.aidee.me/aidee-server",
    "team_base": "https://api.aidee.me/team-aidee-server",
    "web_base": "https://web.aidee.me",
    "release_base": "https://ai-agent.ideamake.cn/aidee-cli",
}


def directory():
    return Path(os.environ.get("AIDEE_CONFIG_DIR", str(Path.home() / ".aidee")))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".aidee-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            os.chmod(temp, 0o600)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default
    except (ValueError, OSError):
        raise CLIError(
            "LOCAL_ERROR",
            "本地配置文件不可读取",
            7,
            hint="检查配置路径和权限；不自动覆盖损坏文件",
        )


def validate_base(value):
    u = urlsplit(value)
    if (
        u.username
        or u.password
        or u.query
        or u.fragment
        or not u.hostname
        or u.scheme not in ("http", "https")
    ):
        raise CLIError(
            "VALIDATION_FAILED", "服务地址必须是无用户信息的 HTTP(S) 基础地址", 2
        )
    if u.scheme == "http" and u.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise CLIError("VALIDATION_FAILED", "非本机服务必须使用 HTTPS", 2)
    return value.rstrip("/")


class Settings:
    def __init__(self, profile=None, **overrides):
        self.path = directory() / "config.json"
        self.data = load_json(self.path, {"currentProfile": "default", "profiles": {}})
        self.name = (
            profile
            or os.environ.get("AIDEE_PROFILE")
            or self.data.get("currentProfile", "default")
        )
        if (
            not self.name
            or len(self.name) > 80
            or any(x in self.name for x in ("/", "\\", "\0"))
        ):
            raise CLIError("VALIDATION_FAILED", "profile 名称无效", 2)
        self.profile = self.data.setdefault("profiles", {}).setdefault(self.name, {})
        self.values = {}
        for field, default in DEFAULTS.items():
            env = {
                "api_base": "AIDEE_BASE_URL",
                "team_base": "AIDEE_TEAM_BASE_URL",
                "web_base": "AIDEE_WEB_BASE",
                "release_base": "AIDEE_RELEASE_BASE",
            }[field]
            self.values[field] = validate_base(
                overrides.get(field)
                or os.environ.get(env)
                or self.profile.get(field)
                or default
            )
        self.values["apiTimezone"] = os.environ.get(
            "AIDEE_API_TIMEZONE"
        ) or self.profile.get("apiTimezone", "Asia/Shanghai")
        try:
            ZoneInfo(self.values["apiTimezone"])
        except ZoneInfoNotFoundError:
            raise CLIError(
                "VALIDATION_FAILED", "apiTimezone不是有效IANA时区", 2
            ) from None
        self.auth_mode = overrides.get("auth_mode") or self.profile.get(
            "auth_mode", "key"
        )
        if self.auth_mode not in ("key", "token"):
            raise CLIError("VALIDATION_FAILED", "auth mode 必须为 key 或 token", 2)
        self.explicit_key = overrides.get("api_key")
        self.explicit_token = overrides.get("token")

    def save(self):
        atomic_json(self.path, self.data)

    def set(self, key, value):
        allowed = set(DEFAULTS) | {"team_id", "update.auto", "auth_mode", "apiTimezone"}
        if key not in allowed:
            raise CLIError(
                "VALIDATION_FAILED",
                "不支持该配置项",
                2,
                hint="使用 config show 查看可配置字段",
            )
        if key in DEFAULTS:
            value = validate_base(value)
        if key == "apiTimezone":
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError:
                raise CLIError(
                    "VALIDATION_FAILED", "apiTimezone不是有效IANA时区", 2
                ) from None
        if key == "update.auto":
            if value not in (True, False, "true", "false"):
                raise CLIError("VALIDATION_FAILED", "update.auto 仅支持 true/false", 2)
            value = value is True or value == "true"
        if key == "auth_mode" and value not in ("key", "token"):
            raise CLIError("VALIDATION_FAILED", "auth_mode 仅支持 key/token", 2)
        self.profile[key] = value
        self.save()

    def binding(self):
        return {
            "api_base": self.values["api_base"],
            "team_base": self.values["team_base"],
        }

    def credential(self):
        value = (
            (self.explicit_token or os.environ.get("AIDEE_TOKEN"))
            if self.auth_mode == "token"
            else (self.explicit_key or os.environ.get("AIDEE_API_KEY"))
        )
        if value:
            return value
        record = credentials_get(self.name)
        if not record:
            return None
        if (
            record.get("binding") != self.binding()
            or record.get("mode") != self.auth_mode
        ):
            raise CLIError(
                "AUTH_ORIGIN_CHANGED",
                "服务地址或认证模式已变更，请重新验证凭据",
                3,
                hint="运行 auth login",
            )
        return record.get("secret")

    def show(self):
        return {
            "profile": self.name,
            **self.values,
            "auth_mode": self.auth_mode,
            "team_id": self.profile.get("team_id"),
            "update.auto": self.profile.get("update.auto", False),
        }


def _keyring():
    if os.environ.get("AIDEE_KEYRING_DISABLED") == "1":
        return None
    try:
        import keyring

        if keyring.get_keyring().priority <= 0:
            return None
        return keyring
    except Exception:
        return None


def _credential_index():
    return directory() / "credential-index.json"


def credentials_get(profile):
    authority = load_json(_credential_index(), {}).get(profile)
    if authority is None or authority.get("store") == "logged-out":
        return None
    if authority.get("store") == "keyring":
        ring = _keyring()
        if not ring:
            raise CLIError(
                "LOCAL_ERROR",
                "当前凭据的钥匙串不可用，未切换到其他账号",
                7,
                hint="解锁系统钥匙串或重新执行 auth login",
            )
        try:
            raw = ring.get_password("aidee-cli", profile)
            value = json.loads(raw) if raw else None
        except Exception:
            raise CLIError(
                "LOCAL_ERROR", "无法读取当前钥匙串凭据，未回退旧凭据", 7
            ) from None
    elif authority.get("store") == "file":
        value = load_json(directory() / "credentials.json", {}).get(profile)
    else:
        raise CLIError("LOCAL_ERROR", "凭据存储标记无效，请重新登录", 7)
    if not isinstance(value, dict) or value.get("generation") != authority.get(
        "generation"
    ):
        raise CLIError(
            "LOCAL_ERROR",
            "当前凭据代次不匹配，未尝试其他账号",
            7,
            hint="重新执行 auth login",
        )
    return value


def credentials_set(settings, secret):
    generation = str(uuid.uuid4())
    value = {
        "secret": secret,
        "mode": settings.auth_mode,
        "binding": settings.binding(),
        "generation": generation,
    }
    ring = _keyring()
    store = "file"
    if ring:
        try:
            ring.set_password("aidee-cli", settings.name, json.dumps(value))
            store = "keyring"
        except Exception:
            pass
    if store == "file":
        path = directory() / "credentials.json"
        data = load_json(path, {})
        data[settings.name] = value
        atomic_json(path, data)
    index = load_json(_credential_index(), {})
    index[settings.name] = {"store": store, "generation": generation}
    # This authoritative marker changes only after the new secret is safely stored.
    # Stale copies may remain if cleanup fails, but can never become a fallback identity.
    atomic_json(_credential_index(), index)
    if store == "keyring":
        path = directory() / "credentials.json"
        try:
            old = load_json(path, {})
            if settings.name in old:
                old.pop(settings.name)
                atomic_json(path, old)
        except (CLIError, OSError):
            pass
    return store


def credentials_delete(profile):
    index = load_json(_credential_index(), {})
    previous_store = index.get(profile, {}).get("store")
    index[profile] = {"store": "logged-out", "generation": str(uuid.uuid4())}
    # Persist the tombstone first. A locked ring must never resurrect an old session.
    atomic_json(_credential_index(), index)
    ring = _keyring()
    cleanup_pending = previous_store == "keyring" and ring is None
    if ring:
        try:
            ring.delete_password("aidee-cli", profile)
        except Exception:
            cleanup_pending = True
    path = directory() / "credentials.json"
    if path.exists():
        try:
            data = load_json(path, {})
            data.pop(profile, None)
            atomic_json(path, data)
        except (OSError, CLIError):
            cleanup_pending = True
    return {"loggedOut": True, "credentialCleanupPending": cleanup_pending}
