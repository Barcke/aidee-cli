"""WebSocket admin module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def clients_count(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get connected clients count."""
    return api_request("GET", "/api/websocket/clients/count", base_url, token)


def sessions(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get active sessions."""
    return api_request("GET", "/api/websocket/sessions", base_url, token)


def send_session(base_url: str, token: Optional[str], session_id: str, **kwargs) -> dict[str, Any]:
    """Send message to session."""
    return api_request("POST", f"/api/websocket/send/session/{session_id}", base_url, token, json_body=kwargs)


def send_user(base_url: str, token: Optional[str], user_id: str, **kwargs) -> dict[str, Any]:
    """Send message to user."""
    return api_request("POST", f"/api/websocket/send/user/{user_id}", base_url, token, json_body=kwargs)


def user_sessions(base_url: str, token: Optional[str], user_id: str) -> dict[str, Any]:
    """Get user sessions."""
    return api_request("GET", f"/api/websocket/user/{user_id}/sessions", base_url, token)


def send_system(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Send system message."""
    return api_request("POST", "/api/websocket/send/system", base_url, token, json_body=kwargs)


def send_notify(base_url: str, token: Optional[str], **kwargs) -> dict[str, Any]:
    """Send notify."""
    return api_request("POST", "/api/websocket/send/notify", base_url, token, json_body=kwargs)
