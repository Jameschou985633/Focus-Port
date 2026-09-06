$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$node = 'C:\Program Files\Lenovo\AIAgent\mcp\node-v22.16.0-win-x64\node.exe'
$npm = 'C:\Program Files\Lenovo\AIAgent\mcp\node-v22.16.0-win-x64\npm.cmd'
$frontendDir = Join-Path $repoRoot 'focusport-frontend'

Write-Host 'Starting local dev API on http://127.0.0.1:8005 ...'
$oldHost = $env:HOST
$oldPort = $env:PORT
$oldViteTarget = $env:VITE_DEV_API_TARGET

try {
  $env:HOST = '127.0.0.1'
  $env:PORT = '8005'
  Start-Process -WindowStyle Hidden -FilePath $node -ArgumentList 'local-dev-api.mjs' -WorkingDirectory $repoRoot

  Write-Host 'Starting frontend on http://127.0.0.1:5177 ...'
  $env:VITE_DEV_API_TARGET = 'http://127.0.0.1:8005'
  Start-Process -WindowStyle Hidden -FilePath $npm -ArgumentList 'run dev -- --host 127.0.0.1 --port 5177' -WorkingDirectory $frontendDir

  Start-Sleep -Seconds 3
  Write-Host ''
  Write-Host 'Ready: http://127.0.0.1:5177/'
}
finally {
  $env:HOST = $oldHost
  $env:PORT = $oldPort
  $env:VITE_DEV_API_TARGET = $oldViteTarget
}
