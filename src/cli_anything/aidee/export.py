"""Write only complete exports. Existing files require explicit overwrite."""

import json
import os
from pathlib import Path
import tempfile
from .errors import CLIError
from .output import normalize


def render(data, format):
    if format == "json":
        return json.dumps(normalize(data), ensure_ascii=False, indent=2) + "\n"
    rows = data if isinstance(data, list) else [data]
    parts = []
    for row in rows:
        if isinstance(row, str):
            parts.append(row)
        elif isinstance(row, dict):
            content = row.get("text") if "text" in row else row.get("content")
            if content is None and isinstance(row.get("summary"), dict):
                content = row["summary"].get("content")
            if content is None and isinstance(row.get("summary"), str):
                content = row["summary"]
            if content is None:
                raise CLIError(
                    "BUSINESS_REJECTED", "返回内容中没有可导出的原文或总结", 5
                )
            prefix = (
                ("# " + str(row["title"]) + "\n\n")
                if format == "md" and row.get("title")
                else ""
            )
            parts.append(prefix + str(content))
        else:
            raise CLIError("BUSINESS_REJECTED", "不可导出的内容类型", 5)
    return "\n\n".join(parts) + "\n"


def write(content, filename, overwrite=False):
    target = Path(filename)
    if target.exists() and not overwrite:
        raise CLIError(
            "LOCAL_ERROR", "目标文件已存在", 7, hint="使用 --overwrite 明确覆盖"
        )
    if not target.parent.exists():
        raise CLIError("LOCAL_ERROR", "目标目录不存在", 7)
    fd, temp = tempfile.mkstemp(prefix=".aidee-export-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temp, target)
        else:
            # Atomic exclusive installation also protects against a racing writer.
            os.link(temp, target)
            os.unlink(temp)
    except FileExistsError:
        raise CLIError("LOCAL_ERROR", "目标文件已存在，未覆盖", 7) from None
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return {"path": str(target.resolve()), "bytes": len(content.encode("utf-8"))}
