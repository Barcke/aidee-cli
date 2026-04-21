"""AIDEE CLI — Main entry point."""

import os
import shlex
import sys

import click

from cli_anything.aidee import __version__
from cli_anything.aidee.core.session import get_api_key, get_base_url, get_token
from cli_anything.aidee.core.config import set_api_key, set_base_url, set_token, show as config_show, clear as config_clear
from cli_anything.aidee.core.recording import (
    create as recording_create,
    get as recording_get,
    update as recording_update,
    delete as recording_delete,
    list_recordings,
    get_speakers,
    update_ai_summary,
    get_summary_templates,
    get_by_file_name,
    update_by_file_name,
    batch_delete as recording_batch_delete,
    text_page,
    update_speaker,
    update_summary_template,
    like_or_feedback,
    batch_move_group,
    usage_statistics,
    update_status,
    speakers_batch,
    speakers_search,
    batch_abstract,
)
from cli_anything.aidee.core.summary import (
    list_by_recording as summary_list,
    get as summary_get,
    update as summary_update,
    stop as summary_stop,
    delete as summary_delete,
)
from cli_anything.aidee.core.user import register, info, membership_current, update_user, industry_position, delete as user_delete
from cli_anything.aidee.core.device import (
    bind, unbind, list_devices, get_primary, set_primary, get as device_get, count as device_count,
    update as device_update, usage_logs, check_bound,
)
from cli_anything.aidee.core.group import create as group_create, update as group_update, delete as group_delete, list_all as group_list, sort as group_sort
from cli_anything.aidee.core.template import (
    create as template_create, update as template_update, delete as template_delete,
    list_templates, get as template_get, redeem, redeem_by_user, usage_bill, quota,
)
from cli_anything.aidee.core import redemption as redemption_api
from cli_anything.aidee.core.template_category import list_categories as template_category_list, get as template_category_get
from cli_anything.aidee.core.membership import levels as membership_levels, purchase, order, order_status, orders, upgrade_price
from cli_anything.aidee.core.industry import list_all as industry_list
from cli_anything.aidee.core.position import list_all as position_list
from cli_anything.aidee.core.word_library import personal, industry as word_industry, add_hot_word, delete_hot_word, update_hot_word, hot_words
from cli_anything.aidee.core.feedback import create as feedback_create, get as feedback_get, update as feedback_update, list_all as feedback_list, delete as feedback_delete
from cli_anything.aidee.core.expo import check_update, manifest, asset
from cli_anything.aidee.core.websocket import clients_count, sessions, send_session, send_user, user_sessions, send_system, send_notify
from cli_anything.aidee.core.thirdparty import convert_summary_to_document
from cli_anything.aidee.core.firmware import upgrade_info, update_upgrade_record
from cli_anything.aidee.utils.output import print_result as _print_result
from cli_anything.aidee.utils.repl_skin import ReplSkin


def _ctx_base(ctx):
    return ctx.obj.get("base_url") or get_base_url()


def _ctx_token(ctx):
    return ctx.obj.get("token") or get_token()


def _output(result, json_mode: bool):
    _print_result(result, json_mode)


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="cli-anything-aidee")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.option("--base-url", envvar="AIDEE_BASE_URL", help="AIDEE API base URL")
@click.option("--token", envvar="AIDEE_TOKEN", help="Auth token")
@click.option("--api-key", envvar="AIDEE_API_KEY", help="AIDEE API key (sent as X-Api-Key)")
@click.pass_context
def cli(ctx, json_mode, base_url, token, api_key):
    """AIDEE CLI — AI recording, transcription, and summarization API client."""
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["base_url"] = base_url
    ctx.obj["token"] = token
    ctx.obj["api_key"] = api_key or get_api_key()
    if ctx.obj["api_key"]:
        os.environ["AIDEE_API_KEY"] = ctx.obj["api_key"]

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# --- config ---
@cli.group("config")
def config_group():
    """Configuration."""
    pass


@config_group.command("set-base-url")
@click.argument("url")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def config_set_base_url(ctx, url, json_mode):
    """Set AIDEE base URL."""
    r = set_base_url(url)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@config_group.command("set-token")
@click.argument("token")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def config_set_token_cmd(ctx, token, json_mode):
    """Set auth token."""
    r = set_token(token)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@config_group.command("set-api-key")
@click.argument("api_key")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def config_set_api_key_cmd(ctx, api_key, json_mode):
    """Set API key."""
    r = set_api_key(api_key)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@config_group.command("show")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def config_show_cmd(ctx, json_mode):
    """Show current config."""
    r = config_show()
    _output(r, json_mode or ctx.obj.get("json_mode"))


@config_group.command("clear")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def config_clear_cmd(ctx, json_mode):
    """Clear session."""
    r = config_clear()
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- session ---
@cli.group("session")
def session_group():
    """Session status."""
    pass


@session_group.command("status")
@click.pass_context
@click.option("--json", "json_mode", is_flag=True)
def session_status(ctx, json_mode):
    """Show session status."""
    r = config_show()
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- recording ---
@cli.group("recording")
def recording_group():
    """Recording management."""
    pass


@recording_group.command("create")
@click.option("--title", required=True)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_create_cmd(ctx, title, json_mode):
    """Create recording."""
    base = _ctx_base(ctx)
    tok = _ctx_token(ctx)
    r = recording_create(base, tok, title=title)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("get")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_get_cmd(ctx, code, json_mode):
    """Get recording by code."""
    r = recording_get(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("update")
@click.argument("code")
@click.option("--title")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_update_cmd(ctx, code, title, json_mode):
    """Update recording."""
    r = recording_update(_ctx_base(ctx), _ctx_token(ctx), code, title=title)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("delete")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_delete_cmd(ctx, code, json_mode):
    """Delete recording."""
    r = recording_delete(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("list")
@click.option("--page", default=1, type=int)
@click.option("--size", default=20, type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_list_cmd(ctx, page, size, json_mode):
    """List recordings."""
    r = list_recordings(_ctx_base(ctx), _ctx_token(ctx), page=page, size=size)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("speakers")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_speakers_cmd(ctx, code, json_mode):
    """Get speakers for recording."""
    r = get_speakers(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("summary-templates")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_templates_cmd(ctx, json_mode):
    """Get summary templates."""
    r = get_summary_templates(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- summary ---
@cli.group("summary")
def summary_group():
    """Recording summary management."""
    pass


@summary_group.command("list")
@click.argument("recording_code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def summary_list_cmd(ctx, recording_code, json_mode):
    """List summaries for recording."""
    r = summary_list(_ctx_base(ctx), _ctx_token(ctx), recording_code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@summary_group.command("get")
@click.argument("id", type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def summary_get_cmd(ctx, id, json_mode):
    """Get summary by ID."""
    r = summary_get(_ctx_base(ctx), _ctx_token(ctx), id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@summary_group.command("update")
@click.argument("id", type=int)
@click.option("--content")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def summary_update_cmd(ctx, id, content, json_mode):
    """Update summary."""
    r = summary_update(_ctx_base(ctx), _ctx_token(ctx), id, content=content)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@summary_group.command("stop")
@click.argument("id", type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def summary_stop_cmd(ctx, id, json_mode):
    """Stop summary generation."""
    r = summary_stop(_ctx_base(ctx), _ctx_token(ctx), id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@summary_group.command("delete")
@click.argument("id", type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def summary_delete_cmd(ctx, id, json_mode):
    """Delete summary."""
    r = summary_delete(_ctx_base(ctx), _ctx_token(ctx), id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- user ---
@cli.group("user")
def user_group():
    """User management."""
    pass


@user_group.command("info")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def user_info_cmd(ctx, json_mode):
    """Get user information."""
    r = info(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@user_group.command("membership")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def user_membership_cmd(ctx, json_mode):
    """Get current membership."""
    r = membership_current(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- device ---
@cli.group("device")
def device_group():
    """Device management."""
    pass


@device_group.command("list")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_list_cmd(ctx, json_mode):
    """List user devices."""
    r = list_devices(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@device_group.command("primary")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_primary_cmd(ctx, json_mode):
    """Get primary device."""
    r = get_primary(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- group ---
@cli.group("group")
def group_group():
    """Recording group management."""
    pass


@group_group.command("list")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def group_list_cmd(ctx, json_mode):
    """List recording groups."""
    r = group_list(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@group_group.command("create")
@click.option("--name", "group_name", required=True)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def group_create_cmd(ctx, group_name, json_mode):
    """Create recording group."""
    r = group_create(_ctx_base(ctx), _ctx_token(ctx), group_name=group_name)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@group_group.command("update")
@click.option("--id", "id_", required=True, type=int)
@click.option("--name", "group_name")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def group_update_cmd(ctx, id_, group_name, json_mode):
    """Update recording group."""
    r = group_update(_ctx_base(ctx), _ctx_token(ctx), id=id_, group_name=group_name)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@group_group.command("delete")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def group_delete_cmd(ctx, code, json_mode):
    """Delete recording group."""
    r = group_delete(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@group_group.command("sort")
@click.argument("codes", nargs=-1, required=True)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def group_sort_cmd(ctx, codes, json_mode):
    """Sort recording groups."""
    r = group_sort(_ctx_base(ctx), _ctx_token(ctx), list(codes))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- recording 扩展命令 ---
@recording_group.command("get-by-file-name")
@click.argument("file_name")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_get_by_file_name_cmd(ctx, file_name, json_mode):
    """Get recording by file name."""
    r = get_by_file_name(_ctx_base(ctx), _ctx_token(ctx), file_name)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("batch-delete")
@click.argument("codes", nargs=-1, required=True)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_batch_delete_cmd(ctx, codes, json_mode):
    """Batch delete recordings."""
    r = recording_batch_delete(_ctx_base(ctx), _ctx_token(ctx), list(codes))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@recording_group.command("usage-statistics")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def recording_usage_statistics_cmd(ctx, json_mode):
    """Get usage statistics."""
    r = usage_statistics(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- user 扩展 ---
@user_group.command("update")
@click.option("--nickname")
@click.option("--avatar")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def user_update_cmd(ctx, nickname, avatar, json_mode):
    """Update user info."""
    r = update_user(_ctx_base(ctx), _ctx_token(ctx), nickname=nickname, avatar=avatar)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@user_group.command("industry-position")
@click.option("--industry-id")
@click.option("--position-id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def user_industry_position_cmd(ctx, industry_id, position_id, json_mode):
    """Update industry position."""
    r = industry_position(_ctx_base(ctx), _ctx_token(ctx), industryId=industry_id, positionId=position_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@user_group.command("delete")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def user_delete_cmd(ctx, json_mode):
    """Delete user (logout)."""
    r = user_delete(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- device 扩展 ---
@device_group.command("bind")
@click.option("--device-id", required=True)
@click.option("--device-name")
@click.option("--sn")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_bind_cmd(ctx, device_id, device_name, sn, json_mode):
    """Bind device."""
    r = bind(_ctx_base(ctx), _ctx_token(ctx), deviceId=device_id, deviceName=device_name, sn=sn)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@device_group.command("unbind")
@click.argument("device_id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_unbind_cmd(ctx, device_id, json_mode):
    """Unbind device."""
    r = unbind(_ctx_base(ctx), _ctx_token(ctx), device_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@device_group.command("set-primary")
@click.argument("device_id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_set_primary_cmd(ctx, device_id, json_mode):
    """Set primary device."""
    r = set_primary(_ctx_base(ctx), _ctx_token(ctx), device_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@device_group.command("get")
@click.argument("identifier")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_get_cmd(ctx, identifier, json_mode):
    """Get device by identifier."""
    r = device_get(_ctx_base(ctx), _ctx_token(ctx), identifier)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@device_group.command("count")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_count_cmd(ctx, json_mode):
    """Get device count."""
    r = device_count(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@device_group.command("check-bound")
@click.argument("sn")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def device_check_bound_cmd(ctx, sn, json_mode):
    """Check if device is bound."""
    r = check_bound(_ctx_base(ctx), _ctx_token(ctx), sn)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- template ---
@cli.group("template")
def template_group():
    """Summary template management."""
    pass


@template_group.command("list")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_list_cmd(ctx, json_mode):
    """List templates."""
    r = list_templates(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@template_group.command("get")
@click.argument("template_id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_get_cmd(ctx, template_id, json_mode):
    """Get template."""
    r = template_get(_ctx_base(ctx), _ctx_token(ctx), template_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@template_group.command("create")
@click.option("--name", required=True)
@click.option("--description")
@click.option("--prompt")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_create_cmd(ctx, name, description, prompt, json_mode):
    """Create template."""
    r = template_create(_ctx_base(ctx), _ctx_token(ctx), name=name, description=description, prompt=prompt)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@template_group.command("delete")
@click.argument("template_id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_delete_cmd(ctx, template_id, json_mode):
    """Delete template."""
    r = template_delete(_ctx_base(ctx), _ctx_token(ctx), template_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@template_group.command("redeem")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_redeem_cmd(ctx, code, json_mode):
    """Redeem code."""
    r = redeem(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@template_group.command("quota")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_quota_cmd(ctx, json_mode):
    """Get quota."""
    r = quota(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- redemption ---
@cli.group("redemption")
def redemption_group():
    """兑换码：详情、兑换记录（与后端 /recordings/redemption 对齐）。"""
    pass


@redemption_group.command("code-detail")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def redemption_code_detail_cmd(ctx, code, json_mode):
    """按兑换码查询权益详情（确认页）。"""
    r = redemption_api.code_detail(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@redemption_group.command("records")
@click.option("--redeem-source", help="按兑换来源过滤，如 aideeApp")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def redemption_records_cmd(ctx, redeem_source, json_mode):
    """当前登录用户的兑换记录列表。"""
    r = redemption_api.list_records(_ctx_base(ctx), _ctx_token(ctx), redeem_source=redeem_source)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- template-category ---
@cli.group("template-category")
def template_category_group():
    """Template category."""
    pass


@template_category_group.command("list")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_category_list_cmd(ctx, json_mode):
    """List template categories."""
    r = template_category_list(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@template_category_group.command("get")
@click.argument("code")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def template_category_get_cmd(ctx, code, json_mode):
    """Get template category."""
    r = template_category_get(_ctx_base(ctx), _ctx_token(ctx), code)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- membership ---
@cli.group("membership")
def membership_group():
    """Membership management."""
    pass


@membership_group.command("levels")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def membership_levels_cmd(ctx, json_mode):
    """Get membership levels."""
    r = membership_levels(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@membership_group.command("orders")
@click.option("--page", default=1, type=int)
@click.option("--size", default=20, type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def membership_orders_cmd(ctx, page, size, json_mode):
    """List orders."""
    r = orders(_ctx_base(ctx), _ctx_token(ctx), page=page, size=size)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@membership_group.command("order")
@click.argument("order_no")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def membership_order_cmd(ctx, order_no, json_mode):
    """Get order."""
    r = order(_ctx_base(ctx), _ctx_token(ctx), order_no)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@membership_group.command("order-status")
@click.argument("order_no")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def membership_order_status_cmd(ctx, order_no, json_mode):
    """Get order status."""
    r = order_status(_ctx_base(ctx), _ctx_token(ctx), order_no)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@membership_group.command("upgrade-price")
@click.argument("target_level_id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def membership_upgrade_price_cmd(ctx, target_level_id, json_mode):
    """Get upgrade price."""
    r = upgrade_price(_ctx_base(ctx), _ctx_token(ctx), target_level_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- industry / position ---
@cli.group("industry")
def industry_group():
    """Industry."""
    pass


@industry_group.command("list")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def industry_list_cmd(ctx, json_mode):
    """List industries."""
    r = industry_list(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@cli.group("position")
def position_group():
    """Position."""
    pass


@position_group.command("list")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def position_list_cmd(ctx, json_mode):
    """List positions."""
    r = position_list(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- word-library ---
@cli.group("word-library")
def word_library_group():
    """Word library."""
    pass


@word_library_group.command("personal")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def word_library_personal_cmd(ctx, json_mode):
    """Get personal word library."""
    r = personal(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@word_library_group.command("hot-words")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def word_library_hot_words_cmd(ctx, json_mode):
    """Get hot words."""
    r = hot_words(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@word_library_group.command("add-hot-word")
@click.option("--words", "hot_words", required=True, help="热词，多个用换行或逗号分隔")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def word_library_add_hot_word_cmd(ctx, hot_words, json_mode):
    """Add hot word(s)."""
    r = add_hot_word(_ctx_base(ctx), _ctx_token(ctx), hot_words=hot_words)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@word_library_group.command("delete-hot-word")
@click.argument("hot_word_id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def word_library_delete_hot_word_cmd(ctx, hot_word_id, json_mode):
    """Delete hot word."""
    r = delete_hot_word(_ctx_base(ctx), _ctx_token(ctx), hot_word_id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- feedback ---
@cli.group("feedback")
def feedback_group():
    """Feedback."""
    pass


@feedback_group.command("list")
@click.option("--page", default=1, type=int)
@click.option("--size", default=20, type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def feedback_list_cmd(ctx, page, size, json_mode):
    """List feedback."""
    r = feedback_list(_ctx_base(ctx), _ctx_token(ctx), page=page, size=size)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@feedback_group.command("get")
@click.argument("id")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def feedback_get_cmd(ctx, id, json_mode):
    """Get feedback."""
    r = feedback_get(_ctx_base(ctx), _ctx_token(ctx), id)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- websocket (admin) ---
@cli.group("websocket")
def websocket_group():
    """WebSocket admin."""
    pass


@websocket_group.command("clients-count")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def websocket_clients_count_cmd(ctx, json_mode):
    """Get clients count."""
    r = clients_count(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@websocket_group.command("sessions")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def websocket_sessions_cmd(ctx, json_mode):
    """Get sessions."""
    r = sessions(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


@websocket_group.command("send-session")
@click.argument("session_id")
@click.option("--message", required=True)
@click.option("--type", "msg_type", default="system")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def websocket_send_session_cmd(ctx, session_id, message, msg_type, json_mode):
    """Send message to session."""
    r = send_session(_ctx_base(ctx), _ctx_token(ctx), session_id, message=message, type=msg_type)
    _output(r, json_mode or ctx.obj.get("json_mode"))


@websocket_group.command("send-user")
@click.argument("user_id")
@click.option("--message", required=True)
@click.option("--type", "msg_type", default="system")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def websocket_send_user_cmd(ctx, user_id, message, msg_type, json_mode):
    """Send message to user."""
    r = send_user(_ctx_base(ctx), _ctx_token(ctx), user_id, message=message, type=msg_type)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- thirdparty ---
@cli.group("thirdparty")
def thirdparty_group():
    """Third party."""
    pass


@thirdparty_group.command("convert-summary-to-document")
@click.option("--recording-id", required=True)
@click.option("--platform-type", required=True)
@click.option("--version")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def thirdparty_convert_cmd(ctx, recording_id, platform_type, version, json_mode):
    """Convert summary to document."""
    r = convert_summary_to_document(_ctx_base(ctx), _ctx_token(ctx), recordingId=recording_id, platformType=platform_type, version=version)
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- firmware ---
@cli.group("firmware")
def firmware_group():
    """Firmware."""
    pass


@firmware_group.command("upgrade-info")
@click.option("--json", "json_mode", is_flag=True)
@click.pass_context
def firmware_upgrade_info_cmd(ctx, json_mode):
    """Get upgrade info."""
    r = upgrade_info(_ctx_base(ctx), _ctx_token(ctx))
    _output(r, json_mode or ctx.obj.get("json_mode"))


# --- REPL ---
@cli.command("repl")
def repl():
    """Interactive REPL mode."""
    skin = ReplSkin("aidee", __version__)
    skin.print_banner()
    commands = {
        "config": ["set-base-url", "set-token", "set-api-key", "show", "clear"],
        "session": ["status"],
        "recording": ["create", "get", "list", "..."],
        "summary": ["list", "get", "update", "stop", "delete"],
        "template": ["list", "get", "redeem", "quota", "..."],
        "redemption": ["code-detail", "records"],
        "user": ["info", "membership", "update", "..."],
        "device": ["list", "primary", "bind", "..."],
        "group": ["list", "create", "update", "delete", "sort"],
    }
    skin.help(commands)
    skin.info("提示: 支持带空格的参数，例如: recording list --size 5")
    while True:
        try:
            line = skin.get_input()
            if not line or line.lower() in ("exit", "quit"):
                skin.print_goodbye()
                break
            try:
                parts = shlex.split(line)
            except ValueError as e:
                skin.error(f"引号/转义未闭合: {e}")
                continue
            if not parts:
                continue
            sys.argv = ["cli-anything-aidee"] + parts
            try:
                cli()
            except SystemExit:
                pass
        except KeyboardInterrupt:
            skin.print_goodbye()
            break
        except Exception as e:
            skin.error(str(e))


def main():
    cli()


if __name__ == "__main__":
    main()
