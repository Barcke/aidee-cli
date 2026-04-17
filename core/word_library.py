"""Word library module."""

from typing import Any, Optional

from cli_anything.aidee.utils.aidee_backend import api_request


def personal(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get personal word library."""
    return api_request("GET", "/word-libraries/personal", base_url, token)


def industry(base_url: str, token: Optional[str], **params) -> dict[str, Any]:
    """Get industry word library."""
    return api_request("GET", "/word-libraries/industry", base_url, token, params=params)


def add_hot_word(base_url: str, token: Optional[str], hot_words: str, **kwargs) -> dict[str, Any]:
    """Add personal hot words. hot_words: single word or newline-separated list."""
    return api_request("POST", "/word-libraries/personal/hot-words", base_url, token, json_body={"hotWords": hot_words, **kwargs})


def delete_hot_word(base_url: str, token: Optional[str], hot_word_id: str) -> dict[str, Any]:
    """Delete personal hot word."""
    return api_request("DELETE", f"/word-libraries/personal/hot-words/{hot_word_id}", base_url, token)


def update_hot_word(base_url: str, token: Optional[str], hot_word_id: str, **kwargs) -> dict[str, Any]:
    """Update personal hot word."""
    return api_request("PUT", f"/word-libraries/personal/hot-words/{hot_word_id}", base_url, token, json_body=kwargs)


def hot_words(base_url: str, token: Optional[str]) -> dict[str, Any]:
    """Get personal hot words."""
    return api_request("GET", "/word-libraries/personal/hot-words", base_url, token)
