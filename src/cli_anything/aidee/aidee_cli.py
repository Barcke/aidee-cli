"""User CLI using the existing core read contracts and narrowly registered writes."""

from __future__ import annotations
from contextvars import ContextVar
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json
import re
import os
import sys
import time
import subprocess
import uuid
import click
from . import __version__
from .auth import login_browser, safe_metadata, require_identity
from .client import Client, active_client, pages, segment
from .errors import CLIError
from .output import emit
from .settings import (
    Settings,
    credentials_set,
    credentials_delete,
    directory,
    atomic_json,
    load_json,
)
from .metadata import REGISTRY, record
from .core import (
    recording as recording_core,
    summary as summary_core,
    group as folder_core,
    user as user_core,
    membership as membership_core,
    redemption as redemption_core,
)
from . import export as exporting

_invocation_args = ContextVar("invocation_args", default=())


class UserGroup(click.Group):
    def main(self, *args, **kwargs):
        requested = kwargs.pop("standalone_mode", True)
        argv = kwargs.get("args") or (args[0] if args else sys.argv[1:])
        token = _invocation_args.set(tuple(argv))
        try:
            return super().main(*args, standalone_mode=False, **kwargs)
        except CLIError as error:
            emit(error.envelope())
            if requested:
                raise SystemExit(error.exit_code)
            raise click.exceptions.Exit(error.exit_code)
        except click.ClickException as error:
            emit(
                CLIError(
                    "VALIDATION_FAILED",
                    error.format_message(),
                    2,
                    hint="使用 --help 或 schema 查看支持的用户命令",
                ).envelope()
            )
            if requested:
                raise SystemExit(2)
            raise click.exceptions.Exit(2)
        except (KeyboardInterrupt, click.Abort):
            emit(CLIError("CANCELLED", "操作已取消", 130).envelope())
            if requested:
                raise SystemExit(130)
            raise click.exceptions.Exit(130)
        except (OSError, subprocess.SubprocessError):
            emit(CLIError("LOCAL_ERROR", "本地文件或凭据操作失败", 7).envelope())
            if requested:
                raise SystemExit(7)
            raise click.exceptions.Exit(7)
        finally:
            _invocation_args.reset(token)


@click.group(cls=UserGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="aidee")
@click.option("--profile")
@click.option("--base-url")
@click.option("--team-base-url")
@click.option("--web-base")
@click.option("--api-key", help="兼容参数；推荐 auth login 隐藏输入或环境变量")
@click.option("--token", help="明确选择旧 token 模式")
@click.option("--auth-mode", type=click.Choice(["key", "token"]))
@click.option(
    "--json", "json_mode", is_flag=True, help="结构化输出（默认）；禁止自动升级"
)
@click.option(
    "--output", type=click.Choice(["json", "table", "markdown"]), default="json"
)
@click.option("--jq", help="使用已安装的系统 jq 过滤结果")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", is_flag=True)
@click.pass_context
def cli(
    ctx,
    profile,
    base_url,
    team_base_url,
    web_base,
    api_key,
    token,
    auth_mode,
    json_mode,
    output,
    jq,
    dry_run,
    yes,
):
    """Aidee 本人录音、授权团队空间、本人兑换与会员购买。"""
    if api_key and token:
        raise CLIError("VALIDATION_FAILED", "不能同时传 API Key 与 token", 2)
    if token and auth_mode == "key":
        raise CLIError("VALIDATION_FAILED", "token 与 key 模式冲突", 2)
    dry_run = dry_run or "--dry-run" in _invocation_args.get()
    json_mode = json_mode or "--json" in _invocation_args.get()
    settings = Settings(
        profile,
        api_base=base_url,
        team_base=team_base_url,
        web_base=web_base,
        api_key=api_key,
        token=token,
        auth_mode=auth_mode or ("token" if token else None),
    )
    ctx.obj = {
        "settings": settings,
        "client": Client(settings),
        "dry": dry_run,
        "yes": yes,
        "mode": output,
        "jq": jq,
        "json": json_mode,
    }
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    # Offline discovery and explicit upgrade/authentication never trigger background work.
    if (
        ctx.invoked_subcommand
        not in ("update", "schema", "skills", "config", "profile", "auth")
        and not dry_run
    ):
        from .updates import startup_check

        result = startup_check(settings, explicit_json=json_mode)
        if result is not None:
            result_out(ctx, result)
            ctx.exit(0)


def state(ctx):
    return ctx.find_root().obj


def result_out(ctx, data, meta=None):
    obj = state(ctx)
    value = {"ok": True, "data": data}
    if meta is not None:
        value["meta"] = meta
    emit(
        value,
        mode="json" if obj["json"] or ctx.params.get("json_mode") else obj["mode"],
        jq=obj["jq"],
    )


def preview(ctx, name, params=None, body=None):
    info = REGISTRY[name]
    result_out(
        ctx,
        {
            "dryRun": True,
            "operation": name,
            "service": info["service"],
            "method": info["method"],
            "path": info["path"],
            "params": params or {},
            "body": body or {},
            "credential": "***",
        },
    )


def is_dry(ctx, value=False):
    return value or state(ctx)["dry"]


def confirm(ctx, message, yes=False):
    if yes or state(ctx)["yes"]:
        return
    if not sys.stdin.isatty():
        raise CLIError(
            "CONFIRMATION_REQUIRED",
            "非交互写操作需要明确确认",
            4,
            hint="取得用户授权后添加 --yes",
        )
    if not click.confirm(message, default=False, err=True):
        raise CLIError("CANCELLED", "操作已取消", 130)


def corecall(ctx, fn, *args, **kwargs):
    obj = state(ctx)
    marker = active_client.set(obj["client"])
    try:
        return fn(obj["settings"].values["api_base"], None, *args, **kwargs)["data"]
    finally:
        active_client.reset(marker)


def options(fn):
    for decorator in reversed(
        [
            click.option("--json", "json_mode", is_flag=True),
            click.option("--raw", is_flag=True),
            click.option("--dry-run", is_flag=True),
        ]
    ):
        fn = decorator(fn)
    return fn


def list_options(fn):
    for decorator in reversed(
        [
            click.option("--page", type=click.IntRange(1), default=1),
            click.option("--limit", "--size", type=click.IntRange(1, 200), default=20),
            click.option("--all", "all_pages", is_flag=True),
            click.option(
                "--offset",
                type=click.IntRange(0),
                default=0,
                help="续读meta.next.offset；仅跳过当前页已有条目",
            ),
            click.option("--max-pages", type=click.IntRange(1, 100), default=100),
            click.option("--max-items", type=click.IntRange(1, 5000), default=5000),
            click.option("--max-seconds", type=click.IntRange(1, 120), default=120),
        ]
    ):
        fn = decorator(fn)
    return fn


def simple(group, name, operation, path, *, service="aidee", team=False, core=None):
    record(operation, "GET", path, service=service)

    @group.command(name)
    @options
    @click.pass_context
    def command(ctx, json_mode, raw, dry_run):
        if is_dry(ctx, dry_run):
            return preview(ctx, operation)
        data = (
            corecall(ctx, core)
            if core and not raw
            else state(ctx)["client"].request(
                "GET", path, service=service, team=team, raw=raw
            )
        )
        result_out(ctx, data)

    return command


@cli.group()
def auth():
    """已有 Key 导入、浏览器授权、状态和本机退出。"""


@auth.command("login")
@click.option("--browser", is_flag=True)
@click.option(
    "--scope",
    "scopes",
    type=click.Choice(["read", "write"]),
    multiple=True,
    default=("read",),
    help="浏览器授权范围；write包含read，仍需网页确认",
)
@click.option("--no-browser", is_flag=True, help="仅显示PKCE授权地址")
@click.option("--key", help="兼容导入参数；推荐隐藏输入")
@click.option("--key-stdin", is_flag=True)
@click.option("--api-base")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def auth_login(ctx, browser, scopes, no_browser, key, key_stdin, api_base, dry_run):
    obj = state(ctx)
    settings = obj["settings"]
    if "write" in scopes and not browser:
        raise CLIError(
            "VALIDATION_FAILED",
            "导入已有Key不能增加权限；请使用 --browser --scope write 明确授权",
            2,
        )
    if browser and (key or key_stdin):
        raise CLIError("VALIDATION_FAILED", "浏览器登录与Key导入不能混用", 2)
    if is_dry(ctx, dry_run):
        return result_out(
            ctx,
            {
                "dryRun": True,
                "operation": "auth.login",
                "method": "browser" if browser else "existing-key",
            },
        )
    if api_base:
        from .settings import validate_base

        settings.values["api_base"] = validate_base(api_base)
    if browser:
        settings.auth_mode = "key"
        data = login_browser(settings, no_browser=no_browser, scopes=scopes)
    else:
        secret = key or (
            sys.stdin.readline().strip()
            if key_stdin
            else settings.explicit_token
            if settings.auth_mode == "token"
            else settings.explicit_key or os.environ.get("AIDEE_API_KEY")
        )
        if not secret:
            if not sys.stdin.isatty():
                raise CLIError(
                    "MISSING_CREDENTIALS", "请使用 --key-stdin 或配置 AIDEE_API_KEY", 3
                )
            secret = click.prompt(
                "本人 Token" if settings.auth_mode == "token" else "本人已有 API Key",
                hide_input=True,
                err=True,
            )
        path = (
            "/users/information"
            if settings.auth_mode == "token"
            else "/integration/keys/current"
        )
        metadata = Client(settings, secret=secret).request("GET", path)
        require_identity(metadata, token_mode=settings.auth_mode == "token")
        store = credentials_set(settings, secret)
        data = {
            "loggedIn": True,
            "method": "existing-key",
            "profile": settings.name,
            "keyStore": store,
            **safe_metadata(metadata),
        }
    settings.profile.update(settings.binding())
    settings.profile.pop("team_id", None)
    settings.profile["auth_mode"] = settings.auth_mode
    settings.save()
    result_out(ctx, data)


@auth.command("status")
@click.option("--verify", is_flag=True)
@click.pass_context
def auth_status(ctx, verify):
    settings = state(ctx)["settings"]
    result = {
        "profile": settings.name,
        "configured": bool(settings.credential()),
        "verified": False,
        "authMode": settings.auth_mode,
    }
    if verify and not is_dry(ctx):
        path = (
            "/users/information"
            if settings.auth_mode == "token"
            else "/integration/keys/current"
        )
        result.update(
            safe_metadata(
                require_identity(
                    state(ctx)["client"].request("GET", path),
                    token_mode=settings.auth_mode == "token",
                )
            )
        )
        result["verified"] = True
    result_out(ctx, result)


@auth.command("logout")
@click.pass_context
def auth_logout(ctx):
    cleared = credentials_delete(state(ctx)["settings"].name) if not is_dry(ctx) else {}
    result_out(
        ctx,
        {
            "loggedOut": not is_dry(ctx),
            **cleared,
            "dryRun": is_dry(ctx),
            "serverRevoked": False,
            "environmentCredentialPresent": bool(
                os.environ.get("AIDEE_API_KEY") or os.environ.get("AIDEE_TOKEN")
            ),
        },
    )


@auth.command("migrate")
@click.option(
    "--session-file", type=click.Path(exists=True, dir_okay=False), required=True
)
@click.option("--yes", is_flag=True)
@click.pass_context
def auth_migrate(ctx, session_file, yes):
    if is_dry(ctx):
        return result_out(ctx, {"dryRun": True, "operation": "auth.migrate"})
    confirm(ctx, "验证并导入指定旧配置？原文件会保留。", yes)
    legacy = load_json(session_file, {})
    secret = legacy.get("api_key")
    if not secret:
        raise CLIError(
            "VALIDATION_FAILED", "旧文件中没有 API Key；token 请显式选择兼容模式", 2
        )
    settings = state(ctx)["settings"]
    if legacy.get("base_url") != settings.values["api_base"]:
        raise CLIError("AUTH_ORIGIN_CHANGED", "旧服务地址与当前profile不一致", 3)
    metadata = Client(settings, secret=secret).request(
        "GET", "/integration/keys/current"
    )
    require_identity(metadata)
    store = credentials_set(settings, secret)
    settings.profile.update(settings.binding())
    settings.profile.pop("team_id", None)
    settings.profile["auth_mode"] = settings.auth_mode
    settings.save()
    result_out(ctx, {"migrated": True, "keyStore": store, **safe_metadata(metadata)})


@cli.group("config")
def config_group():
    """当前 profile 的配置和升级偏好。"""


@config_group.command("show")
@click.pass_context
def config_show(ctx):
    result_out(ctx, state(ctx)["settings"].show())


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx, key, value):
    if not is_dry(ctx):
        state(ctx)["settings"].set(key, value)
    result_out(ctx, {"key": key, "value": value, "dryRun": is_dry(ctx)})


@config_group.command("set-api-key", hidden=True)
@click.argument("key", required=False)
@click.pass_context
def set_api_key(ctx, key):
    ctx.invoke(
        auth_login,
        key=key,
        browser=False,
        no_browser=False,
        key_stdin=False,
        api_base=None,
        dry_run=False,
    )


@config_group.command("set-token", hidden=True)
@click.argument("token")
@click.pass_context
def set_token(ctx, token):
    state(ctx)["settings"].auth_mode = "token"
    state(ctx)["settings"].explicit_token = token
    ctx.invoke(
        auth_login,
        key=None,
        browser=False,
        no_browser=False,
        key_stdin=False,
        api_base=None,
        dry_run=False,
    )


@config_group.command("set-base-url", hidden=True)
@click.argument("url")
@click.pass_context
def set_base_url(ctx, url):
    ctx.invoke(config_set, key="api_base", value=url)


@cli.group()
def profile():
    """环境隔离；切换不会复用其他origin的凭据。"""


@profile.command("list")
@click.pass_context
def profile_list(ctx):
    settings = state(ctx)["settings"]
    result_out(
        ctx, {"current": settings.name, "profiles": list(settings.data["profiles"])}
    )


@profile.command("use")
@click.argument("name")
@click.pass_context
def profile_use(ctx, name):
    settings = Settings(name)
    if not is_dry(ctx):
        settings.data["currentProfile"] = name
        settings.save()
    result_out(ctx, {"profile": name, "dryRun": is_dry(ctx)})


simple(cli, "whoami", "whoami", "/users/information", core=user_core.info)


@cli.command("doctor")
@click.pass_context
def doctor(ctx):
    if is_dry(ctx):
        return result_out(ctx, {"dryRun": True, "operation": "doctor"})
    checks = []
    settings = state(ctx)["settings"]
    client = state(ctx)["client"]
    try:
        configured = bool(settings.credential())
        checks.append({"name": "credentials", "configured": configured})
    except CLIError as error:
        return result_out(
            ctx,
            {
                "version": __version__,
                "configuration": settings.show(),
                "healthy": False,
                "checks": [
                    {
                        "name": "credentials",
                        "configured": False,
                        "errorCode": error.code,
                        "hint": error.hint,
                    }
                ],
            },
        )
    personal_path = (
        "/users/information"
        if settings.auth_mode == "token"
        else "/integration/keys/current"
    )
    for name, path, service in [
        ("personal", personal_path, "aidee"),
        ("team", "/team/aidee/teams/joined", "team"),
    ]:
        try:
            data = client.request("GET", path, service=service, timeout=5)
            check = {"name": name, "reachable": True, "authenticated": True}
            if service == "aidee":
                require_identity(data, token_mode=settings.auth_mode == "token")
                check.update(safe_metadata(data))
            elif isinstance(data, list):
                check["joinedTeams"] = len(data)
                if not data:
                    check["hint"] = "尚未加入团队；本人录音仍可正常使用"
            checks.append(check)
        except CLIError as error:
            checks.append(
                {
                    "name": name,
                    "reachable": error.exit_code in (3, 4, 5),
                    "authenticated": False,
                    "errorCode": error.code,
                    "upstreamCode": error.upstream,
                    "hint": error.hint,
                }
            )
    result_out(
        ctx,
        {
            "version": __version__,
            "configuration": settings.show(),
            "healthy": configured and all(x.get("authenticated", True) for x in checks),
            "checks": checks,
        },
    )


@cli.group("recording")
def recordings():
    """本人录音与已有内容。"""


@recordings.command("list")
@options
@list_options
@click.option("--keyword")
@click.option("--folder")
@click.option("--status")
@click.option(
    "--period", type=click.Choice(["today", "yesterday", "this_week", "last_week"])
)
@click.option(
    "--week", help="指定ISO周YYYY-Www，按timezone周一到周日；不与period/from/to混用"
)
@click.option("--from", "from_time")
@click.option("--to", "to_time")
@click.option("--timezone", default="Asia/Taipei")
@click.pass_context
def recording_list(
    ctx,
    json_mode,
    raw,
    dry_run,
    page,
    limit,
    all_pages,
    offset,
    max_pages,
    max_items,
    max_seconds,
    keyword,
    folder,
    status,
    period,
    week,
    from_time,
    to_time,
    timezone,
):
    params = {"page": page, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    if folder:
        params.update(recordingsGroupCode=folder, folderMode=True)
    if status:
        params["status"] = status
    try:
        zone = ZoneInfo(timezone)
        api_zone = ZoneInfo(state(ctx)["settings"].values["apiTimezone"])
    except ZoneInfoNotFoundError:
        raise CLIError("VALIDATION_FAILED", "未知时区", 2) from None
    if week and (period or from_time or to_time):
        raise CLIError("VALIDATION_FAILED", "week与period/from/to不能同时使用", 2)
    if period and (from_time or to_time):
        raise CLIError("VALIDATION_FAILED", "period与from/to不能同时使用", 2)
    if period or week:
        if week:
            try:
                if not re.fullmatch(r"[0-9]{4}-W[0-9]{2}", week):
                    raise ValueError()
                year, number = week.split("-W")
                start = datetime.fromisocalendar(int(year), int(number), 1).replace(
                    tzinfo=zone
                )
            except ValueError:
                raise CLIError(
                    "VALIDATION_FAILED",
                    "无效ISO周；格式为YYYY-Www，周号必须在该ISO年内有效",
                    2,
                ) from None
        else:
            now = datetime.now(zone)
            start = datetime.combine(now.date(), dt_time(), zone)
            if period in ("this_week", "last_week"):
                start -= timedelta(days=start.weekday())
            if period == "yesterday":
                start -= timedelta(days=1)
            if period == "last_week":
                start -= timedelta(days=7)
        end = (
            start
            + timedelta(days=7 if week or "week" in period else 1)
            - timedelta(microseconds=1)
        )
        params.update(
            startTime=start.astimezone(api_zone).replace(tzinfo=None).isoformat(),
            endTime=end.astimezone(api_zone).replace(tzinfo=None).isoformat(),
        )
    for key, value in [("startTime", from_time), ("endTime", to_time)]:
        if value:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise CLIError("VALIDATION_FAILED", "时间必须是ISO格式", 2) from None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=zone)
            params[key] = parsed.astimezone(api_zone).replace(tzinfo=None).isoformat()
    if (
        "startTime" in params
        and "endTime" in params
        and params["startTime"] > params["endTime"]
    ):
        raise CLIError("VALIDATION_FAILED", "开始时间不能晚于结束时间", 2)
    if is_dry(ctx, dry_run):
        return preview(ctx, "recording.list", params)
    client = state(ctx)["client"]
    if raw:
        if all_pages or offset:
            raise CLIError("VALIDATION_FAILED", "raw不能与all或offset同时使用", 2)
        return result_out(
            ctx, client.request("GET", "/recordings", params=params, raw=True)
        )
    data, meta = pages(
        lambda query, deadline: client.request(
            "GET", "/recordings", params=query, deadline=deadline
        ),
        params,
        all_pages=all_pages,
        offset=offset,
        max_pages=max_pages,
        max_items=max_items,
        max_seconds=max_seconds,
    )
    result_out(ctx, data, meta)


record(
    "recording.list",
    "GET",
    "/recordings",
    params=[
        "page",
        "limit",
        "keyword",
        "folder",
        "status",
        "period",
        "week",
        "from",
        "to",
        "timezone",
        "all",
        "max-pages",
        "max-items",
        "max-seconds",
    ],
)


@recordings.command("get")
@click.argument("code")
@options
@click.pass_context
def recording_get(ctx, code, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "recording.get", {"code": code})
    data = (
        state(ctx)["client"].request("GET", f"/recordings/{segment(code)}", raw=True)
        if raw
        else corecall(ctx, recording_core.get, code)
    )
    result_out(ctx, data)


record("recording.get", "GET", "/recordings/{code}")


def fetch_transcript(
    ctx,
    code,
    space=None,
    *,
    page=1,
    limit=100,
    all_pages=True,
    offset=0,
    max_pages=100,
    max_items=5000,
    max_seconds=120,
):
    client = state(ctx)["client"]
    path = (
        f"/team/aidee/spaces/{segment(space)}/recordings/{segment(code)}/text"
        if space
        else "/recordings/text/page"
    )
    params = {"page": page, "limit": limit, "orderDirection": "asc"}
    if not space:
        params["recordingCode"] = code
    return pages(
        lambda query, deadline: client.request(
            "GET",
            path,
            service="team" if space else "aidee",
            team=bool(space),
            params=query,
            deadline=deadline,
        ),
        params,
        all_pages=all_pages,
        offset=offset,
        max_pages=max_pages,
        max_items=max_items,
        max_seconds=max_seconds,
    )


@recordings.command("transcript")
@click.argument("code")
@options
@list_options
@click.pass_context
def recording_transcript(
    ctx,
    code,
    json_mode,
    raw,
    dry_run,
    page,
    limit,
    all_pages,
    offset,
    max_pages,
    max_items,
    max_seconds,
):
    if is_dry(ctx, dry_run):
        return preview(
            ctx,
            "recording.transcript",
            {"recordingCode": code, "page": page, "limit": limit},
        )
    if raw and (all_pages or offset):
        raise CLIError("VALIDATION_FAILED", "raw不能与all或offset同时使用", 2)
    if raw:
        return result_out(
            ctx,
            state(ctx)["client"].request(
                "GET",
                "/recordings/text/page",
                params={"recordingCode": code, "page": page, "limit": limit},
                raw=True,
            ),
        )
    data, meta = fetch_transcript(
        ctx,
        code,
        page=page,
        limit=limit,
        all_pages=all_pages,
        offset=offset,
        max_pages=max_pages,
        max_items=max_items,
        max_seconds=max_seconds,
    )
    result_out(ctx, data, meta)


record(
    "recording.transcript",
    "GET",
    "/recordings/text/page",
    params=["code", "page", "limit", "all"],
)


@cli.group("summary")
def summaries():
    """已有个人总结；不会触发AI。"""


@summaries.command("list")
@click.argument("code")
@options
@click.pass_context
def summary_list(ctx, code, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "summary.list", {"recordingCode": code})
    data = (
        state(ctx)["client"].request(
            "GET", f"/recordings/summaries/recording/{segment(code)}", raw=True
        )
        if raw
        else corecall(ctx, summary_core.list_by_recording, code)
    )
    result_out(ctx, data)


record("summary.list", "GET", "/recordings/summaries/recording/{code}")


@summaries.command("get")
@click.argument("summary_id")
@options
@click.pass_context
def summary_get(ctx, summary_id, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "summary.get", {"summaryId": summary_id})
    result_out(
        ctx,
        state(ctx)["client"].request(
            "GET", f"/recordings/summaries/{segment(summary_id)}", raw=True
        )
        if raw
        else corecall(ctx, summary_core.get, summary_id),
    )


record("summary.get", "GET", "/recordings/summaries/{summaryId}")


@cli.group("folder")
def folders():
    """个人目录只读。"""


simple(
    folders,
    "list",
    "folder.list",
    "/recording-groups/user/all",
    core=folder_core.list_all,
)
simple(
    folders, "tree", "folder.tree", "/recording-groups/tree/all", core=folder_core.tree
)


@cli.group()
def team():
    """本人已加入的团队；不管理成员。"""


simple(team, "list", "team.list", "/team/aidee/teams/joined", service="team")
simple(
    team,
    "current",
    "team.current",
    "/team/aidee/teams/current",
    service="team",
    team=True,
)
simple(
    team,
    "entitlements",
    "team.entitlements",
    "/team/aidee/teams/current/entitlements",
    service="team",
    team=True,
)


@team.command("use")
@click.argument("team_id")
@click.pass_context
def team_use(ctx, team_id):
    if is_dry(ctx):
        return result_out(ctx, {"dryRun": True, "teamId": team_id})
    joined = state(ctx)["client"].request(
        "GET", "/team/aidee/teams/joined", service="team"
    )
    if not isinstance(joined, list) or not any(
        str(row.get("teamId")) == team_id for row in joined
    ):
        raise CLIError("PERMISSION_DENIED", "当前账号未加入该团队", 4)
    state(ctx)["settings"].set("team_id", team_id)
    result_out(ctx, {"teamId": team_id, "localSelectionOnly": True})


record("team.use", "LOCAL", "profile.team_id", service="local")


@cli.group()
def space():
    """所选团队内有权访问的TEAM空间。"""


@space.command("list")
@options
@click.pass_context
def space_list(ctx, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "space.list")
    data = state(ctx)["client"].request(
        "GET", "/team/aidee/spaces", service="team", team=True, raw=raw
    )
    rows = data.get("data") if raw else data
    if not isinstance(rows, list):
        raise CLIError("BUSINESS_REJECTED", "空间列表响应类型不正确", 5)
    team_id = str(state(ctx)["settings"].profile.get("team_id"))
    rows = [
        row
        for row in rows
        if row.get("spaceType") == "TEAM" and str(row.get("teamId")) == team_id
    ]
    result_out(ctx, {**data, "data": rows} if raw else rows)


record("space.list", "GET", "/team/aidee/spaces", service="team")


@space.command("get")
@click.argument("space_id")
@options
@click.pass_context
def space_get(ctx, space_id, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "space.get", {"spaceId": space_id})
    data = state(ctx)["client"].request(
        "GET",
        f"/team/aidee/spaces/{segment(space_id)}",
        service="team",
        team=True,
        raw=raw,
    )
    projected = data.get("data") if raw else data
    if projected.get("spaceType") != "TEAM" or str(projected.get("teamId")) != str(
        state(ctx)["settings"].profile.get("team_id")
    ):
        raise CLIError("PERMISSION_DENIED", "该入口仅提供TEAM空间", 4)
    result_out(ctx, data)


record("space.get", "GET", "/team/aidee/spaces/{spaceId}", service="team")


@space.group("recording")
def space_recordings():
    """空间普通录音及合并总结当前版本。"""


@space_recordings.command("list")
@click.option("--space", "space_id", required=True)
@click.option(
    "--share-origin", type=click.Choice(["ALL", "MINE", "OTHERS"]), default="ALL"
)
@click.option("--cursor-sort-time")
@click.option("--cursor-id")
@options
@list_options
@click.pass_context
def space_recording_list(
    ctx,
    space_id,
    share_origin,
    cursor_sort_time,
    cursor_id,
    json_mode,
    raw,
    dry_run,
    page,
    limit,
    all_pages,
    offset,
    max_pages,
    max_items,
    max_seconds,
):
    if bool(cursor_sort_time) != bool(cursor_id):
        raise CLIError("VALIDATION_FAILED", "游标时间与ID必须同时提供", 2)
    params = {"page": page, "limit": limit, "shareOrigin": share_origin, "cursor": True}
    if cursor_id:
        params.update(cursorSortTime=cursor_sort_time, cursorId=cursor_id)
    if is_dry(ctx, dry_run):
        return preview(ctx, "space.recording.list", {"spaceId": space_id, **params})
    path = f"/team/aidee/spaces/{segment(space_id)}/recordings"
    client = state(ctx)["client"]
    if raw:
        if all_pages or offset:
            raise CLIError("VALIDATION_FAILED", "raw不能与all或offset同时使用", 2)
        return result_out(
            ctx,
            client.request(
                "GET", path, service="team", team=True, params=params, raw=True
            ),
        )
    data, meta = pages(
        lambda query, deadline: client.request(
            "GET", path, service="team", team=True, params=query, deadline=deadline
        ),
        params,
        cursor=True,
        all_pages=all_pages,
        offset=offset,
        max_pages=max_pages,
        max_items=max_items,
        max_seconds=max_seconds,
    )
    result_out(ctx, data, meta)


record(
    "space.recording.list",
    "GET",
    "/team/aidee/spaces/{spaceId}/recordings",
    service="team",
    params=[
        "space",
        "share-origin",
        "cursor-id",
        "cursor-sort-time",
        "page",
        "limit",
        "all",
    ],
)


def space_detail(ctx, space_id, code, suffix="", raw=False):
    return state(ctx)["client"].request(
        "GET",
        f"/team/aidee/spaces/{segment(space_id)}/recordings/{segment(code)}" + suffix,
        service="team",
        team=True,
        raw=raw,
    )


for command_name, suffix in [("get", ""), ("summaries", "/summaries")]:

    def register_space_read(name=command_name, tail=suffix):
        @space_recordings.command(name)
        @click.argument("code")
        @click.option("--space", "space_id", required=True)
        @options
        @click.pass_context
        def command(ctx, code, space_id, json_mode, raw, dry_run):
            if is_dry(ctx, dry_run):
                return preview(
                    ctx, "space.recording." + name, {"spaceId": space_id, "code": code}
                )
            result_out(ctx, space_detail(ctx, space_id, code, tail, raw))

        record(
            "space.recording." + name,
            "GET",
            "/team/aidee/spaces/{spaceId}/recordings/{code}" + tail,
            service="team",
        )

    register_space_read()


@space_recordings.command("summary")
@click.argument("code")
@click.argument("summary_id")
@click.option("--space", "space_id", required=True)
@options
@click.pass_context
def space_summary(ctx, code, summary_id, space_id, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(
            ctx,
            "space.recording.summary",
            {"spaceId": space_id, "code": code, "summaryId": summary_id},
        )
    result_out(
        ctx, space_detail(ctx, space_id, code, "/summaries/" + segment(summary_id), raw)
    )


record(
    "space.recording.summary",
    "GET",
    "/team/aidee/spaces/{spaceId}/recordings/{code}/summaries/{summaryId}",
    service="team",
)


@space_recordings.command("transcript")
@click.argument("code")
@click.option("--space", "space_id", required=True)
@options
@list_options
@click.pass_context
def space_transcript(
    ctx,
    code,
    space_id,
    json_mode,
    raw,
    dry_run,
    page,
    limit,
    all_pages,
    offset,
    max_pages,
    max_items,
    max_seconds,
):
    if is_dry(ctx, dry_run):
        return preview(
            ctx, "space.recording.transcript", {"spaceId": space_id, "code": code}
        )
    if raw and (all_pages or offset):
        raise CLIError("VALIDATION_FAILED", "raw不能与all或offset同时使用", 2)
    if raw:
        return result_out(
            ctx,
            state(ctx)["client"].request(
                "GET",
                f"/team/aidee/spaces/{segment(space_id)}/recordings/{segment(code)}/text",
                service="team",
                team=True,
                params={"page": page, "limit": limit},
                raw=True,
            ),
        )
    data, meta = fetch_transcript(
        ctx,
        code,
        space_id,
        page=page,
        limit=limit,
        all_pages=all_pages,
        offset=offset,
        max_pages=max_pages,
        max_items=max_items,
        max_seconds=max_seconds,
    )
    result_out(ctx, data, meta)


record(
    "space.recording.transcript",
    "GET",
    "/team/aidee/spaces/{spaceId}/recordings/{code}/text",
    service="team",
)


def export_command(group, team_space=False):
    @group.command("export")
    @click.argument("code")
    @click.option("--space", "space_id", required=team_space, hidden=not team_space)
    @click.option(
        "--content", type=click.Choice(["transcript", "summary"]), default="transcript"
    )
    @click.option("--summary-id")
    @click.option(
        "--format", "format_", type=click.Choice(["txt", "md", "json"]), default="md"
    )
    @click.option("--output-file", type=click.Path(dir_okay=False))
    @click.option("--overwrite", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @click.pass_context
    def command(
        ctx,
        code,
        space_id,
        content,
        summary_id,
        format_,
        output_file,
        overwrite,
        dry_run,
    ):
        name = "space.recording.export" if team_space else "recording.export"
        if is_dry(ctx, dry_run):
            return preview(
                ctx,
                name,
                {
                    "code": code,
                    "spaceId": space_id,
                    "content": content,
                    "format": format_,
                    "outputFile": output_file,
                },
            )
        if content == "transcript":
            data, meta = fetch_transcript(ctx, code, space_id if team_space else None)
            if meta["truncated"]:
                raise CLIError(
                    "BUSINESS_REJECTED",
                    "内容超过单次导出上限，未写入文件",
                    5,
                    meta=meta,
                )
        else:
            if not summary_id:
                raise CLIError("VALIDATION_FAILED", "导出总结需要 --summary-id", 2)
            data = (
                space_detail(ctx, space_id, code, "/summaries/" + segment(summary_id))
                if team_space
                else corecall(ctx, summary_core.get, summary_id)
            )
        rendered = exporting.render(data, format_)
        if output_file:
            result_out(ctx, exporting.write(rendered, output_file, overwrite))
        else:
            click.echo(rendered, nl=False)

    record(
        "space.recording.export" if team_space else "recording.export",
        "GET",
        "已有内容原接口",
        service="team" if team_space else "aidee",
    )


export_command(recordings)
export_command(space_recordings, True)


@cli.group("membership")
def membership():
    """本人会员、真实套餐和付款入口。"""


simple(
    membership,
    "current",
    "membership.current",
    "/users/membership/current",
    core=user_core.membership_current,
)
simple(
    membership,
    "plans",
    "membership.plans",
    "/memberships/plans",
    core=membership_core.plans,
)
simple(
    membership,
    "quota",
    "membership.quota",
    "/memberships/quota/overview",
    core=membership_core.quota,
)


def owned_order_view(ctx, data):
    if not isinstance(data, dict) or not data.get("orderNo"):
        return data
    # This route still requires the purchasing account's Web login; orderNo is never an authorization token.
    return {
        **data,
        "checkoutUrl": state(ctx)["settings"].values["web_base"]
        + "/cli/checkout/"
        + segment(data["orderNo"]),
    }


@membership.command("checkout")
@click.option("--plan", "plan_id", required=True, help="真实发布的packageVersionId")
@click.option(
    "--request-id", help="恢复重试时使用原requestId；不填写则创建新的本次购买意图"
)
@click.option("--yes", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def checkout(ctx, plan_id, request_id, yes, dry_run):
    if is_dry(ctx, dry_run):
        return preview(
            ctx,
            "membership.checkout",
            body={
                "packageVersionId": plan_id,
                "expectedPriceMinor": "<由真实套餐报价>",
                "requestId": request_id or "<本次购买意图>",
            },
        )
    client = state(ctx)["client"]
    settings = state(ctx)["settings"]
    identity = client.request("GET", "/integration/keys/current")
    if not identity.get("effectivePermissions", {}).get("checkoutSelf"):
        raise CLIError(
            "PERMISSION_DENIED",
            "此Key未获准本人下单",
            4,
            hint="aidee auth login --browser --scope write"
            if "write" not in identity.get("scopes", [])
            else "该Key的调用策略不允许本人下单，请检查原Key管理权限",
        )
    if request_id:
        # Re-running an existing intent is a read-only recovery, never a generic POST retry.
        result_out(
            ctx,
            owned_order_view(
                ctx,
                client.request(
                    "GET", "/memberships/orders/by-request/" + segment(request_id)
                ),
            ),
            {"recovered": True, "createdNewOrder": False},
        )
        return
    plans = corecall(ctx, membership_core.plans)
    if not isinstance(plans, list):
        raise CLIError("BUSINESS_REJECTED", "套餐目录响应缺少约定的商品列表", 5)
    selected = next(
        (p for p in plans if str(p.get("packageVersionId")) == plan_id), None
    )
    if selected is None or selected.get("purchasable") is False:
        raise CLIError("BUSINESS_REJECTED", "套餐不可购买或已变更", 5)
    price = selected.get("priceMinor")
    if price is None or not str(price).isdigit():
        raise CLIError("BUSINESS_REJECTED", "套餐没有有效的分金额报价", 5)
    click.echo(
        "购买确认："
        + json.dumps(
            {
                k: selected[k]
                for k in (
                    "name",
                    "packageName",
                    "packageVersionId",
                    "priceMinor",
                    "currency",
                    "durationDays",
                    "action",
                    "reason",
                    "description",
                )
                if k in selected
            },
            ensure_ascii=False,
        ),
        err=True,
    )
    confirm(ctx, "确认创建本人付款订单？付款需自行完成。", yes)
    rid = str(uuid.uuid4())
    path = directory() / "requests" / settings.name / (rid + ".json")
    intent = {
        "requestId": rid,
        "packageVersionId": plan_id,
        "expectedPriceMinor": str(price),
        "state": "PENDING",
        "binding": settings.binding(),
        "userCenterUserId": identity.get("userCenterUserId"),
    }
    atomic_json(path, intent)
    try:
        response = client.request(
            "POST",
            "/memberships/checkout",
            body={
                "packageVersionId": plan_id,
                "expectedPriceMinor": str(price),
                "requestId": rid,
            },
        )
    except CLIError as error:
        intent["state"] = "UNKNOWN"
        atomic_json(path, intent)
        error.meta = {"requestId": rid, "next": "aidee order recover " + rid}
        raise
    intent.update(state="READY", orderNo=response.get("orderNo"))
    atomic_json(path, intent)
    result_out(
        ctx,
        owned_order_view(ctx, {"requestId": rid, **response}),
        {
            "next": "打开checkoutUrl并登录同一购买账号自行付款；order wait查看支付与到账。个人会员不一定提升团队权益。"
        },
    )


record(
    "membership.checkout",
    "POST",
    "/memberships/checkout",
    risk="write",
    params=["plan", "request-id", "yes"],
)


@cli.group("order")
def orders():
    """本人订单和原requestId恢复；不自动支付。"""


@orders.command("list")
@options
@list_options
@click.pass_context
def order_list(
    ctx,
    json_mode,
    raw,
    dry_run,
    page,
    limit,
    all_pages,
    offset,
    max_pages,
    max_items,
    max_seconds,
):
    params = {"page": page, "size": limit}
    if is_dry(ctx, dry_run):
        return preview(ctx, "order.list", params)
    client = state(ctx)["client"]
    if raw:
        if all_pages or offset:
            raise CLIError("VALIDATION_FAILED", "raw不能与all或offset同时使用", 2)
        return result_out(
            ctx, client.request("GET", "/memberships/orders", params=params, raw=True)
        )
    data, meta = pages(
        lambda query, deadline: client.request(
            "GET", "/memberships/orders", params=query, deadline=deadline
        ),
        params,
        all_pages=all_pages,
        offset=offset,
        max_pages=max_pages,
        max_items=max_items,
        max_seconds=max_seconds,
    )
    result_out(ctx, data, meta)


record("order.list", "GET", "/memberships/orders")


@orders.command("get")
@click.argument("order_no")
@options
@click.pass_context
def order_get(ctx, order_no, json_mode, raw, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "order.get", {"orderNo": order_no})
    result_out(
        ctx,
        state(ctx)["client"].request(
            "GET", "/memberships/orders/" + segment(order_no), raw=True
        )
        if raw
        else owned_order_view(ctx, corecall(ctx, membership_core.order, order_no)),
    )


record("order.get", "GET", "/memberships/orders/{orderNo}")


@orders.command("recover")
@click.argument("request_id", required=False)
@click.pass_context
def order_recover(ctx, request_id):
    settings = state(ctx)["settings"]
    if not request_id:
        intents = []
        for file in sorted((directory() / "requests" / settings.name).glob("*.json")):
            item = load_json(file, {})
            intents.append({k: item.get(k) for k in ("requestId", "orderNo", "state")})
        return result_out(ctx, intents)
    if is_dry(ctx):
        return preview(ctx, "order.recover", {"requestId": request_id})
    result_out(
        ctx, owned_order_view(ctx, corecall(ctx, membership_core.recover, request_id))
    )


record("order.recover", "GET", "/memberships/orders/by-request/{requestId}")


@orders.command("wait")
@click.argument("order_no")
@click.option("--timeout", type=click.IntRange(1, 180), default=180)
@click.pass_context
def order_wait(ctx, order_no, timeout):
    if is_dry(ctx):
        return preview(ctx, "order.wait", {"orderNo": order_no})
    deadline = time.monotonic() + timeout
    interval = 3
    data = None
    while time.monotonic() < deadline:
        data = state(ctx)["client"].request(
            "GET", "/memberships/orders/" + segment(order_no), deadline=deadline
        )
        status = str(data.get("status", data.get("orderStatus", ""))).upper()
        fulfillment = str(data.get("fulfillmentStatus", "UNKNOWN")).upper()
        if fulfillment in ("FAILED", "FAILURE"):
            return result_out(
                ctx,
                data,
                {
                    "paymentStatus": status,
                    "fulfillmentStatus": fulfillment,
                    "fulfillmentFailed": True,
                    "paymentFailed": False,
                    "next": "aidee order get " + order_no,
                    "hint": "权益发放失败，请查询同一订单或联系支持；不要重新下单或付款",
                },
            )
        if fulfillment == "SUCCESS" or status in (
            "CANCELLED",
            "CLOSED",
            "EXPIRED",
            "FAILED",
        ):
            return result_out(
                ctx, data, {"paymentStatus": status, "fulfillmentStatus": fulfillment}
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))
        interval = min(10, interval * 1.5)
    result_out(
        ctx,
        data,
        {
            "timedOut": True,
            "paymentStatus": str(
                (data or {}).get("status", (data or {}).get("orderStatus", "UNKNOWN"))
            ).upper(),
            "fulfillmentStatus": str(
                (data or {}).get("fulfillmentStatus", "UNKNOWN")
            ).upper(),
            "next": "aidee order get " + order_no,
            "paymentFailed": False,
        },
    )


record("order.wait", "GET", "/memberships/orders/{orderNo}")


@cli.group("redemption")
def redemption():
    """仅本人预览、兑换与记录。"""


def _without_redeem_secret(value, secret):
    if isinstance(value, dict):
        return {
            k: _without_redeem_secret(v, secret)
            for k, v in value.items()
            if k not in ("code", "redemptionCode")
        }
    if isinstance(value, list):
        return [_without_redeem_secret(v, secret) for v in value]
    return value.replace(secret, "***") if isinstance(value, str) else value


def obtain_code(value):
    if value:
        return value
    if not sys.stdin.isatty():
        raise CLIError("VALIDATION_FAILED", "非交互请输入 --code-stdin", 2)
    return click.prompt("兑换码", hide_input=True, err=True)


@redemption.command("preview")
@click.argument("code", required=False)
@click.option("--code-stdin", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def redemption_preview(ctx, code, code_stdin, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "redemption.preview", {"code": "***"})
    value = obtain_code(sys.stdin.readline().strip() if code_stdin else code)
    result_out(
        ctx,
        _without_redeem_secret(
            corecall(ctx, redemption_core.code_detail, value), value
        ),
    )


record("redemption.preview", "GET", "/recordings/redemption/code-detail")


@redemption.command("redeem")
@click.argument("code", required=False)
@click.option("--code-stdin", is_flag=True)
@click.option("--yes", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def redemption_redeem(ctx, code, code_stdin, yes, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "redemption.redeem", body={"code": "***"})
    value = obtain_code(sys.stdin.readline().strip() if code_stdin else code)
    client = state(ctx)["client"]
    identity = client.request("GET", "/integration/keys/current")
    if not identity.get("effectivePermissions", {}).get("redeemSelf"):
        raise CLIError(
            "PERMISSION_DENIED",
            "此Key未获准本人兑换",
            4,
            hint="aidee auth login --browser --scope write"
            if "write" not in identity.get("scopes", [])
            else "该Key的调用策略不允许本人兑换，请检查原Key管理权限",
        )
    benefit = corecall(ctx, redemption_core.code_detail, value)
    benefit = _without_redeem_secret(benefit, value)
    click.echo("兑换预览：" + json.dumps(benefit, ensure_ascii=False), err=True)
    confirm(ctx, "确认将上述权益兑换给本人？", yes)
    result_out(
        ctx,
        client.request(
            "POST",
            "/recordings/redemption/redeem",
            body={"code": value, "redeemSource": "aideeApp"},
        ),
    )


record(
    "redemption.redeem",
    "POST",
    "/recordings/redemption/redeem",
    risk="write",
    params=["code-stdin", "yes"],
)


@redemption.command("records")
@click.option("--redeem-source", default="aideeApp")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def redemption_records(ctx, redeem_source, dry_run):
    if is_dry(ctx, dry_run):
        return preview(ctx, "redemption.records", {"redeemSource": redeem_source})
    result_out(
        ctx, corecall(ctx, redemption_core.list_records, redeem_source=redeem_source)
    )


record("redemption.records", "GET", "/recordings/redemption/records")


@cli.command("schema")
@click.argument("operation", required=False)
@click.pass_context
def schema(ctx, operation):
    if operation and operation not in REGISTRY:
        raise CLIError(
            "VALIDATION_FAILED", "未知用户命令", 2, hint="schema 列出可用命令"
        )
    result_out(ctx, REGISTRY[operation] if operation else list(REGISTRY.values()))


@cli.group("skills")
def skills_group():
    """本产品Agent说明，不包含任何凭据。"""


@skills_group.command("list")
@click.pass_context
def skills_list(ctx):
    from .skills import names

    result_out(ctx, names())


@skills_group.command("read")
@click.argument("name")
def skills_read(name):
    from .skills import read

    click.echo(read(name), nl=False)


@skills_group.command("sync")
@click.option("--target", type=click.Path(file_okay=False))
@click.option("--dry-run", is_flag=True)
@click.pass_context
def skills_sync(ctx, target, dry_run):
    from .skills import sync

    result_out(ctx, sync(target, is_dry(ctx, dry_run)))


@cli.command("update")
@click.option("--check", is_flag=True)
@click.option(
    "--register-manager",
    type=click.Choice(["uv", "pipx"]),
    help="显式逐文件核验当前版本签名wheel，登记已有工具安装",
)
@click.option(
    "--sync-skills",
    is_flag=True,
    help="明确选择同步本CLI的Agent指南，结果与升级分别报告",
)
@click.option("--channel", type=click.Choice(["stable", "preview"]), default="stable")
@click.pass_context
def update(ctx, check, channel, sync_skills, register_manager):
    from .updates import check_update, install_update, register_installation

    if check and register_manager:
        raise CLIError("VALIDATION_FAILED", "check不会修改安装登记；请分开运行", 2)

    if is_dry(ctx):
        return result_out(
            ctx, {"dryRun": True, "operation": "update", "channel": channel}
        )
    settings = state(ctx)["settings"]
    registration = (
        register_installation(settings, register_manager) if register_manager else None
    )
    manifest = check_update(settings, channel)
    result = (
        manifest
        if check
        else install_update(settings, manifest, sync_skills=sync_skills)
    )
    if registration:
        result["registration"] = registration
    result_out(ctx, result)


# Keep explicit safe aliases; no removed operation changes meaning.
@cli.group("user", hidden=True)
def user_alias():
    pass


user_alias.add_command(cli.commands["whoami"], "info")
user_alias.add_command(membership.commands["current"], "membership")


@cli.group("session", hidden=True)
def session_alias():
    pass


session_alias.add_command(auth.commands["status"], "status")


@cli.group("group", hidden=True)
def group_alias():
    pass


group_alias.add_command(folders.commands["list"], "list")


@cli.group("template", hidden=True)
def template_alias():
    pass


template_alias.add_command(redemption.commands["redeem"], "redeem")
redemption.add_command(redemption.commands["preview"], "code-detail")
membership.add_command(membership.commands["plans"], "levels")
membership.add_command(orders.commands["list"], "orders")
membership.add_command(orders.commands["get"], "order")
membership.add_command(orders.commands["get"], "order-status")


def _complete_schema(group, prefix=""):
    for name, command in group.commands.items():
        if command.hidden:
            continue
        key = (prefix + "." + name).strip(".")
        if isinstance(command, click.Group):
            _complete_schema(command, key)
            continue
        for flag in ("--json", "--dry-run"):
            if not any(flag in getattr(p, "opts", []) for p in command.params):
                command.params.append(
                    click.Option([flag], is_flag=True, expose_value=False)
                )
        if key not in REGISTRY:
            record(key, "LOCAL", "local:" + key, service="local")
        REGISTRY[key]["description"] = command.help or ""
        REGISTRY[key]["params"] = [
            {
                "name": p.name,
                "flags": getattr(p, "opts", []),
                "required": p.required,
                "type": str(p.type),
                "default": p.default,
            }
            for p in command.params
        ]


_complete_schema(cli)


def main():
    # Machine output and redirected Skill content always use UTF-8, including Windows.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    cli(prog_name="aidee")


if __name__ == "__main__":
    main()
