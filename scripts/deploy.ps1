param(
    [Parameter(Mandatory=$true)][string]$Image,
    [string]$EnvFile = "$env:USERPROFILE/.inventory-agent.env"
)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $EnvFile)) { throw "Create $EnvFile with GEMINI_API_KEY and DJANGO_SECRET_KEY before deployment." }
docker info | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop must be running in Linux container mode.' }
docker pull --platform linux/amd64 $Image
if ($LASTEXITCODE -ne 0) { throw 'Image pull failed; existing app was left running.' }
$existing = docker ps -aq --filter 'name=^/inventory-agent-app$'
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect containers.' }
if ($existing) {
    docker rm -f inventory-agent-app
    if ($LASTEXITCODE -ne 0) { throw 'Cannot replace existing app.' }
}
docker run -d --platform linux/amd64 --name inventory-agent-app --restart unless-stopped -p 127.0.0.1:8000:8000 --env-file $EnvFile -e DJANGO_DB_PATH=/data/db.sqlite3 -v inventory-agent-data:/data $Image
if ($LASTEXITCODE -ne 0) { throw 'Container failed to start.' }
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $health = docker inspect --format '{{.State.Health.Status}}' inventory-agent-app
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect application health.' }
    if ($health -eq 'healthy') { Write-Output 'Deployment healthy: http://localhost:8000'; exit 0 }
    Start-Sleep -Seconds 2
}
docker logs inventory-agent-app
throw 'Deployment did not become healthy.'
