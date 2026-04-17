"""CLI 输出：人类可读与 JSON 模式统一处理。"""

from __future__ import annotations

import json
from typing import Any


def dumps_json(data: Any) -> str:
    """将结果序列化为 JSON 字符串（UTF-8，缩进便于 agent 解析）。"""
    return json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(o: Any) -> Any:
    if hasattr(o, "isoformat"):
        try:
            return o.isoformat()
        except Exception:
            return str(o)
    return str(o)


def print_result(result: Any, json_mode: bool) -> None:
    """根据模式打印 API 返回（dict/list 或其它可 JSON 化对象）。"""
    if json_mode:
        print(dumps_json(result))
        return
    if isinstance(result, dict) and "data" in result:
        d = result.get("data")
        if isinstance(d, dict):
            for k, v in d.items():
                print(f"  {k}: {v}")
        elif isinstance(d, list):
            for i, item in enumerate(d[:10]):
                print(f"  [{i}] {item}")
            if len(d) > 10:
                print(f"  ... and {len(d) - 10} more")
        else:
            print(f"  {d}")
    else:
        print(result)
