#!/bin/sh
# Run on the NAS as the dedicated service identity. Never source an .env file.
set -eu
fail() { printf '%s\n' "$1" >&2; exit 1; }
for tool in awk grep readlink id dirname stat; do command -v "$tool" >/dev/null || fail 'A required host preflight tool is unavailable.'; done
if [ "${1:-}" = '--simple' ]; then
    [ "$#" = 4 ] || fail 'Usage: preflight-host.sh --simple UID GID ROOT'
    simple_uid=$2 simple_gid=$3 simple_root=$4
else
    config=${1:-.env}
    [ -f "$config" ] || fail 'Environment file is missing.'
fi
env_value() {
    awk -v name="$1" 'index($0,name "=")==1 { sub(/^[^=]*=/, ""); sub(/\r$/, ""); print; count++ } END { if(count!=1) exit 1 }' "$config"
}
value() {
    if [ "${simple_root:-}" ]; then
        case "$1" in
            APP_UID) printf '%s\n' "$simple_uid";;
            APP_GID) printf '%s\n' "$simple_gid";;
            APP_BIND) printf '%s\n' '127.0.0.1';;
            PREVIEW_DATA_ONLY) printf '%s\n' 'TRUE';;
            APP_IMAGE) printf '%s\n' 'ghcr.io/tostman1/notenarchiv@sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d';;
            SOURCE_HOST) printf '%s/raw\n' "$simple_root";;
            CURATED_HOST) printf '%s/clean\n' "$simple_root";;
            PROCESSED_HOST) printf '%s/processed\n' "$simple_root";;
            STATUS_HOST) printf '%s/status\n' "$simple_root";;
            EXPORT_HOST) printf '%s/export\n' "$simple_root";;
            DATA_HOST) printf '%s/data\n' "$simple_root";;
            SECRET_HOST) printf '%s/secrets/django_secret_key\n' "$simple_root";;
            *) return 1;;
        esac
    else
        env_value "$1"
    fi
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
        [ "$(stat -c '%u' "$path")" != "$uid" ] || fail 'The service must not own RAW and be able to change its mode.'
        child=$path
        ancestor=$(dirname "$path")
        while :; do
            [ "$(stat -c '%u' "$ancestor")" != "$uid" ] || fail 'The service must not own a RAW ancestor.'
            if [ -w "$ancestor" ]; then
                # A sticky shared temp parent cannot rename another owner's child.
                [ -k "$ancestor" ] && [ "$(stat -c '%u' "$child")" != "$uid" ] ||
                    fail 'A RAW ancestor is service-writable; fix the host permission boundary.'
            fi
            [ "$ancestor" != '/' ] || break
            child=$ancestor
            ancestor=$(dirname "$ancestor")
        done
    elif [ "$key" = DATA_HOST ]; then
        [ -w "$path" ] || fail 'DATA is not writable by the service identity.'
    fi
done
secret=$(value SECRET_HOST) || fail 'SECRET_HOST is required.'
[ -f "$secret" ] && [ -r "$secret" ] && [ ! -L "$secret" ] || fail 'Protected secret file is missing or unreadable.'
[ ! -w "$secret" ] || fail 'The service identity must not be able to replace its secret.'
[ ! -w "$(dirname "$secret")" ] || fail 'The service identity must not be able to replace its secret directory entry.'
[ "$(readlink -f "$secret")" = "$secret" ] || fail 'The secret path must be canonical without symlinks.'
printf '%s\n' 'Host preflight passed. No RAW writes were attempted. DSM ACL and synthetic negative tests remain mandatory.'
