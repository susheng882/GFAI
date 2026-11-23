# GFLC local one-click build + start (Windows PowerShell)
# Usage: cd gflc/deploy ; .\build.ps1
$ErrorActionPreference = "Stop"
Write-Host "=== GFLC production build ===" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop not found. Install it first." -ForegroundColor Red
    exit 1
}
docker version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker daemon is not running. Start Docker Desktop, then rerun." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker daemon available" -ForegroundColor Green

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created deploy/.env. Fill in all CHANGE_ME values, then rerun." -ForegroundColor Yellow
    exit 1
}
$cfg = Get-Content .env -Raw
if ($cfg -match "CHANGE_ME") {
    Write-Host ".env still has CHANGE_ME placeholders. Set DB/MinIO/LLM/session secrets." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] .env configured" -ForegroundColor Green

# Frontend: build React app and stage it into the image context (backend/frontend/dist).
Write-Host ">>> build React frontend" -ForegroundColor Cyan
Push-Location ../web
if (-not (Test-Path node_modules)) { npm install; if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 } }
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location
if (Test-Path ../backend/frontend/dist) { Remove-Item -Recurse -Force ../backend/frontend/dist }
Copy-Item -Recurse ../web/dist ../backend/frontend/dist
Write-Host "[OK] frontend staged -> backend/frontend/dist" -ForegroundColor Green

Write-Host ">>> docker compose build" -ForegroundColor Cyan
docker compose build
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ">>> docker compose up -d" -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ">>> waiting for health (up to 180s)" -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 3
    docker compose exec -T app curl -fsS http://127.0.0.1:8000/health *> $null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
}
if (-not $ok) {
    Write-Host "Service not ready. Check: docker compose logs -f app" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] service ready" -ForegroundColor Green
Write-Host "Frontend: http://localhost   API docs: disabled in production" -ForegroundColor Green
Write-Host "Logs: docker compose logs -f app" -ForegroundColor DarkGray
