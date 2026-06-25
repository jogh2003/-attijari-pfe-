# start_api.ps1 — Démarrage rapide du backend FastAPI
# Ce script ferme proprement l'ancien serveur sur le port 8000, puis démarre Uvicorn.

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$port = 8000
$python = Join-Path $projectRoot 'venv\Scripts\python.exe'

Write-Host "Projet : $projectRoot"
Write-Host "Port choisi : $port"

if (-Not (Test-Path $python)) {
    Write-Error "Impossible de trouver l'interpréteur Python du venv : $python"
    Write-Error "Activez le venv ou créez-le avec 'python -m venv venv' puis installez les dépendances."
    exit 1
}

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Write-Host "Le port $port est déjà utilisé par le PID $($listener.OwningProcess). Arrêt du processus..."
    Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Write-Host "Lancement du serveur Uvicorn..."
& $python -m uvicorn app.main:app --host 127.0.0.1 --port $port --log-level info
