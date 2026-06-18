$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $repoRoot
try {
    . (Join-Path $PSScriptRoot "load_dev_ports.ps1")

    $webHost = if ($env:VITE_WEB_HOST) { $env:VITE_WEB_HOST } else { "127.0.0.1" }
    $webPort = if ($env:VITE_WEB_PORT) { $env:VITE_WEB_PORT } else { "5173" }
    $apiHost = if ($env:CF_API_HOST) { $env:CF_API_HOST } else { "127.0.0.1" }
    $apiPort = if ($env:CF_API_PORT) { $env:CF_API_PORT } else { "8020" }

    if (-not $env:VITE_API_PROXY_TARGET) {
        if ($env:VITE_DEV_API_PROXY_TARGET) {
            $env:VITE_API_PROXY_TARGET = $env:VITE_DEV_API_PROXY_TARGET
        }
        else {
            $env:VITE_API_PROXY_TARGET = "http://${apiHost}:${apiPort}"
        }
    }

    Push-Location "apps/web"
    try {
        & npm run dev -- --host $webHost --port $webPort
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}
