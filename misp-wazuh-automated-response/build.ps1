<#
.SYNOPSIS
  Builds misp-ar.exe from src\misp-ar.py with PyInstaller (and optionally deploys it).

.EXAMPLE
  .\build.ps1             # build only  -> dist\misp-ar.exe
  .\build.ps1 -Deploy     # build + copy to Wazuh agent + restart service (run as Administrator)
#>
param(
    [switch]$Deploy,
    [string]$AgentBin = "C:\Program Files (x86)\ossec-agent\active-response\bin"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/4] Installing build dependencies..."
python -m pip install --quiet -r requirements-build.txt

Write-Host "[2/4] Building executable with PyInstaller..."
# --onefile : single standalone .exe (no Python needed on the endpoint)
# -w        : windowed, no console popup when Wazuh launches it
pyinstaller.exe --onefile -w --name misp-ar src\misp-ar.py

$exe = Join-Path $PSScriptRoot "dist\misp-ar.exe"
if (-not (Test-Path $exe)) { throw "Build failed: $exe not found." }

Write-Host "[3/4] SHA256 of the build:"
Get-FileHash $exe -Algorithm SHA256 | Format-List

if ($Deploy) {
    Write-Host "[4/4] Deploying to $AgentBin and restarting Wazuh agent..."
    Copy-Item $exe $AgentBin -Force
    Restart-Service WazuhSvc
    Write-Host "Deployed."
} else {
    Write-Host "[4/4] Skipped deployment (use -Deploy). Output: $exe"
}
