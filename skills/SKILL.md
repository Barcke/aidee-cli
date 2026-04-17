---
name: "cli-anything-aidee"
description: "AIDEE CLI — AI recording, transcription, and summarization API client. Control the AIDEE backend via structured commands and JSON output."
triggers:
  - aidee
  - recording
  - transcription
  - summary
  - ai summary
  - cli aidee
  - redemption
  - 兑换码
---

# cli-anything-aidee

AIDEE CLI client for AI-powered recording, transcription, and summarization.

## Prerequisites

- AIDEE service running (default: http://localhost:8945/aidee-server)
- Auth token (from Ideamake auth system)

## Installation

```bash
cd agent-harness && pip install -e .
```

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| config | set-base-url, set-token, show, clear | Configure API URL and auth |
| recording | create, get, update, delete, list, speakers, summary-templates | Recording CRUD |
| summary | list, get, update, stop, delete | Recording summary management |
| template | list, get, redeem, quota, … | Templates and template-scoped redeem |
| redemption | create-code, code-detail, records | Redemption codes (create / preview / history) |
| user | info, membership | User info and membership |
| device | list, primary | Device management |
| group | list, create | Recording groups |

## Agent Guidance

- Use `--json` for machine-readable output: `cli-anything-aidee --json recording list`
- Set token: `cli-anything-aidee config set-token <token>` or `AIDEE_TOKEN` env
- **Token format**: Raw IM-TOKEN value (no "Bearer" prefix); AIDEE uses `IM-TOKEN` header
- Set base URL: `cli-anything-aidee config set-base-url <url>` or `AIDEE_BASE_URL` env
- Optional: `AIDEE_REQUEST_TIMEOUT` (seconds, default 30)
- Most commands require authentication; configure token first
- REPL supports quoted args (shell-like splitting via `shlex`)

## Examples

```bash
# Configure
cli-anything-aidee config set-base-url http://localhost:8945/aidee-server
cli-anything-aidee config set-token YOUR_TOKEN

# User info
cli-anything-aidee user info

# List recordings (JSON for agents)
cli-anything-aidee --json recording list

# Create recording
cli-anything-aidee recording create --title "Meeting Notes"

# Get recording
cli-anything-aidee recording get RECORDING_CODE

# List summaries for recording
cli-anything-aidee summary list RECORDING_CODE

# Redemption codes
cli-anything-aidee redemption create-code --code-type USAGE_COUNT --template-id TPL --quantity 10
cli-anything-aidee redemption code-detail CODE_STRING
cli-anything-aidee --json redemption records
```
