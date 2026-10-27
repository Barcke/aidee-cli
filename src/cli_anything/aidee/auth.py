"""Public-client PKCE delivery; the existing user Key remains the only credential."""

from __future__ import annotations
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import threading
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import webbrowser
import click
from .client import Client
from .errors import CLIError
from .settings import credentials_set


def pkce():
    verifier = secrets.token_urlsafe(32)
    return verifier, base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode().rstrip("=")


def require_identity(data, *, token_mode=False):
    if (
        not isinstance(data, dict)
        or not data
        or (not token_mode and not isinstance(data.get("userCenterUserId"), str))
        or (not token_mode and not data["userCenterUserId"].strip())
    ):
        raise CLIError(
            "AUTH_INVALID",
            "服务没有返回可核验的本人身份，未保存凭据",
            3,
            hint="检查所选环境是否已部署CLI认证接口",
        )
    return data


def login_browser(settings, *, no_browser=False, timeout=300, scopes=("read",)):
    verifier, challenge = pkce()
    state = secrets.token_urlsafe(32)
    finished = threading.Event()
    outcome = {}
    claimed = threading.Lock()

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            request = urlsplit(self.path)
            query = parse_qs(request.query)
            if request.path != "/callback":
                self.send_error(404)
                return
            supplied = query.get("state", [""])[0]
            if not secrets.compare_digest(supplied, state):
                self.send_error(400, "Authorization request mismatch")
                return
            if not claimed.acquire(blocking=False):
                self.send_error(409)
                return
            try:
                if query.get("error"):
                    raise CLIError("CANCELLED", "已拒绝浏览器授权", 130)
                code = query.get("code", [""])[0]
                if not code:
                    raise CLIError("AUTH_INVALID", "授权回调缺少一次码", 3)
                data = Client(settings).request(
                    "POST",
                    "/integration/cli-auth/token",
                    auth=False,
                    body={
                        "code": code,
                        "codeVerifier": verifier,
                        "clientId": "aidee-cli",
                        "redirectUri": redirect,
                    },
                )
                key = data.get("apiKey") if isinstance(data, dict) else None
                if not isinstance(key, str) or not key.startswith("aidee_"):
                    raise CLIError("AUTH_INVALID", "授权服务没有返回有效用户 Key", 3)
                metadata = Client(settings, secret=key).request(
                    "GET", "/integration/keys/current"
                )
                require_identity(metadata)
                store = credentials_set(settings, key)
                outcome["data"] = {
                    "loggedIn": True,
                    "method": "browser",
                    "keyStore": store,
                    "profile": settings.name,
                    **safe_metadata(metadata),
                }
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write("授权成功，请回到终端。".encode())
            except CLIError as error:
                outcome["error"] = error
                self.send_response(400)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b"Authorization failed; return to your terminal.")
            except Exception:
                outcome["error"] = CLIError(
                    "LOCAL_ERROR", "授权完成失败，未确认登录成功", 7
                )
                self.send_error(500)
            finally:
                finished.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Callback)
    server.daemon_threads = True
    redirect = f"http://127.0.0.1:{server.server_port}/callback"
    url = (
        settings.values["web_base"]
        + "/cli/authorize?"
        + urlencode(
            {
                "client_id": "aidee-cli",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "redirect_uri": redirect,
                "scope": "read write" if "write" in scopes else "read",
            }
        )
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        click.echo("请在5分钟内完成本人授权：\n" + url, err=True)
        if not no_browser:
            try:
                webbrowser.open(url)
            except Exception:
                click.echo("请手动打开上面的授权地址。", err=True)
        until = time.monotonic() + timeout
        while not finished.wait(min(0.2, max(0, until - time.monotonic()))):
            if time.monotonic() >= until:
                raise CLIError(
                    "AUTH_INVALID",
                    "浏览器授权已超时",
                    3,
                    hint="重新运行 auth login --browser",
                )
        if "error" in outcome:
            raise outcome["error"]
        return outcome["data"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def safe_metadata(data):
    allowed = (
        "userCenterUserId",
        "aideeUserId",
        "keyId",
        "keyPrefix",
        "scopes",
        "expiresAt",
        "effectivePermissions",
    )
    return (
        {key: data[key] for key in allowed if key in data}
        if isinstance(data, dict)
        else {}
    )
