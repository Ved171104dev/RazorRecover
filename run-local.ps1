[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [int]$ApiPort = 8000,
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot "backend"
$webRoot = Join-Path $projectRoot "apps\web"
$venvPython = Join-Path $backendRoot ".venv\Scripts\python.exe"

function Require-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. $InstallHint"
    }
}

Require-Command "python" "Install Python 3.11 or newer and reopen PowerShell."
Require-Command "npm" "Install Node.js 20 or newer and reopen PowerShell."

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating the Python virtual environment..." -ForegroundColor Cyan
    & python -m venv (Join-Path $backendRoot ".venv")
}

if (-not $SkipInstall) {
    Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
    & $venvPython -m pip install -r (Join-Path $backendRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }

    if (-not (Test-Path -LiteralPath (Join-Path $webRoot "node_modules"))) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
        Push-Location $webRoot
        try { & npm install } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
    }
}

$databasePath = (Join-Path $backendRoot "razorrecover-demo.db").Replace("\", "/")
$apiUrl = "http://localhost:$ApiPort"

Write-Host "Starting RazorRecover local demo..." -ForegroundColor Green
Write-Host "Frontend: http://localhost:$WebPort"
Write-Host "API:      $apiUrl"
Write-Host "Database: SQLite demo database (PostgreSQL remains the Docker/deployment default)"
Write-Host "Press Ctrl+C to stop both services.`n"

$apiJob = Start-Job -Name "RazorRecover-API" -ScriptBlock {
    param($backendRoot, $venvPython, $databasePath, $apiPort)
    Set-Location $backendRoot
    $env:DATABASE_URL = "sqlite:///$databasePath"
    $env:AUTO_CREATE_SCHEMA = "true"
    $env:PYTHONUNBUFFERED = "1"
    & $venvPython -m uvicorn app.main:app --host localhost --port $apiPort 2>&1 |
        ForEach-Object { $_.ToString() }
} -ArgumentList $backendRoot, $venvPython, $databasePath, $ApiPort

$webJob = $null
try {
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Milliseconds 500
        Receive-Job -Job $apiJob
        if ($apiJob.State -eq "Failed") { throw "The API failed to start." }
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri "$apiUrl/health" -TimeoutSec 2
            $apiReady = $health.StatusCode -eq 200
        } catch {
            $apiReady = $false
        }
    } until ($apiReady -or (Get-Date) -gt $deadline)

    if (-not $apiReady) { throw "The API did not become healthy within 45 seconds." }

    $webJob = Start-Job -Name "RazorRecover-Web" -ScriptBlock {
        param($webRoot, $apiUrl, $webPort)
        Set-Location $webRoot
        $env:NEXT_PUBLIC_API_URL = $apiUrl
        & npm run dev -- --port $webPort 2>&1 |
            ForEach-Object { $_.ToString() }
    } -ArgumentList $webRoot, $apiUrl, $WebPort

    while ($true) {
        Receive-Job -Job $apiJob
        Receive-Job -Job $webJob
        if ($apiJob.State -in @("Failed", "Completed", "Stopped")) {
            throw "The API process stopped unexpectedly."
        }
        if ($webJob.State -in @("Failed", "Completed", "Stopped")) {
            throw "The frontend process stopped unexpectedly."
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    @($apiJob, $webJob) | Where-Object { $_ } | Stop-Job -ErrorAction SilentlyContinue
    @($apiJob, $webJob) | Where-Object { $_ } | Remove-Job -Force -ErrorAction SilentlyContinue
    Write-Host "RazorRecover stopped." -ForegroundColor Yellow
}
