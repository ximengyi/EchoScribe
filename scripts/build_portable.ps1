$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Test-Path .\.venv\Scripts\pyinstaller.exe)) {
        & .\scripts\setup_dev.ps1
    }

    & .\.venv\Scripts\pyinstaller.exe `
        --noconfirm `
        --windowed `
        --name EchoScribe `
        --paths .\src `
        --add-data "vendor;vendor" `
        --add-data "scripts\record_system_audio.ps1;scripts" `
        src\echoscribe\app.py

    $zip = Join-Path $root "dist\EchoScribe-portable.zip"
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path "dist\EchoScribe\*" -DestinationPath $zip
    Write-Host "Portable package: $zip"
}
finally {
    Pop-Location
}

