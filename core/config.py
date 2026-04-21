"""Config module — set base_url, token/api key, show status."""

from cli_anything.aidee.core.session import (
    load_session,
    save_session,
    clear_session,
)


def set_base_url(url: str) -> dict:
    """Set base URL and save to session."""
    save_session(base_url=url)
    return {"base_url": url, "status": "ok"}


def set_token(token: str) -> dict:
    """Set auth token and save to session."""
    save_session(token=token)
    return {"status": "ok", "message": "Token saved"}


def set_api_key(api_key: str) -> dict:
    """Set API key and save to session."""
    save_session(api_key=api_key)
    return {"status": "ok", "message": "API key saved"}


def _mask_secret(value: str | None) -> str:
    if not value:
        return "(not set)"
    return "***" + value[-4:] if len(value) > 4 else "***"


def show() -> dict:
    """Show current config (masked secrets)."""
    from cli_anything.aidee.core.session import SESSION_FILE
    sess = load_session()
    base_url = sess.get("base_url") or "http://localhost:8945/aidee-server (default)"
    return {
        "base_url": base_url,
        "token": _mask_secret(sess.get("token")),
        "api_key": _mask_secret(sess.get("api_key")),
        "session_file": str(SESSION_FILE),
    }


def clear() -> dict:
    """Clear session."""
    clear_session()
    return {"status": "ok", "message": "Session cleared"}
