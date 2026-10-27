"""Stable CLI failures; upstream messages never determine permission classification."""


class CLIError(Exception):
    def __init__(
        self, code, message, exit_code=5, *, hint="", upstream=None, meta=None
    ):
        super().__init__(message)
        self.code, self.message, self.exit_code = code, message, exit_code
        self.hint, self.upstream, self.meta = hint, upstream, meta

    def envelope(self):
        types = {
            2: "validation",
            3: "auth",
            4: "permission",
            5: "business",
            6: "network",
            7: "local",
            130: "cancelled",
        }
        result = {
            "ok": False,
            "error": {
                "type": types.get(self.exit_code, "business"),
                "code": self.code,
                "upstreamCode": None if self.upstream is None else str(self.upstream),
                "message": self.message,
                "hint": self.hint,
            },
        }
        if self.meta:
            result["meta"] = self.meta
        return result


def from_upstream(code, message, *, status=200):
    text = str(code)
    if text in ("1001", "1002", "1003", "401") or status == 401:
        return CLIError(
            "AUTH_INVALID",
            message,
            3,
            upstream=code,
            hint="运行 aidee auth login 重新导入本人 Key",
        )
    if text in ("4030", "4031", "4032", "4033"):
        return CLIError(
            "PERMISSION_DENIED",
            message,
            4,
            upstream=code,
            hint="访问受风控限制，请通过原账户检查或联系支持",
        )
    if text in ("1004", "1005", "403") or status == 403:
        return CLIError(
            "PERMISSION_DENIED",
            message,
            4,
            upstream=code,
            hint="检查 Key 的 scope、调用策略和空间分享权限",
        )
    if text == "404" or status == 404:
        return CLIError("RESOURCE_NOT_FOUND", message, 5, upstream=code)
    if text in ("429", "4290", "4291", "4292", "4293", "4299") or status == 429:
        return CLIError("RATE_LIMITED", message, 6, upstream=code, hint="稍后重试")
    if status >= 500 or text == "503":
        return CLIError("NETWORK_ERROR", message, 6, upstream=code)
    return CLIError("BUSINESS_REJECTED", message, 5, upstream=code)
