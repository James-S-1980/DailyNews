$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonCandidates = @(
    "$projectRoot\.venv\Scripts\python.exe",
    "python",
    "py"
)

$python = $null
foreach ($candidate in $pythonCandidates) {
    try {
        if ($candidate -like "*\python.exe" -and -not (Test-Path $candidate)) {
            continue
        }
        & $candidate --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate
            break
        }
    } catch {
        continue
    }
}

if (-not $python) {
    throw "Python was not found. Install Python 3.10+ or add it to PATH."
}

& $python "$projectRoot\daily_headlines.py"
exit $LASTEXITCODE
