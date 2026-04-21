# AIDEE CLI Test Plan

## Test Inventory Plan

- `test_core.py`: 12 unit tests planned
- `test_full_e2e.py`: 6 E2E tests planned (require running AIDEE service)

## Unit Test Plan

### session.py
- `test_load_session_empty` — No file returns {}
- `test_save_and_load_session` — Save base_url, token, api_key; load matches
- `test_clear_session` — Clear removes file
- `test_get_base_url_default` — Returns default when empty
- `test_get_token_default` — Returns None when empty
- `test_get_api_key_default` — Returns None when empty

### config.py
- `test_set_base_url` — Sets and persists
- `test_set_token` — Sets and persists
- `test_set_api_key` — Sets and persists
- `test_show` — Returns dict with base_url, token/api_key (masked)

### recording.py (with mocked api_request)
- `test_create_calls_api` — POST /recordings with correct body
- `test_get_calls_api` — GET /recordings/{code}
- `test_list_calls_api` — GET /recordings with params

## E2E Test Plan

### Prerequisites
- AIDEE service running at `https://api.aidee.me/aidee-server` (or AIDEE_BASE_URL)
- Valid token in `AIDEE_TOKEN` or API key in `AIDEE_API_KEY` (or session)

### Workflows
1. **Config flow** — Set base_url, set token/api key, show config
2. **Health check** — GET /actuator/health (if exposed)
3. **User info** — user info (requires token)
4. **Recording list** — recording list (requires token)
5. **CLI subprocess** — Run `cli-anything-aidee --help` via subprocess
6. **CLI config show** — Run `cli-anything-aidee config show --json` via subprocess

## Realistic Workflow Scenarios

- **Workflow: Setup** — config set-base-url, config set-token or config set-api-key, config show
- **Workflow: Inspect** — user info, recording list, device list
- **Workflow: Create** — recording create --title "Test", summary list <code>

## Test Results

```
============================= test session starts ==============================
cli_anything/aidee/tests/test_core.py::test_load_session_empty PASSED
cli_anything/aidee/tests/test_core.py::test_save_and_load_session PASSED
cli_anything/aidee/tests/test_core.py::test_clear_session PASSED
cli_anything/aidee/tests/test_core.py::test_get_base_url_default PASSED
cli_anything/aidee/tests/test_core.py::test_get_token_default PASSED
cli_anything/aidee/tests/test_core.py::test_set_base_url PASSED
cli_anything/aidee/tests/test_core.py::test_set_token PASSED
cli_anything/aidee/tests/test_core.py::test_show PASSED
cli_anything/aidee/tests/test_core.py::test_recording_create_calls_api PASSED
cli_anything/aidee/tests/test_core.py::test_recording_get_calls_api PASSED
cli_anything/aidee/tests/test_core.py::test_recording_list_calls_api PASSED
cli_anything/aidee/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/aidee/tests/test_full_e2e.py::TestCLISubprocess::test_config_show_json PASSED
cli_anything/aidee/tests/test_full_e2e.py::TestCLISubprocess::test_config_set_base_url PASSED
cli_anything/aidee/tests/test_full_e2e.py::TestCLISubprocess::test_recording_list_requires_service PASSED
============================== 15 passed, 1 skipped ==============================
```
