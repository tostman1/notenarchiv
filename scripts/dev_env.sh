# Local development environment (POSIX: bash/zsh).
# Usage: source scripts/dev_env.sh   (or: . ./scripts/dev_env.sh)
#
# Selects the local profile explicitly (loopback-only, synthetic roots under
# .dev/, git-ignored). Production security settings are not weakened: this
# script only chooses development data locations; the nas profile remains
# the deployment default and is used when this is not sourced.
set -euo pipefail

export NOTENARCHIV_PROFILE=local
export DEBUG_MODE="${DEBUG_MODE:-FALSE}"
export NOTENARCHIV_LOCAL_ROOT="${NOTENARCHIV_LOCAL_ROOT:-.dev}"
