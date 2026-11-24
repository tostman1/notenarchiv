#!/bin/sh
# Service-identity ACL checks without ever writing/probing RAW.
set -eu
fail() { printf '%s\n' "$1" >&2; exit 1; }
uid=$1 gid=$2 root=$3
[ "$(id -u)" = "$uid" ] && [ "$(id -g)" = "$gid" ] || fail 'Prüfung mit echter Dienstidentität ausführen.'
for name in raw clean processed status export data; do
    path=$root/$name
    [ -r "$path" ] && [ -x "$path" ] && [ "$(readlink -f "$path")" = "$path" ] || fail 'Testordner nicht lesbar oder verknüpft.'
    if [ "$name" = raw ]; then [ ! -w "$path" ] || fail 'RAW ist schreibbar: DSM-ACL gezielt korrigieren.'
    else [ -w "$path" ] || fail 'Verwalteter Testordner nicht schreibbar: DSM-ACL gezielt prüfen.'; fi
done
find "$root/raw" -print | while IFS= read -r path; do
    [ ! -L "$path" ] || fail 'RAW-Testdaten enthalten Symlinks; keine Verknüpfungen verwenden.'
    [ -r "$path" ] && [ ! -w "$path" ] || fail 'RAW-Testdatei unlesbar oder schreibbar: DSM-ACL gezielt prüfen.'
done
child=$root/raw ancestor=$root
while :; do
    [ "$(stat -c '%u' "$child")" != "$uid" ] || fail 'Dienstkonto darf RAW/übergeordneten Ordner nicht besitzen.'
    if [ -w "$ancestor" ]; then [ -k "$ancestor" ] && [ "$(stat -c '%u' "$child")" != "$uid" ] || fail 'Übergeordneter RAW-Ordner erlaubt Umbenennen.'; fi
    [ "$(stat -c '%u' "$ancestor")" != "$uid" ] || fail 'Dienstkonto besitzt RAW-Vorfahren.'
    [ "$ancestor" != / ] || break
    child=$ancestor ancestor=$(dirname "$ancestor")
done
secret=$root/secrets/django_secret_key
[ -r "$secret" ] && [ ! -w "$secret" ] && [ ! -w "$root/secrets" ] && [ ! -L "$secret" ] || fail 'Schlüsselzugriff unsicher.'
printf '%s\n' 'Hostgrenzen geprüft, keine RAW-Schreibprobe. Private DSM-ACL/Firewall-Abnahme bleibt erforderlich.'
