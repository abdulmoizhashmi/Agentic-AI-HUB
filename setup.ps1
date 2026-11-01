$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10 or newer is required. Install Python and reopen VS Code."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js 18 or newer (including npm) is required. Install Node.js and reopen VS Code."
}

if (-not (Test-Path $venvPython)) {
    python -m venv (Join-Path $backend ".venv")
}
& $venvPython -m pip install -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Backend dependency installation failed."
}

Push-Location $frontend
try {
    npm install
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend dependency installation failed."
    }
}
finally {
    Pop-Location
}

$backendEnv = Join-Path $backend ".env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $backend ".env.example") $backendEnv
}

Write-Host "Setup complete. In VS Code, run the task 'Start Agentic AI Hub'."
