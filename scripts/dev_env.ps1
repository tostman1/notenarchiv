# Local development environment (PowerShell).
# Usage: . ./scripts/dev_env.ps1
#
# Selects the local profile explicitly (loopback-only, synthetic roots under
# .dev/, git-ignored). Production security settings are not weakened: this
# script only chooses development data locations; the nas profile remains
# the deployment default and is used when this is not sourced.

$ErrorActionPreference = "Stop"

$env:NOTENARCHIV_PROFILE = "local"
if (-not $env:DEBUG_MODE) { $env:DEBUG_MODE = "FALSE" }
if (-not $env:NOTENARCHIV_LOCAL_ROOT) { $env:NOTENARCHIV_LOCAL_ROOT = ".dev" }
