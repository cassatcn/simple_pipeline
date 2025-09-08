<#  data_db_setup.ps1
    - Creates remote dirs
    - Copies user_data.zip and purchase_data.zip to the server
    - Unzips them into the pipeline data dirs
    - Creates/owns the postgres DB/schema

    Usage example:
      .\data_db_setup.ps1
#>

[CmdletBinding()]
param(
  [string]$User = "moxy",
  [string]$RemoteHost = "10.10.219.8",
  [string]$RemoteBase = "~/simple_pipeline",
  [string]$LocalUserZip = $(Join-Path $PSScriptRoot 'user_data.zip'),
  [string]$LocalPurchaseZip = $(Join-Path $PSScriptRoot 'purchase_data.zip'),
  [string]$DbName = "ecommerce",
  [string]$DbOwner = "appuser",
  [switch]$VerboseScp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve local files
$LocalUserZipPath = (Resolve-Path -LiteralPath $LocalUserZip).Path
$LocalPurchaseZipPath = (Resolve-Path -LiteralPath $LocalPurchaseZip).Path

$SshTarget = "$User@$RemoteHost"
$RemoteDest = "${SshTarget}:$RemoteBase/"
$RemoteScriptName = ".data_db_setup_run.sh"
$RemoteScriptDest = "${SshTarget}:$RemoteBase/$RemoteScriptName"

Write-Host "==> Ensuring remote directories exist on ${SshTarget}..."
& ssh $SshTarget "mkdir -p -- '$RemoteBase/data/user_data' '$RemoteBase/data/purchase_data'"
if ($LASTEXITCODE -ne 0) { throw "ssh mkdir failed (exit $LASTEXITCODE)" }

Write-Host "==> Copying ZIPs to ${SshTarget}:$RemoteBase/ ..."
$scpArgs = @()
if (-not $VerboseScp) { $scpArgs += "-q" }

& scp @scpArgs "$LocalUserZipPath"     "$RemoteDest"
if ($LASTEXITCODE -ne 0) { throw "scp user_data.zip failed (exit $LASTEXITCODE)" }

& scp @scpArgs "$LocalPurchaseZipPath" "$RemoteDest"
if ($LASTEXITCODE -ne 0) { throw "scp purchase_data.zip failed (exit $LASTEXITCODE)" }

Write-Host "==> Uploading and running remote setup script..."

# Remote bash script content
$remoteScript = @'
#!/usr/bin/env bash
set -euo pipefail

echo "[remote] Unzipping datasets into ${RemoteBase} ..."
if ! command -v unzip >/dev/null 2>&1; then
  echo "[remote] ERROR: unzip not installed (try: sudo apt-get update && sudo apt-get install -y unzip)" >&2
  exit 1
fi
unzip -q -o "${RemoteBase}/user_data.zip"     -d "${RemoteBase}/data/user_data"
unzip -q -o "${RemoteBase}/purchase_data.zip" -d "${RemoteBase}/data/purchase_data"

# Avoid sudo chdir warnings
cd /tmp

echo "[remote] Creating database if missing..."
if ! sudo -H -u postgres psql -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '${DbName}'" | grep -q 1; then
  sudo -H -u postgres createdb -O '${DbOwner}' '${DbName}'
fi

echo "[remote] Enforcing DB and schema ownership..."
sudo -H -u postgres psql -d postgres  -v ON_ERROR_STOP=1 -c "ALTER DATABASE ${DbName} OWNER TO ${DbOwner};"
sudo -H -u postgres psql -d "${DbName}" -v ON_ERROR_STOP=1 -c "ALTER SCHEMA public OWNER TO ${DbOwner};"

echo "[remote] Done."
'@

# Inject vars and force LF endings
$remoteScript =
  $remoteScript.Replace('${DbName}',$DbName).
                Replace('${DbOwner}',$DbOwner).
                Replace('${RemoteBase}',$RemoteBase) -replace "`r`n","`n" -replace "`r","`n"

# Write temp file with UTF-8 + LF
$tmp = Join-Path $env:TEMP ("deploy_" + [guid]::NewGuid().ToString() + ".sh")
[System.IO.File]::WriteAllBytes($tmp, [System.Text.Encoding]::UTF8.GetBytes($remoteScript))

# Copy the script to the server
& scp @scpArgs "$tmp" "$RemoteScriptDest"
if ($LASTEXITCODE -ne 0) { throw "scp remote script failed (exit $LASTEXITCODE)" }

# Run the script with a TTY so sudo can prompt interactively
& ssh -t $SshTarget "chmod +x $RemoteBase/$RemoteScriptName && bash $RemoteBase/$RemoteScriptName && rm -f $RemoteBase/$RemoteScriptName"
if ($LASTEXITCODE -ne 0) { throw "remote script failed (exit $LASTEXITCODE)" }

Remove-Item $tmp -Force -ErrorAction SilentlyContinue

Write-Host "==> All done."
Write-Host "   • Data unzipped to $RemoteBase/data/{user_data,purchase_data}"
Write-Host "   • Postgres DB '$DbName' exists and is owned by '$DbOwner'"
