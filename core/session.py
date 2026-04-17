"""Session state management — base_url, token persistence."""

import json
import os
from pathlib import Path
from typing import Optional

def _session_dir() -> Path:
    if os.environ.get("AIDEE_SESSION_DIR"):
        return Path(os.environ["AIDEE_SESSION_DIR"])
    return Path.home() / ".cli_anything_aidee"

SESSION_DIR = _session_dir()
SESSION_FILE = SESSION_DIR / "session.json"


def _ensure_session_dir() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def load_session() -> dict:
    """Load session from file."""
    if not SESSION_FILE.exists():
        return {}
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _locked_save_json(path: Path, data: dict) -> None:
    """Atomically write JSON with exclusive file locking."""
    _ensure_session_dir()
    try:
        f = open(path, "r+")
    except FileNotFoundError:
        f = open(path, "w")
    with f:
        _locked = False
        try:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            _locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            f.flush()
        finally:
            if _locked:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass


def save_session(base_url: Optional[str] = None, token: Optional[str] = None) -> dict:
    """Update and save session."""
    sess = load_session()
    if base_url is not None:
        sess["base_url"] = base_url
    if token is not None:
        sess["token"] = token
    _locked_save_json(SESSION_FILE, sess)
    return sess


def clear_session() -> None:
    """Clear session file."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def get_base_url() -> str:
    import os
    sess = load_session()
    return sess.get("base_url") or os.environ.get("AIDEE_BASE_URL", "http://localhost:8945/aidee-server")


def get_token() -> Optional[str]:
    import os
    sess = load_session()
    return sess.get("token") or os.environ.get("AIDEE_TOKEN")
