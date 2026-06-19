$ErrorActionPreference = "Stop"

function Import-DotEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }

        $separator = $line.IndexOf("=")
        if ($separator -lt 1) {
            continue
        }

        $name = $line.Substring(0, $separator).Trim()
        if ($name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            continue
        }

        $value = $line.Substring($separator + 1).Trim()
        if ($value.Length -ge 2) {
            $first = $value.Substring(0, 1)
            $last = $value.Substring($value.Length - 1, 1)
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        Set-Item -Path "Env:$name" -Value $value
    }
}

function Get-ProcessEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    [Environment]::GetEnvironmentVariable($Name, "Process")
}

function Set-ProcessEnvDefault {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace((Get-ProcessEnv -Name $Name))) {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

Import-DotEnvFile -Path "config/dev-ports.env"
Import-DotEnvFile -Path "config/dify.local.env"

$localDifyEnv = Get-ProcessEnv -Name "CODEFACTORY_LOCAL_DIFY_ENV"
if ([string]::IsNullOrWhiteSpace($localDifyEnv)) {
    $localDifyEnv = Join-Path $HOME ".codefactory\dify.local.env"
}
Import-DotEnvFile -Path $localDifyEnv

Import-DotEnvFile -Path ".env.local"

$branchName = Get-ProcessEnv -Name "CF_DEV_BRANCH_OVERRIDE"
if ([string]::IsNullOrWhiteSpace($branchName)) {
    try {
        $branchName = (& git branch --show-current 2>$null).Trim()
    }
    catch {
        $branchName = ""
    }
}
if ([string]::IsNullOrWhiteSpace($branchName)) {
    $branchName = "main"
}

$branchKey = (($branchName.ToUpperInvariant() -replace "[^A-Z0-9]+", "_").Trim("_"))
$apiPortVar = "${branchKey}_API_PORT"
$webPortVar = "${branchKey}_WEB_PORT"
$defaultRouteVar = "${branchKey}_DEFAULT_ROUTE"

$apiPort = Get-ProcessEnv -Name $apiPortVar
if ([string]::IsNullOrWhiteSpace($apiPort)) {
    $apiPort = Get-ProcessEnv -Name "MAIN_API_PORT"
}
if ([string]::IsNullOrWhiteSpace($apiPort)) {
    $apiPort = "8020"
}

$webPort = Get-ProcessEnv -Name $webPortVar
if ([string]::IsNullOrWhiteSpace($webPort)) {
    $webPort = Get-ProcessEnv -Name "MAIN_WEB_PORT"
}
if ([string]::IsNullOrWhiteSpace($webPort)) {
    $webPort = "5173"
}

$defaultRoute = Get-ProcessEnv -Name $defaultRouteVar
if ([string]::IsNullOrWhiteSpace($defaultRoute)) {
    $defaultRoute = Get-ProcessEnv -Name "MAIN_DEFAULT_ROUTE"
}
if ([string]::IsNullOrWhiteSpace($defaultRoute)) {
    $defaultRoute = "/documents"
}

Set-ProcessEnvDefault -Name "CF_API_HOST" -Value "127.0.0.1"
Set-ProcessEnvDefault -Name "VITE_WEB_HOST" -Value "127.0.0.1"
Set-ProcessEnvDefault -Name "CF_API_PORT" -Value $apiPort
Set-ProcessEnvDefault -Name "VITE_WEB_PORT" -Value $webPort
Set-ProcessEnvDefault -Name "VITE_DEFAULT_ROUTE" -Value $defaultRoute

$proxyTarget = Get-ProcessEnv -Name "VITE_DEV_API_PROXY_TARGET"
if ([string]::IsNullOrWhiteSpace($proxyTarget)) {
    $proxyTarget = "http://$($env:CF_API_HOST):$($env:CF_API_PORT)"
}
Set-ProcessEnvDefault -Name "VITE_API_PROXY_TARGET" -Value $proxyTarget
