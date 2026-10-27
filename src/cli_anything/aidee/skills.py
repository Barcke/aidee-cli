"""Read and sync only our packaged Skill; local edits receive a backup."""

from importlib.resources import files
from pathlib import Path
import os
import hashlib
from .errors import CLIError


def names():
    return ["aidee-user"]


def read(name):
    if name not in names():
        raise CLIError("VALIDATION_FAILED", "未知 Skill", 2, hint="skills list")
    return (
        files("cli_anything.aidee")
        .joinpath("skills", name + ".md")
        .read_text(encoding="utf-8")
    )


def sync(target=None, dry_run=False):
    root = Path(
        target
        or os.environ.get("AIDEE_SKILLS_DIR", str(Path.home() / ".agents" / "skills"))
    )
    updated = []
    backed_up = []
    for name in names():
        file = root / name / "SKILL.md"
        content = read(name)
        if file.exists() and file.read_bytes() == content.encode("utf-8"):
            continue
        if file.exists():
            existing = file.read_bytes()
            backup = Path(str(file) + ".pre-aidee")
            if backup.exists() and backup.read_bytes() != existing:
                digest = hashlib.sha256(existing).hexdigest()[:16]
                backup = Path(str(file) + ".pre-aidee-" + digest)
            suffix = 0
            stem = backup
            while backup.exists() and backup.read_bytes() != existing:
                suffix += 1
                backup = Path(str(stem) + "-" + str(suffix))
            if not backup.exists():
                backed_up.append(name)
                if not dry_run:
                    with backup.open("xb") as stream:
                        stream.write(existing)
        updated.append(name)
        if not dry_run:
            file.parent.mkdir(parents=True, exist_ok=True)
            import tempfile

            fd, temp = tempfile.mkstemp(dir=file.parent, prefix=".aidee-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(content)
                os.replace(temp, file)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
    return {
        "target": str(root),
        "updated": updated,
        "backedUp": backed_up,
        "dryRun": dry_run,
    }
