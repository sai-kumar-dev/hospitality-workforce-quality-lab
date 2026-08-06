$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

python -m uv sync --locked
npm.cmd --prefix apps/web ci
python -m uv run playwright install chromium

Write-Host "ShiftBridge development dependencies are ready."

