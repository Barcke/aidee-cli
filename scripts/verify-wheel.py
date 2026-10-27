#!/usr/bin/env python3
"""Install this build into a fresh venv; never resolve a PATH-installed old CLI."""

import os
from pathlib import Path
import subprocess
import tempfile
import shutil
import venv

wheels = list(Path("dist").glob("*.whl"))
if len(wheels) != 1:
    raise SystemExit("Exactly one wheel required")
with tempfile.TemporaryDirectory(prefix="aidee-wheel-") as tmp:
    root = Path(tmp)
    venv.EnvBuilder(
        with_pip=False, system_site_packages=False, symlinks=os.name != "nt"
    ).create(root / "venv")
    binary = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [
            shutil.which("uv") or "uv",
            "pip",
            "install",
            "--python",
            str(binary),
            str(wheels[0].resolve()),
        ],
        check=True,
    )
    env = {
        **os.environ,
        "AIDEE_CONFIG_DIR": str(root / "config"),
        "AIDEE_KEYRING_DISABLED": "1",
        "AIDEE_NO_UPDATE": "1",
    }
    env.pop("PYTHONPATH", None)
    env.pop("AIDEE_API_KEY", None)
    env.pop("AIDEE_TOKEN", None)
    subprocess.run(
        [
            str(binary),
            "-c",
            "from zoneinfo import ZoneInfo,reset_tzpath;from datetime import datetime;reset_tzpath(());ZoneInfo.clear_cache();assert datetime(2026,1,1,tzinfo=ZoneInfo('Asia/Shanghai')).utcoffset().total_seconds()==28800;ny=ZoneInfo('America/New_York');assert datetime(2026,1,1,tzinfo=ny).utcoffset().total_seconds()==-18000;assert datetime(2026,7,1,tzinfo=ny).utcoffset().total_seconds()==-14400;print('Packaged tzdata without system TZ database: Shanghai and New York DST verified')",
        ],
        check=True,
        cwd=tmp,
        env=env,
    )
    redirected = subprocess.check_output(
        [str(binary), "-m", "cli_anything.aidee", "skills", "read", "aidee-user"],
        cwd=tmp,
        env={**env, "PYTHONIOENCODING": "cp1252:strict"},
    )
    assert "Aidee" in redirected.decode("utf-8")
    print("Packaged Skills redirected as UTF-8 under cp1252:strict verified")
    for args in (
        ["--version"],
        ["schema"],
        ["--dry-run", "recording", "list"],
        ["skills", "list"],
    ):
        subprocess.run(
            [str(binary), "-m", "cli_anything.aidee", *args],
            check=True,
            cwd=tmp,
            env=env,
        )
