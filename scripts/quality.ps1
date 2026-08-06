$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Native command failed with exit code $LASTEXITCODE."
    }
}

$VenvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
    $PythonPrefix = @("-m")
}
else {
    $PythonCommand = "python"
    $PythonPrefix = @("-m", "uv", "run")
}

Invoke-CheckedNative { & $PythonCommand @PythonPrefix ruff format --check . }
Invoke-CheckedNative { & $PythonCommand @PythonPrefix ruff check . }
Invoke-CheckedNative { & $PythonCommand @PythonPrefix mypy --strict apps/api/src qa/src }
Invoke-CheckedNative { & $PythonCommand @PythonPrefix pytest apps/api/tests qa/tests/unit -m unit `
  --basetemp=.pytest-tmp/quality `
  --cov=shiftbridge_api `
  --cov=shiftbridge_qa `
  --cov-branch `
  --cov-report=term-missing }
Invoke-CheckedNative { npm.cmd --prefix apps/web run format:check }
Invoke-CheckedNative { npm.cmd --prefix apps/web run lint }
Invoke-CheckedNative { npm.cmd --prefix apps/web run typecheck }
Invoke-CheckedNative { npm.cmd --prefix apps/web run test }
Invoke-CheckedNative { npm.cmd --prefix apps/web run build }
