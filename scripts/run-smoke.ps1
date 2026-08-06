$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

python -m uv run pytest qa/tests/ui -m smoke --browser chromium `
  --tracing retain-on-failure `
  --video retain-on-failure `
  --screenshot only-on-failure `
  --junitxml artifacts/junit/ui-smoke.xml `
  --html artifacts/pytest/ui-smoke.html `
  --self-contained-html

