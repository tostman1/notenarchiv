#!/bin/sh
# Run on the NAS as the dedicated service identity. Never source an .env file.
set -eu
fail() { printf '%s\n' "$1" >&2; exit 1; }
config=${1:-.env}
[ -f "$config" ] || fail 'Environment file is missing.'
value() {
    awk -v name="$1" 'index($0,name "=")==1 { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; count++ } END { if(count!=1) exit 1 }' "$config"
}
uid=$(value APP_UID) || fail 'APP_UID must occur exactly once.'
gid=$(value APP_GID) || fail 'APP_GID must occur exactly once.'
case "$uid:$gid" in *[!0-9:]*|:*|*:) fail 'UID/GID must be numeric.';; esac
[ "$uid" -gt 0 ] && [ "$gid" -gt 0 ] || fail 'Use a non-root service identity.'
[ "$(id -u)" = "$uid" ] || fail 'Run this check as the configured service account.'
[ "$(id -g)" = "$gid" ] || fail 'Run this check with the configured dedicated service group.'
[ "$(value APP_BIND)" = '127.0.0.1' ] || fail 'Preview backend must bind to loopback.'
[ "$(value PREVIEW_DATA_ONLY)" = 'TRUE' ] || fail 'Preview requires empty or synthetic data only.'
image=$(value APP_IMAGE) || fail 'APP_IMAGE is required.'
printf '%s' "$image" | grep -Eq '^ghcr\.io/tostman1/notenarchiv@sha256:[0-9a-f]{64}$' || fail 'Use the published immutable image digest.'
canonical=''
for key in SOURCE_HOST CURATED_HOST PROCESSED_HOST STATUS_HOST EXPORT_HOST DATA_HOST; do
    path=$(value "$key") || fail 'A storage path is missing or repeated.'
    case "$path" in /*) ;; *) fail 'Host roots must be absolute.';; esac
    [ -d "$path" ] && [ -r "$path" ] && [ -x "$path" ] || fail 'A host root is missing or unreadable.'
    resolved=$(readlink -f "$path") || fail 'Cannot resolve a host root.'
    [ "$resolved" = "$path" ] || fail 'Host roots must be canonical and have no symlink components.'
    old_ifs=$IFS
    IFS='
'
    for prior in $canonical; do
        case "$path/" in "$prior/"*) fail 'Host storage roots overlap.';; esac
        case "$prior/" in "$path/"*) fail 'Host storage roots overlap.';; esac
    done
    IFS=$old_ifs
    canonical="${canonical}${canonical:+
}$path"
    if [ "$key" = SOURCE_HOST ]; then
        [ ! -w "$path" ] || fail 'RAW is writable by the service identity at the host boundary.'
        [ ! -w "$(dirname "$path")" ] || fail 'The RAW root could be renamed via its parent directory.'
    elif [ "$key" = DATA_HOST ]; then
        [ -w "$path" ] || fail 'DATA is not writable by the service identity.'
    fi
done
secret=$(value SECRET_HOST) || fail 'SECRET_HOST is required.'
[ -f "$secret" ] && [ -r "$secret" ] && [ ! -L "$secret" ] || fail 'Protected secret file is missing or unreadable.'
[ ! -w "$secret" ] || fail 'The service identity must not be able to replace its secret.'
printf '%s\n' 'Host preflight passed. No RAW writes were attempted. DSM ACL and synthetic negative tests remain mandatory.'
