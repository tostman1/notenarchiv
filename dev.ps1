param([Parameter(Position=0)][ValidateSet('start','stop','restart','status')][string]$Action = 'start',
      [switch]$ManualAuth, [switch]$NoBrowser, [int]$Port = 8085)
$ErrorActionPreference = 'Stop'
$arguments = @('run', 'python', 'scripts/dev.py', $Action, '--port', "$Port")
if ($ManualAuth) { $arguments += '--manual-auth' }
if ($NoBrowser) { $arguments += '--no-browser' }
Push-Location $PSScriptRoot
try { & uv @arguments } finally { Pop-Location }
