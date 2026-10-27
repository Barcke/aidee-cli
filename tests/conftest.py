import pytest


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("AIDEE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("AIDEE_KEYRING_DISABLED", "1")
    monkeypatch.setenv("AIDEE_NO_UPDATE", "1")
    for key in (
        "AIDEE_API_KEY",
        "AIDEE_TOKEN",
        "AIDEE_PROFILE",
        "AIDEE_BASE_URL",
        "AIDEE_TEAM_BASE_URL",
        "AIDEE_WEB_BASE",
        "AIDEE_RELEASE_PUBLIC_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
