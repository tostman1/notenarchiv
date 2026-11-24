#!/bin/sh
# Isolated synthetic preparation only; existing objects are validated, never repaired.
set -eu
umask 077
fail() { printf '%s\n' "$1" >&2; exit 1; }
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || fail 'Aufruf: sudo sh prepare.sh UID GID [/volume1/docker/notenarchiv-test]'
[ "$(id -u)" = 0 ] || fail 'Vorbereitung als Administrator mit sudo ausführen.'
uid=$1 gid=$2 root=${3:-/volume1/docker/notenarchiv-test}
case "$uid:$gid" in *[!0-9:]*|:*|*:) fail 'UID und GID müssen numerisch sein.';; esac
[ "$uid" -gt 0 ] && [ "$gid" -gt 0 ] && [ "$gid" != 100 ] || fail 'Echte Nicht-Root-UID und eigene Dienstgruppe verwenden, nicht users/root.'
[ "$(id -u "$uid")" = "$uid" ] || fail 'Dienstkonto existiert nicht.'
case " $(id -G "$uid") " in *" $gid "*) ;; *) fail 'Dienstkonto muss Mitglied der Dienstgruppe sein.';; esac
case " $(id -Gn "$uid") " in *' administrators '*|*' sudo '*|*' wheel '*|*' docker '*) fail 'Dienstkonto darf keine Administrator-/Dockerrechte besitzen.';; esac
case "$root" in /*/notenarchiv-test) ;; *) fail 'Kanonischen absoluten Pfad mit Ende /notenarchiv-test verwenden.';; esac
case "$root" in *[[:space:]]*) fail 'Testpfad darf keine Leerzeichen enthalten.';; esac
parent=$(dirname "$root")
[ -d "$parent" ] && [ "$(readlink -f "$parent")" = "$parent" ] || fail 'Übergeordneter Ordner muss ohne Symlinks existieren.'
directory() {
    path=$root${1:+/$1} owner=$2 mode=$3
    if [ ! -e "$path" ] && [ ! -L "$path" ]; then mkdir -m "$mode" "$path"; chown "$owner:$gid" "$path"; fi
    [ -d "$path" ] && [ ! -L "$path" ] && [ "$(readlink -f "$path")" = "$path" ] || fail 'Ordner fehlt oder ist verknüpft; nichts Bestehendes ändern.'
    [ "$(stat -c '%u:%g:%a' "$path")" = "$owner:$gid:$mode" ] || fail 'Bestehende Eigentümer/Rechte abweichend; gezielt DSM-ACL prüfen.'
}
directory '' 0 750
directory raw 0 550
for name in clean processed status export; do directory "$name" "$uid" 750; done
directory data "$uid" 700
directory secrets 0 750
directory config 0 750
secret=$root/secrets/django_secret_key
temporary=''
trap 'if [ -n "$temporary" ]; then rm -f -- "$temporary"; fi' EXIT HUP INT TERM
if [ -e "$secret" ] || [ -L "$secret" ]; then
    [ -f "$secret" ] && [ ! -L "$secret" ] && [ "$(stat -c '%u:%g:%a' "$secret")" = "0:$gid:440" ] || fail 'Bestehender Schlüssel unsicher; er wurde erhalten.'
    [ "$(wc -c < "$secret")" -ge 50 ] || fail 'Bestehender Schlüssel zu kurz; Original wiederherstellen.'
else
    for item in "$root/data"/* "$root/data"/.[!.]* "$root/data"/..?*; do
        [ ! -e "$item" ] && [ ! -L "$item" ] || fail 'DATA enthält bereits Daten, Schlüssel fehlt: Original wiederherstellen.'
    done
    temporary=$(mktemp "$root/secrets/.key.XXXXXX")
    command -v openssl >/dev/null || fail 'OpenSSL fehlt; keine unsichere Schlüsselgenerierung.'
    openssl rand -hex 64 > "$temporary"
    chown "0:$gid" "$temporary"; chmod 440 "$temporary"
    ln "$temporary" "$secret" || fail 'Schlüssel existiert inzwischen; kein Überschreiben.'
    rm -- "$temporary"; temporary=''
fi
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd -P)
sudo -u "#$uid" -g "#$gid" sh -s -- "$uid" "$gid" "$root" < "$script_dir/verify-host.sh"
printf 'Testordner vorbereitet. compose.yaml user: "%s:%s". Bestehende Daten/Schlüssel erhalten.\n' "$uid" "$gid"
