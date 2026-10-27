#!/usr/bin/env sh
set -eu
base="${AIDEE_RELEASE_BASE:-https://ai-agent.ideamake.cn/aidee-cli}"
command -v uv >/dev/null 2>&1 || { echo '请先安装 uv：https://docs.astral.sh/uv/getting-started/installation/' >&2; exit 1; }
task_tmp="$(mktemp -d)"
trap 'rm -rf "$task_tmp"' EXIT HUP INT TERM
installer_path="install.py"
previous_arg=""
for install_arg in "$@"; do
  if [ "$previous_arg" = "--channel" ] && [ "$install_arg" = "preview" ]; then installer_path="preview/install.py"; fi
  if [ "$install_arg" = "--channel=preview" ]; then installer_path="preview/install.py"; fi
  previous_arg="$install_arg"
done
curl --fail --silent --show-error --proto '=https' "$base/$installer_path" -o "$task_tmp/install.py"
uv run --no-project --with 'cryptography==48.0.1' --with 'packaging==26.0' python "$task_tmp/install.py" --base "$base" "$@"
