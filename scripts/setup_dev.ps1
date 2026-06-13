$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = "C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Push-Location $root
try {
    & $python -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
    & .\.venv\Scripts\python.exe -m pip install -e .
}
finally {
    Pop-Location
}

