"""Config module — set base_url, token, show status."""

from cli_anything.aidee.core.session import (
    load_session,
    save_session,
    clear_session,
    get_base_url,
    get_token,
)


def set_base_url(url: str) -> dict:
    """Set base URL and save to session."""
    save_session(base_url=url)
    return {"base_url": url, "status": "ok"}


def set_token(token: str) -> dict:
    """Set auth token and save to session."""
    save_session(token=token)
    return {"status": "ok", "message": "Token saved"}


def show() -> dict:
    """Show current config (masked token)."""
    from cli_anything.aidee.core.session import SESSION_FILE
    sess = load_session()
    base_url = sess.get("base_url") or "http://localhost:8945/aidee-server (default)"
    token = sess.get("token")
    token_display = "***" + token[-4:] if token and len(token) > 4 else ("(not set)" if not token else "***")
    return {
        "base_url": base_url,
        "token": token_display,
        "session_file": str(SESSION_FILE),
    }


def clear() -> dict:
    """Clear session."""
    clear_session()
    return {"status": "ok", "message": "Session cleared"}
