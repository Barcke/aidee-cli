"""JSON is the default; progress belongs to stderr. Resource ids stay decimal strings."""

import json
import shutil
import subprocess
from .errors import CLIError


# Amount values already represented as decimal major units stay as supplied by the service.
def normalize(value, key=""):
    if isinstance(value, dict):
        return {
            k: normalize(v, k)
            for k, v in value.items()
            if k
            not in {
                "apiKey",
                "keyHash",
                "token",
                "promptTokens",
                "completionTokens",
                "modelName",
                "provider",
                "billingId",
                "fallbackDetail",
                "internalTaskMetadata",
            }
        }
    if isinstance(value, list):
        return [normalize(x, key) for x in value]
    if isinstance(value, int) and not isinstance(value, bool):
        if (
            key == "id"
            or key.endswith("Id")
            or key.endswith("Ids")
            or key.endswith("Minor")
            or abs(value) > 2**53 - 1
        ):
            return str(value)
    return value


def terminal_text(value, *, formatted=False):
    """Escape control bytes in readable output without changing source data."""
    return "".join(
        f"\\x{ord(char):02x}"
        if (ord(char) < 32 and not (formatted and char == "\n"))
        or 127 <= ord(char) <= 159
        else char
        for char in str(value)
    ).replace("|", "\\|")


def emit(value, *, mode="json", jq=None):
    value = normalize(value)
    if jq:
        executable = shutil.which("jq")
        if not executable:
            raise CLIError(
                "QUERY_FAILED", "未安装 jq", 2, hint="安装系统 jq 后重试 --jq"
            )
        result = subprocess.run(
            [executable, "--monochrome-output", jq],
            input=json.dumps(value, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=10,
        )
        if result.returncode:
            raise CLIError("QUERY_FAILED", "jq 表达式无效或执行失败", 2)
        print(result.stdout, end="")
        return
    if mode == "json":
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        data = value.get("data", value)
        rows = data if isinstance(data, list) else [data]
        if not rows:
            print("（暂无记录）")
            return
        if not all(isinstance(row, dict) for row in rows):
            print(
                terminal_text(
                    json.dumps(data, ensure_ascii=False, indent=2), formatted=True
                )
            )
            return
        keys = list(dict.fromkeys(k for row in rows for k in row))
        print(" | ".join(terminal_text(key) for key in keys))
        if mode == "markdown":
            print(" | ".join("---" for _ in keys))
        for row in rows:
            print(" | ".join(terminal_text(row.get(k, " ")) for k in keys))
        if value.get("meta"):
            print(terminal_text(json.dumps(value["meta"], ensure_ascii=False)))
