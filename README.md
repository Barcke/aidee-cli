# AIDEE CLI

Python CLI for the AIDEE backend. It exposes the AIDEE REST API as structured terminal commands for recordings, AI summaries, templates, users, devices, memberships, redemption codes, and related operational endpoints.

中文文档见 [README.zh-CN.md](/Users/jeyyu/pyProject/aidee-cli/README.zh-CN.md).

## Overview

AIDEE CLI is designed for developers, internal tools, QA workflows, and automation scripts that need direct access to the AIDEE service without going through a graphical client.

The project provides:

- A `click`-based command tree with grouped subcommands
- JSON output mode for scripting and agent usage
- Local session persistence for API base URL and token
- Environment-variable based configuration for CI and non-interactive use
- REPL mode for interactive exploration
- Thin per-resource API wrappers that map closely to backend endpoints
- Unit and end-to-end oriented test files for core workflows

## What The CLI Covers

The current codebase includes commands and API wrappers for:

- `config`: persist base URL and token locally
- `session`: inspect current session state
- `recording`: create, fetch, update, delete, list, inspect speakers, usage statistics, batch delete, file-name lookup, and related operations
- `summary`: list, fetch, update, stop, and delete summaries for recordings
- `template`: manage summary templates, redeem codes, inspect quota
- `redemption`: create redemption codes, inspect code details, list redemption records
- `user`: fetch profile, membership, update user profile, update industry/position, delete user
- `device`: list devices, inspect primary device, bind, unbind, set primary, inspect device status
- `group`: create and manage recording groups
- `template-category`: list and fetch template categories
- `membership`: membership levels, orders, order status, upgrade price
- `industry` and `position`: metadata lookup endpoints
- `word-library`: personal lexicon and hot-word management
- `feedback`: feedback listing and retrieval
- `websocket`: administrative WebSocket inspection and message sending
- `thirdparty`: convert summaries into third-party documents
- `firmware`: device upgrade information

## Architecture

Most business logic lives on the AIDEE backend. The CLI focuses on four responsibilities:

1. Accepts command-line arguments and validates the user input shape.
2. Resolves runtime configuration from flags, session state, and environment variables.
3. Calls backend endpoints with the expected request method, path, headers, and payload.
4. Returns either pretty terminal output or JSON-friendly structured output.

This structure keeps the project straightforward to extend. New endpoints generally require:

1. A wrapper function in `core/<resource>.py`
2. A command in [aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py)
3. Tests for argument and request-shape behavior
4. Documentation updates

## Authentication And Configuration

The backend uses the `IM-TOKEN` request header, not `Authorization: Bearer`.

Configuration can come from three sources:

- CLI flags: `--base-url`, `--token`
- Environment variables:
  - `AIDEE_BASE_URL`
  - `AIDEE_TOKEN`
  - `AIDEE_REQUEST_TIMEOUT`
  - `AIDEE_SESSION_DIR`
- Local persisted session file

Session data is stored in:

- `$AIDEE_SESSION_DIR/session.json`, if `AIDEE_SESSION_DIR` is set
- otherwise `~/.cli_anything_aidee/session.json`

## Typical Usage

### Configure

```bash
cli-anything-aidee config set-base-url http://localhost:8945/aidee-server
cli-anything-aidee config set-token YOUR_IM_TOKEN
cli-anything-aidee config show
```

### Inspect user and recordings

```bash
cli-anything-aidee user info
cli-anything-aidee recording list
cli-anything-aidee recording get RECORDING_CODE
```

### Work with summaries

```bash
cli-anything-aidee summary list RECORDING_CODE
cli-anything-aidee summary get 123
cli-anything-aidee summary update 123 --content "Updated summary content"
```

### Use machine-readable output

```bash
cli-anything-aidee --json recording list
cli-anything-aidee --json redemption records
```

### Start the interactive shell

```bash
cli-anything-aidee
# or
cli-anything-aidee repl
```

The REPL uses `shlex.split`, so quoted arguments with spaces are supported:

```bash
recording create --title "Quarterly Business Review"
```

## Repository Structure

```text
.
├── aidee_cli.py          # Click CLI entry and command registration
├── __main__.py           # python -m entry point
├── core/                 # Per-resource REST API wrappers
├── utils/
│   ├── aidee_backend.py  # HTTP client and error handling
│   ├── output.py         # JSON/plain output formatting
│   └── repl_skin.py      # REPL shell presentation
├── tests/
│   ├── test_core.py      # Unit tests with mocked requests
│   ├── test_full_e2e.py  # Subprocess and optional real-service tests
│   └── TEST.md           # Test plan notes
└── skills/SKILL.md       # Agent-oriented project guidance
```

## Implementation

### CLI Layer

[aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py) contains the top-level `click` group and registers all command groups. It also:

- exposes `--json`
- resolves context-level `base_url` and `token`
- falls back to REPL mode when no subcommand is provided
- keeps command handlers thin by delegating real HTTP work to `core/`

### Core API Layer

Each file under [core](/Users/jeyyu/pyProject/aidee-cli/core) maps a backend resource to a small set of wrapper functions. These functions are intentionally direct and mostly correspond 1:1 to REST endpoints.

Examples:

- [core/recording.py](/Users/jeyyu/pyProject/aidee-cli/core/recording.py)
- [core/summary.py](/Users/jeyyu/pyProject/aidee-cli/core/summary.py)
- [core/redemption.py](/Users/jeyyu/pyProject/aidee-cli/core/redemption.py)

### HTTP Backend

[utils/aidee_backend.py](/Users/jeyyu/pyProject/aidee-cli/utils/aidee_backend.py) centralizes:

- timeout handling
- `IM-TOKEN` header injection
- JSON decoding
- connection, timeout, and HTTP error translation

This keeps the command handlers and resource modules focused on endpoint behavior instead of transport details.

## Testing

The repository includes:

- [tests/test_core.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_core.py): unit tests for session/config behavior and request-shape validation with mocks
- [tests/test_full_e2e.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_full_e2e.py): subprocess tests plus optional live-service E2E coverage

Typical test execution:

```bash
pytest tests/ -v
```

Live-service E2E can be gated with:

- `AIDEE_E2E=1`
- reachable AIDEE service
- valid `AIDEE_TOKEN`
