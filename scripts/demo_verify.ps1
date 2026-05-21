# Demo E2E verification script
# Usage: Powershell: .\scripts\demo_verify.ps1
# This script activates venv, starts the API, waits for health, obtains tokens, calls UiPath endpoints, submits a demo reclamation, and stops the API.

Write-Host "=== Demo E2E Verification — Attijari PFE ==="

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating venv..."
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found at ./venv — aborting"
    exit 1
}

# Start uvicorn in background
Write-Host "Starting API (uvicorn)..."
$proc = Start-Process -FilePath python -ArgumentList ("-m","uvicorn","app.main:app","--reload","--host","127.0.0.1","--port","8000") -NoNewWindow -PassThru
Write-Host "Started uvicorn with PID $($proc.Id)"

# Wait for health endpoint
$maxWait = 60
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { Write-Host "API health OK"; break }
    } catch {
        Start-Sleep -Seconds 1
        $waited += 1
    }
}
if ($waited -ge $maxWait) {
    Write-Host "API did not become healthy in time"
    Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
    exit 2
}

function Get-Token {
    param(
        [string]$Username,
        [string]$Password
    )
    try {
        $body = @{ username = $Username; password = $Password }
        $resp = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/auth/login -Body $body -ContentType "application/x-www-form-urlencoded" -TimeoutSec 10
        return $resp.access_token
    } catch {
        Write-Host "Login failed for $Username : $_"
        return $null
    }
}

# Get robot token
Write-Host "Obtaining robot token..."
$robotToken = Get-Token -Username "robot@attijaribank.tn" -Password "Robot@2026!"
if (-not $robotToken) {
    Write-Host "Failed to get robot token"
    Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
    exit 3
}
Write-Host "Robot token received (truncated): $($robotToken.Substring(0,30))..."

# Call GET /api/alertes?seuil=0.75
Write-Host "Calling GET /api/alertes?seuil=0.75"
$headers = @{ Authorization = "Bearer $robotToken" }
try {
    $alerts = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/alertes?seuil=0.75" -Headers $headers -TimeoutSec 10
    $count = 0
    if ($alerts) { $count = ($alerts | Measure-Object).Count }
    Write-Host "Returned $count alert(s)"
} catch {
    Write-Host "Failed to call /api/alertes: $_"
}

# Submit a demo reclamation (admin)
Write-Host "Obtaining admin token for submission..."
$adminToken = Get-Token -Username "admin@attijaribank.tn" -Password "Admin@2026!"
if (-not $adminToken) {
    Write-Host "Failed to get admin token"
    Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
    exit 4
}
$hdrAdmin = @{ Authorization = "Bearer $adminToken" }

$demo = @{ titre = "TEST_DEMO_SCRIPT"; description = "Reclamation demo pour vérification E2E"; groupe = "Helpdesk"; severite = 2 }
Write-Host "Submitting demo reclamation..."
try {
    $submit = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/reclamations/soumettre" -Headers $hdrAdmin -Body ($demo | ConvertTo-Json -Depth 5) -ContentType "application/json" -TimeoutSec 10
    if ($null -ne $submit) { Write-Host "Submission result id: $($submit.id)" } else { Write-Host "Submission returned null" }
} catch {
    Write-Host "Submission failed: $_"
}

# If alerts exist, try to close the first as robot
if ($alerts -and $alerts.Count -gt 0) {
    $firstId = $alerts[0].id
    Write-Host "Closing alert $firstId as robot..."
    $body = @{ action_effectuee = "Test action via demo script"; statut_final = "resolue" } | ConvertTo-Json
    try {
        $close = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/alertes/$firstId/cloturer" -Headers $headers -Body $body -ContentType "application/json" -TimeoutSec 10
        Write-Host "Close response: $($close | ConvertTo-Json -Depth 3)"
    } catch {
        Write-Host "Close failed: $_"
    }
}

# Run quick smoke tests
Write-Host "Running pytest tests/test_api.py -q"
pytest tests/test_api.py -q

# Stop server
Write-Host "Stopping uvicorn (PID $($proc.Id))"
Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
Write-Host "Demo E2E finished."