$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Compose startup failed. Check Docker Desktop and docker compose logs.' }
docker compose ps
Write-Output 'Citizen: http://localhost:3000 | Planner: http://localhost:3001 | API: http://localhost:8000/docs'
