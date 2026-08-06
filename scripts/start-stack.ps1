$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

docker compose up -d --build
python -m uv run python scripts/wait_for_stack.py
docker compose ps

