# AIDEE CLI

AIDEE CLI is a Python command-line client for the AIDEE backend service. It exposes AIDEE REST APIs as structured terminal commands for recordings, summaries, templates, devices, memberships, redemption workflows, and related operational capabilities.

中文说明见 [README.zh-CN.md](/Users/jeyyu/pyProject/aidee-cli/README.zh-CN.md).

## Overview

This project is intended for developers, QA engineers, automation workflows, and service integrations that need direct access to AIDEE backend capabilities without going through a graphical client.

The CLI provides:

- Resource-oriented command groups built with `click`
- Optional `--json` output for scripts and agents
- Local session persistence for endpoint and credentials
- Environment-variable based, non-interactive configuration
- An interactive REPL for exploratory usage
- A thin API wrapper layer that stays close to backend endpoints

## Authentication

The CLI supports two authentication methods:

- `AIDEE_TOKEN`, sent as the `IM-TOKEN` header
- `AIDEE_API_KEY`, sent as the `X-Api-Key` header

For normal usage, providing either one is sufficient. You do not need to configure both unless a specific backend deployment requires it.

## Repository Note

The executable name used by this project is `cli-anything-aidee`.

This repository currently contains the AIDEE command module source used under the `cli_anything.aidee` package namespace. The source tree in this checkout does not include packaging metadata such as `pyproject.toml` or `setup.py`, so the old `pip install -e .` instruction was not valid for this repository as-is.

For that reason, the command examples below document the correct command surface and executable name, while actual installation should follow the packaging or host-project setup used in your environment.

## Configuration

Configuration can come from command-line options, environment variables, or the local session file.

Supported command-line options:

- `--base-url`
- `--token`
- `--api-key`
- `--json`

Supported environment variables:

- `AIDEE_BASE_URL`
- `AIDEE_TOKEN`
- `AIDEE_API_KEY`
- `AIDEE_REQUEST_TIMEOUT`
- `AIDEE_SESSION_DIR`

Session storage:

- If `AIDEE_SESSION_DIR` is set, the CLI stores session data in `$AIDEE_SESSION_DIR/session.json`
- Otherwise, it uses `~/.cli_anything_aidee/session.json`

Default base URL:

```text
https://api.aidee.me/aidee-server
```

## Quick Start

Configure the service endpoint and one credential type:

```bash
cli-anything-aidee config set-base-url https://api.aidee.me/aidee-server
cli-anything-aidee config set-token YOUR_IM_TOKEN
```

Or use an API key instead of a token:

```bash
cli-anything-aidee config set-base-url https://api.aidee.me/aidee-server
cli-anything-aidee config set-api-key YOUR_AIDEE_API_KEY
```

Inspect the active local configuration:

```bash
cli-anything-aidee config show
cli-anything-aidee session status
```

Use environment variables for non-interactive scenarios:

```bash
export AIDEE_BASE_URL="https://api.aidee.me/aidee-server"
export AIDEE_TOKEN="YOUR_IM_TOKEN"
cli-anything-aidee user info
```

## Common Commands

### Global

```bash
cli-anything-aidee --help
cli-anything-aidee --version
cli-anything-aidee --json recording list
```

### Recordings

```bash
cli-anything-aidee recording list
cli-anything-aidee recording list --page 1 --size 20
cli-anything-aidee recording get RECORDING_CODE
cli-anything-aidee recording create --title "Project Sync"
cli-anything-aidee recording update RECORDING_CODE --title "Updated Title"
cli-anything-aidee recording delete RECORDING_CODE
cli-anything-aidee recording speakers RECORDING_CODE
cli-anything-aidee recording summary-templates
cli-anything-aidee recording get-by-file-name "meeting.wav"
cli-anything-aidee recording batch-delete RECORDING_CODE_1 RECORDING_CODE_2
cli-anything-aidee recording usage-statistics
```

### Summaries

```bash
cli-anything-aidee summary list RECORDING_CODE
cli-anything-aidee summary get SUMMARY_ID
cli-anything-aidee summary update SUMMARY_ID --content "Updated summary content"
cli-anything-aidee summary stop SUMMARY_ID
cli-anything-aidee summary delete SUMMARY_ID
```

### Templates and Redemption

```bash
cli-anything-aidee template list
cli-anything-aidee template get TEMPLATE_ID
cli-anything-aidee template create --name "Sales Review" --prompt "Summarize key outcomes"
cli-anything-aidee template delete TEMPLATE_ID
cli-anything-aidee template redeem CODE_STRING
cli-anything-aidee template quota

cli-anything-aidee redemption code-detail CODE_STRING
cli-anything-aidee redemption records
```

### User and Device

```bash
cli-anything-aidee user info
cli-anything-aidee user membership
cli-anything-aidee user update --nickname "Alice"
cli-anything-aidee user industry-position --industry-id 1 --position-id 2
cli-anything-aidee user delete

cli-anything-aidee device list
cli-anything-aidee device primary
cli-anything-aidee device bind --device-id DEVICE_ID --device-name "Recorder" --sn SN123
cli-anything-aidee device unbind DEVICE_ID
cli-anything-aidee device set-primary DEVICE_ID
cli-anything-aidee device get DEVICE_ID
cli-anything-aidee device count
cli-anything-aidee device check-bound SN123
```

## Command Groups

The current source registers the following top-level command groups:

- `config`
- `session`
- `recording`
- `summary`
- `user`
- `device`
- `group`
- `template`
- `redemption`
- `template-category`
- `membership`
- `industry`
- `position`
- `word-library`
- `feedback`
- `websocket`
- `thirdparty`
- `firmware`
- `repl`

## REPL Mode

Running the CLI without a subcommand enters REPL mode. You can also start it explicitly:

```bash
cli-anything-aidee
cli-anything-aidee repl
```

The REPL uses `shlex.split`, so quoted arguments with spaces are handled correctly:

```bash
recording create --title "Quarterly Business Review"
```

## Project Structure

```text
.
├── aidee_cli.py
├── __main__.py
├── core/
├── utils/
├── tests/
├── README.md
└── README.zh-CN.md
```

Key files:

- [aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py): CLI entrypoint and command registration
- [core/session.py](/Users/jeyyu/pyProject/aidee-cli/core/session.py): session persistence and credential lookup
- [core/config.py](/Users/jeyyu/pyProject/aidee-cli/core/config.py): configuration commands
- [utils/aidee_backend.py](/Users/jeyyu/pyProject/aidee-cli/utils/aidee_backend.py): HTTP transport, timeout handling, and error translation
- [tests/test_core.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_core.py): unit coverage for config/session and request wiring
- [tests/test_full_e2e.py](/Users/jeyyu/pyProject/aidee-cli/tests/test_full_e2e.py): subprocess and optional real-service tests

## Testing

Typical validation targets in this repository are:

```bash
pytest tests/ -v
```

Optional real-service end-to-end coverage depends on:

- `AIDEE_E2E=1`
- reachable AIDEE service
- valid `AIDEE_TOKEN` or `AIDEE_API_KEY`

## Validation Notes

This README was aligned against the current source files, especially:

- command registration in [aidee_cli.py](/Users/jeyyu/pyProject/aidee-cli/aidee_cli.py)
- credential handling in [core/session.py](/Users/jeyyu/pyProject/aidee-cli/core/session.py)
- HTTP header behavior in [utils/aidee_backend.py](/Users/jeyyu/pyProject/aidee-cli/utils/aidee_backend.py)

One important repository caveat remains: this checkout does not include standalone packaging metadata, so documentation should not claim that this repository can be installed directly with `pip install -e .` unless packaging files are added later.
