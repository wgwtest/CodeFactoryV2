$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $repoRoot
try {
    . (Join-Path $PSScriptRoot "load_dev_ports.ps1")

    $apiHost = if ($env:CF_API_HOST) { $env:CF_API_HOST } else { "127.0.0.1" }
    $apiPort = if ($env:CF_API_PORT) { $env:CF_API_PORT } else { "8020" }

    & uv run uvicorn app.main:app --reload --app-dir apps/api --host $apiHost --port $apiPort
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
