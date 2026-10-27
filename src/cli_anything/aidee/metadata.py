"""Only registered personal operations are exposed to users and agents."""

REGISTRY = {}


def record(name, method, path, *, service="aidee", risk="read", params=None):
    REGISTRY[name] = {
        "id": name,
        "method": method,
        "path": path,
        "service": service,
        "risk": risk,
        "scope": "write" if risk == "write" else "read",
        "params": params or [],
    }
