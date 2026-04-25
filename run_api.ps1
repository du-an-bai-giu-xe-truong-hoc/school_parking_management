param(
    [switch]$Detached
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$appFile = Join-Path $PSScriptRoot "app\main.py"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Khong tim thay Python trong .venv: $pythonExe"
}

if (-not (Test-Path $appFile)) {
    Write-Error "Khong tim thay file API: $appFile"
}

if ($Detached) {
    Start-Process -FilePath $pythonExe -ArgumentList $appFile | Out-Null
    Write-Output "Da mo API o che do nen."
    exit 0
}

& $pythonExe $appFile
exit $LASTEXITCODE
