#!/bin/sh
# First-install preparation only. Never traverse/chmod/chown an existing tree.
set -eu
umask 077
fail() { printf '%s\n' "$1" >&2; exit 1; }
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || fail 'Usage: prepare-install.sh UID GID [/volume1/docker/notenarchiv]'
[ "$(id -u)" = 0 ] || fail 'Run preparation as an administrator with sudo.'
uid=$1 gid=$2 root=${3:-/volume1/docker/notenarchiv}
case "$uid:$gid" in *[!0-9:]*|:*|*:) fail 'UID/GID must be numeric.';; esac
[ "$uid" -gt 0 ] && [ "$gid" -gt 0 ] && [ "$gid" != 100 ] || fail 'Use the actual non-root UID and dedicated group, not users/root.'
[ "$(id -u "$uid")" = "$uid" ] || fail 'The service UID must exist on this host.'
case " $(id -G "$uid") " in *" $gid "*) ;; *) fail 'The service account must belong to the dedicated group.';; esac
case " $(id -Gn "$uid") " in *' administrators '*|*' sudo '*|*' wheel '*|*' docker '*) fail 'The service account must not have administrator/Docker rights.';; esac
case "$root" in /*/notenarchiv) ;; *) fail 'Use a canonical absolute root ending in /notenarchiv.';; esac
case "$root" in *[[:space:]]*) fail 'The simple installation root must not contain whitespace.';; esac
parent=$(dirname "$root")
[ -d "$parent" ] && [ "$(readlink -f "$parent")" = "$parent" ] || fail 'The parent must already exist without symlinks.'
[ "$(readlink -f "$root")" = "$root" ] || fail 'The installation root must be canonical, without symlinks.'
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd -P)
image='ghcr.io/tostman1/notenarchiv@sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d'

directory() {
    path=$root${1:+/$1} expected_uid=$2 mode=$3
    if [ ! -e "$path" ] && [ ! -L "$path" ]; then
        mkdir -m "$mode" "$path"
        chown "$expected_uid:$gid" "$path"
    fi
    [ -d "$path" ] && [ ! -L "$path" ] && [ "$(readlink -f "$path")" = "$path" ] || fail 'A directory is missing, replaced or symlinked.'
    [ "$(stat -c '%u:%g:%a' "$path")" = "$expected_uid:$gid:$mode" ] ||
        fail 'An existing directory has unexpected ownership/mode. Nothing existing was changed; inspect it manually.'
}
directory '' 0 750
for name in raw clean processed status export; do directory "$name" 0 550; done
directory data "$uid" 700
directory secrets 0 750
directory config 0 750

secret=$root/secrets/django_secret_key
secret_temp=''
cleanup() { if [ -n "$secret_temp" ]; then rm -f -- "$secret_temp"; fi; }
trap cleanup EXIT HUP INT TERM
if [ -e "$secret" ] || [ -L "$secret" ]; then
    [ -f "$secret" ] && [ ! -L "$secret" ] && [ "$(readlink -f "$secret")" = "$secret" ] || fail 'The existing secret is not a canonical regular file.'
    [ "$(stat -c '%u:%g:%a' "$secret")" = "0:$gid:440" ] || fail 'The existing secret has unexpected permissions; it was preserved.'
    [ "$(wc -c < "$secret")" -ge 50 ] || fail 'The existing secret is too short; it was preserved. Restore/inspect it manually.'
else
    # A missing secret alongside existing data is a recovery problem, not a new
    # installation. Never silently generate an incompatible replacement key.
    for entry in "$root/data"/* "$root/data"/.[!.]* "$root/data"/..?*; do
        [ ! -e "$entry" ] && [ ! -L "$entry" ] || fail 'DATA is not empty but the secret is missing. Restore the original secret.'
    done
    docker image inspect "$image" >/dev/null 2>&1 || docker pull "$image"
    secret_temp=$(mktemp "$root/secrets/.django-key.XXXXXX")
    docker run --rm --log-driver=none --network=none --read-only --cap-drop=ALL \
        --security-opt=no-new-privileges --user "$uid:$gid" --entrypoint python "$image" \
        -c 'import secrets; print(secrets.token_urlsafe(64))' > "$secret_temp"
    [ "$(wc -c < "$secret_temp")" -ge 50 ] || fail 'Secret generation failed; no secret was published.'
    chown "0:$gid" "$secret_temp"
    chmod 440 "$secret_temp"
    ln "$secret_temp" "$secret" || fail 'A secret already exists; it was not overwritten.'
    rm -- "$secret_temp"
    secret_temp=''
fi
# Root opens the script; the service identity need not access the download folder.
sudo -u "#$uid" -g "#$gid" sh -s -- --simple "$uid" "$gid" "$root" < "$script_dir/preflight-host.sh"
printf 'Prepared %s. Set configuration.yaml user to "%s:%s". Existing files were preserved.\n' "$root" "$uid" "$gid"
