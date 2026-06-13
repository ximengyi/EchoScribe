$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Test-Path .\.venv\Scripts\pyinstaller.exe)) {
        & .\scripts\setup_dev.ps1
    }

    & .\.venv\Scripts\python.exe .\scripts\download_model.py
    & .\.venv\Scripts\python.exe .\scripts\build_portable.py
}
finally {
    Pop-Location
}
