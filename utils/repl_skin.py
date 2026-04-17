"""Minimal REPL skin for AIDEE CLI (no prompt_toolkit dependency)."""

import sys
from pathlib import Path


def _skill_path() -> str | None:
    p = Path(__file__).resolve().parent.parent / "skills" / "SKILL.md"
    return str(p) if p.exists() else None


class ReplSkin:
    """Simple REPL skin for AIDEE CLI."""

    def __init__(self, name: str = "aidee", version: str = "1.0.0"):
        self.name = name
        self.version = version

    def print_banner(self) -> None:
        skill = _skill_path()
        lines = [
            f"╔══════════════════════════════════════════╗",
            f"║  {self.name} v{self.version} — AIDEE CLI Client           ║",
            f"║  AI recording, transcription, summary   ║",
            f"╚══════════════════════════════════════════╝",
        ]
        if skill:
            lines.append(f"  ◇ Skill: {skill}")
        for line in lines:
            print(line)

    def get_input(self, prompt: str = "aidee> ") -> str:
        try:
            return input(prompt).strip()
        except EOFError:
            return "exit"

    def success(self, msg: str) -> None:
        print(f"✓ {msg}")

    def error(self, msg: str) -> None:
        print(f"✗ {msg}", file=sys.stderr)

    def warning(self, msg: str) -> None:
        print(f"⚠ {msg}")

    def info(self, msg: str) -> None:
        print(f"● {msg}")

    def help(self, commands_dict: dict) -> None:
        print("\nAvailable commands:")
        for group, cmds in commands_dict.items():
            print(f"  {group}: {', '.join(cmds)}")
        print("  Type 'exit' or 'quit' to exit.\n")

    def print_goodbye(self) -> None:
        print("Goodbye.")
