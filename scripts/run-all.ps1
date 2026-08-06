$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

& "$PSScriptRoot\quality.ps1"
python -m uv run pytest qa/tests/api -m api
python -m uv run pytest qa/tests/contract -m contract
python -m uv run pytest qa/tests/ui qa/tests/e2e qa/tests/accessibility qa/tests/reliability `
  --browser chromium `
  --tracing retain-on-failure `
  --video retain-on-failure `
  --screenshot only-on-failure

