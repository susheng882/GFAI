# GFLC dev server (ASCII only on purpose: PS 5.1 mis-parses non-ASCII comments)
# Usage:  powershell -ExecutionPolicy Bypass -File .\dev.ps1
#         powershell -ExecutionPolicy Bypass -File .\dev.ps1 -Port 8012
param(
    [int]$Port = 8011,
    [string]$Python = "D:\anaconda3\python.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$dist = Join-Path $root "web\dist\index.html"

if (-not (Test-Path $Python)) {
    Write-Host "[ERR] python not found: $Python" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $dist)) {
    Write-Host "[WARN] web/dist missing. Run: cd gflc\web ; npm run build" -ForegroundColor Yellow
} else {
    Write-Host "[OK] frontend build found: web\dist" -ForegroundColor Green
}

$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host "[ERR] port $Port already in use. Stop it first or pass -Port 8012" -ForegroundColor Red
    exit 1
}

Set-Location $backend
Write-Host "[OK] starting GFLC on http://127.0.0.1:$Port" -ForegroundColor Cyan
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
