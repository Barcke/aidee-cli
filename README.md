# cli-anything-aidee

AIDEE CLI — AI recording, transcription, and summarization API client.

**v1.0.1** — 优化 HTTP 错误/超时处理、REPL 使用 `shlex` 解析带空格参数、新增 `redemption` 命令组、`--version`。

## Prerequisites

- **AIDEE service** reachable (e.g. `https://imapi.ideamake.cn/aidee-server` or local `http://localhost:8945/aidee-server`)
- **Python 3.10+**
- **Auth**：支持 `IM-TOKEN` 和 `X-Api-Key`

## Installation

```bash
cd agent-harness
pip install -e .
```

## Usage

### One-shot commands

```bash
# Configure (optional if using env vars)
cli-anything-aidee config set-base-url http://localhost:8945/aidee-server
cli-anything-aidee config set-token YOUR_TOKEN
cli-anything-aidee config set-api-key aidee_your_api_key

# Show config
cli-anything-aidee config show

# User info
cli-anything-aidee user info

# List recordings
cli-anything-aidee recording list

# Get recording by code
cli-anything-aidee recording get RECORDING_CODE

# Create recording
cli-anything-aidee recording create --title "My Recording"

# JSON output for agents
cli-anything-aidee --json recording list

# Version
cli-anything-aidee --version
```

### Redemption (兑换码)

```bash
# 查询某码权益详情
cli-anything-aidee redemption code-detail YOUR_CODE

# 当前用户兑换记录
cli-anything-aidee redemption records
cli-anything-aidee redemption records --redeem-source aideeApp
```

### Environment variables

- `AIDEE_BASE_URL` — API base URL (default: http://localhost:8945/aidee-server)
- `AIDEE_TOKEN` — IM-TOKEN
- `AIDEE_API_KEY` — API key sent as `X-Api-Key`
- `AIDEE_REQUEST_TIMEOUT` — HTTP 超时秒数（默认 `30`）

### REPL mode

```bash
cli-anything-aidee
# or
cli-anything-aidee repl
```

REPL 内可使用引号包裹含空格的参数，例如：`recording create --title "My Title"`。

## Command groups

| Group | Commands |
|-------|----------|
| config | set-base-url, set-token, set-api-key, show, clear |
| session | status |
| recording | create, get, update, delete, list, speakers, summary-templates, ... |
| summary | list, get, update, stop, delete |
| template | list, get, create, delete, redeem, quota, ... |
| redemption | code-detail, records |
| user | info, membership |
| device | list, primary |
| group | list, create |

## Tests

```bash
cd agent-harness
pip install -e .
pytest cli_anything/aidee/tests/ -v
```
