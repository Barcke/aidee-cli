param([ValidateSet("stable", "preview")][string]$Channel = "stable", [switch]$SyncSkills)
$ErrorActionPreference = "Stop"
$base = if ($env:AIDEE_RELEASE_BASE) { $env:AIDEE_RELEASE_BASE } else { "https://ai-agent.ideamake.cn/aidee-cli" }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "请先安装 uv" }
$installer = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString() + ".py")
try {
    $installerPath = if ($Channel -eq "preview") { "preview/install.py" } else { "install.py" }
    Invoke-WebRequest -Uri "$base/$installerPath" -OutFile $installer
    $skillArgs = if ($SyncSkills) { @("--sync-skills") } else { @() }
    uv run --no-project --with 'cryptography==48.0.1' --with 'packaging==26.0' python $installer --base $base --channel $Channel @skillArgs
    if ($LASTEXITCODE -ne 0) { throw "Aidee 安装失败" }
} finally { Remove-Item -Path $installer -ErrorAction SilentlyContinue }
