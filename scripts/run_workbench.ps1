#Requires -Version 5.1
<#
  Developer launcher for the Block 4A validation workbench (editable install, local .venv).
  Does not contain application logic — only env, cwd, and process invocation.

  Usage (from repo root):
    .\scripts\run_workbench.ps1
    .\scripts\run_workbench.ps1 -Reload
    .\scripts\run_workbench.ps1 -NoBrowser
#>
param(
    [switch]$Reload,
    [switch]$NoBrowser,
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Write-Err($msg) { Write-Host $msg -ForegroundColor Red }

if (-not (Test-Path $VenvPython)) {
    Write-Err "No Python virtual environment at: $VenvPython"
    Write-Host "From the repo root, run once:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  pip install -e `".[dev,workbench]`""
    exit 1
}

Push-Location $RepoRoot
try {
    & $VenvPython -c "import structural_tree_app.workbench"
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Cannot import structural_tree_app.workbench (editable install missing or incomplete)."
        Write-Host "Activate .venv and install:"
        Write-Host "  pip install -e `".[dev,workbench]`""
        exit 1
    }
}
finally {
    Pop-Location
}

if (-not $env:STRUCTURAL_TREE_WORKSPACE) {
    $ws = Join-Path $RepoRoot "workspace"
    $env:STRUCTURAL_TREE_WORKSPACE = $ws
    New-Item -ItemType Directory -Force -Path $ws | Out-Null
}

if ($Reload) {
    $env:WORKBENCH_RELOAD = "1"
}

if ($Port -gt 0) {
    $env:WORKBENCH_PORT = "$Port"
}

$listenPort = if ($env:WORKBENCH_PORT) { $env:WORKBENCH_PORT } else { "8000" }
$baseUrl = "http://127.0.0.1:$listenPort"
$openUrl = "$baseUrl/workbench"

Write-Host "Repo:        $RepoRoot"
Write-Host "Workspace:   $($env:STRUCTURAL_TREE_WORKSPACE)"
Write-Host "Workbench:   $openUrl"
Write-Host "Health:      $baseUrl/health   (or: curl $baseUrl/health)"
if ($env:WORKBENCH_RELOAD -eq "1") {
    Write-Host "Reload:      ON (WORKBENCH_RELOAD=1; uvicorn reload restarts on code changes)"
} else {
    Write-Host "Reload:      off (use -Reload for autoreload)"
}
Write-Host "Stop:        Ctrl+C in this window"
Write-Host ""

if (-not $NoBrowser) {
    Start-Process cmd.exe -ArgumentList @(
        "/c", "timeout /t 2 /nobreak >nul && start `"`" `"$openUrl`""
    ) -WindowStyle Hidden
}

Set-Location $RepoRoot
& $VenvPython -m structural_tree_app.workbench
