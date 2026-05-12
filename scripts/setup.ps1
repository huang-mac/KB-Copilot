param(
    [switch]$SkipFrontend,
    [string]$PipIndexUrl = ""
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPath = Join-Path $Root ".venv"
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"
$BackendPath = Join-Path $Root "backend"
$FrontendPath = Join-Path $Root "frontend"

function New-ProjectVenv {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 -m venv $VenvPath
        if ($LASTEXITCODE -eq 0) {
            return
        }

        Write-Host "Python 3.11 was not found by py launcher, trying python from PATH."
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw "python from PATH must be Python 3.11 or newer."
        }

        & python -m venv $VenvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create Python virtual environment."
        }

        return
    }

    throw "Python was not found. Please install Python 3.11 or newer."
}

if (-not (Test-Path $PythonPath)) {
    Write-Host "Creating Python virtual environment at $VenvPath"
    New-ProjectVenv
}

if (-not (Test-Path $PythonPath)) {
    throw "Virtual environment was not created correctly: $PythonPath not found."
}

Write-Host "Installing backend dependencies into .venv"
$PipOptions = @()
if ($PipIndexUrl) {
    $PipOptions += @("--index-url", $PipIndexUrl)
}

& $PythonPath -m pip install @PipOptions --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install base Python packaging tools."
}

& $PythonPath -m pip install @PipOptions -e "$BackendPath[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install backend dependencies."
}

if (-not $SkipFrontend) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm was not found. Install Node.js first, or rerun with -SkipFrontend."
    }

    Write-Host "Installing frontend dependencies"
    Push-Location $FrontendPath
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

Write-Host "Setup complete."
Write-Host "Backend Python: $PythonPath"
