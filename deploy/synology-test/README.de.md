# Notenarchiv-Testversion auf der DS224+

**Nur synthetische Testdaten. Keine Produktionsfreigabe, keine echten Noten oder
Mitgliederdaten anschließen.** Diese Ausgabe enthält die integrierten Funktionen
bis WP-39. Das alte Image `0.1.0-preview.1` ist dafür ungeeignet.

## 1. Voraussetzungen und Download

DSM 7.2 oder neuer mit Container Manager, lokale NAS-Datenspeicherung, ein privater
HTTPS-Name und ein vom Browser akzeptiertes Zertifikat. Einmalige Einrichtung
über eine private SSH-Konsole als Administrator. Kein Image-Build auf der NAS.
DSM-/Docker-Version, RAM und ACLs müssen vor dem Start tatsächlich geprüft werden.

Laden Sie das **notenarchiv-synology-test.tar.gz** der neuen Test-Prerelease unter
<https://github.com/tostman1/notenarchiv/releases> herunter. Entpacken Sie es mit
File Station in einen privaten Administrator-Downloadordner. Enthalten sind die
fertige `compose.yaml`, diese Anleitung, Vorbereitung, Zugriffsprüfung und Demo.
Die YAML enthält bereits den veröffentlichten Image-Digest; nicht ersetzen.
Eine Quellcode-YAML mit „Publication pending“ ist **kein Installationspaket**.

## 2. Dienstkonto und getrennte Ordner

**Systemsteuerung → Benutzer und Gruppe:** eigenes Konto `svc_notenarchiv_test`
und eigene Gruppe `notenarchiv_test_service`, nur dieses Konto in dieser Gruppe.
Keine Administrator-/Dockerrechte oder Zugriff auf echte Notenfreigaben.

In der Konsole des Downloadordners:

```sh
id svc_notenarchiv_test
id -u svc_notenarchiv_test
getent group notenarchiv_test_service
```

UID des Kontos und GID der **eigenen** Gruppe einsetzen, nicht die Gruppe `users`:

```sh
sudo sh prepare.sh IHRE_UID IHRE_GID
```

Der Helfer erstellt ausschließlich fehlende Ordner unter
`/volume1/docker/notenarchiv-test`: `raw`, `clean`, `processed`, `status`, `export`,
`data`, `secrets`, `config`. Ein zufälliger Schlüssel wird geschützt erzeugt.
Bestehende Dateien, Schlüssel und Rechte bleiben unverändert. Bei fehlendem
Schlüssel und vorhandenen Daten: abbrechen und Originalschlüssel wiederherstellen.
Kein rekursives chmod/chown, kein `chmod 777`.

RAW sowie dessen Vorfahren gehören nicht dem Dienstkonto; RAW ist am Host nur
lesbar. Geerbte DSM-ACLs gegebenenfalls **gezielt** im Berechtigungseditor prüfen.
Der Helfer prüft als echte Dienstidentität. Fehler nicht durch Abschalten von
Schutzprüfungen umgehen. Kopieren Sie die angepasste YAML in `config/compose.yaml`.

## 3. Genau drei Pflichtänderungen

| Markierung | Wert |
| --- | --- |
| EDIT 1 | `user: "UID:GID"` aus der Vorbereitung |
| EDIT 2 | privater Hostname in `APP_ALLOWED_HOSTS`, `localhost,127.0.0.1` behalten |
| EDIT 3 | derselbe Name als `https://NAME` in `APP_CSRF_TRUSTED_ORIGINS` |

Standardpfade, Image-Digest und Port 8090 bleiben unverändert. Keine `.env`,
kein Passwort/Schlüssel in der YAML. Drink-POS auf 8089 bleibt unberührt.
Bei anderem Volume alle `/volume1/docker/notenarchiv-test`-Pfade konsistent ändern
und denselben absoluten Testpfad als drittes Argument an `prepare.sh` übergeben.

## 4. Projekt und einmalige Einrichtung

**Container Manager → Projekt → Erstellen**: Name `notenarchiv-test`, Projektpfad
`/volume1/docker/notenarchiv-test/config`, fertige YAML importieren. Noch nicht
starten. Werkzeugdienste sind im Profil `tools`, nicht dauerhaft aktivieren.
Container Manager kann die Datei `docker-compose.yml` nennen. Verwenden Sie nur
die tatsächlich aktive Projektdatei; im folgenden `compose.yaml` ggf. ersetzen:

```sh
cd /volume1/docker/notenarchiv-test/config
sudo docker compose -f compose.yaml config --quiet
sudo docker compose -f compose.yaml pull
sudo docker compose -f compose.yaml --profile tools run --rm initialize
sudo docker compose -f compose.yaml --profile tools run --rm archivist
```

Benutzername und starkes Passwort werden interaktiv eingegeben, Passwort verdeckt.
Keine Standardkonten, keine NAS-Entwickleranmeldung. Ohne Migration startet die
Anwendung absichtlich nicht. Wartung nur bei gestopptem Web **und** Worker.

## 5. Privates HTTPS und Start

**Systemsteuerung → Anmeldeportal → Erweitert → Reverse Proxy**:

- Quelle HTTPS, Ihr privater Hostname, Port 443, passendes Zertifikat zuweisen.
- Ziel HTTP, `127.0.0.1`, Port **8090**.
- Benutzerdefinierter Request-Header `X-Forwarded-Proto` fest auf `https` setzen;
  Hostnamen erhalten. Client-Header nicht ungeprüft übernehmen.
- Keine Router-Portfreigabe. Zugang nur privat, gegebenenfalls über vorhandenes VPN.

**Sicherheitsgate:** Docker vor 28 kann Loopback-Ports im gleichen L2-Netz dennoch
erreichbar machen. Bei unbekannter/älterer Version erst eine wirksame DSM-/Docker-
Firewallregel verifizieren oder Container Manager aktualisieren. Von einem
anderen LAN-Gerät müssen NAS-IP:8090 und Containeradressen unerreichbar sein.
**Bei fehlender Abschirmung nicht starten/anmelden.** Kein LAN-HTTP-Ausweichweg.

Start im Container Manager oder:

```sh
sudo docker compose -f compose.yaml up -d notenarchiv-test-web notenarchiv-test-worker notenarchiv-test-gateway
sudo docker compose -f compose.yaml ps
```

Alle drei Dienste müssen `healthy` sein. Browser: `https://IHR_PRIVATER_NAME/`.
`/healthz` meldet `ok`; **Aufträge** zeigt die eigene Worker-Bereitschaft.
Web und Worker haben nur ein internes Netz. Gateway hat keine Daten-/Secret-Mounts.

## 6. Optionales Demo-Szenario ohne automatische Freigabe

Die Demo erzeugt drei originale Teststücke mit je Posaune 1/2. Posaune 3 fehlt
absichtlich; Alpha hat zwei A4-Seiten für die A3-Paarung. Auf einem Rechner mit Python (keine Zusatzpakete):

```sh
python demo.py demo-noten
```

Als Administrator diese neuen Dateien mit File Station nach `raw/` kopieren,
Dienstgruppe Leserecht geben, **kein** Schreibrecht. Bestehende Dateien nicht
ersetzen. Es gibt keinen Import-/Autoapprove-Trick im Produktimage.

Im Browser unter **Instrumente und Stimmen** Posaune, Bassschlüssel, Stimmen
1/2/3 anlegen; unter **Mitglieder** drei erfundene Personen „Testperson Alpha“,
„Testperson Beta“, „Testperson Gamma“ mit diesen regulären Stimmen. Unter **Werke
und Arrangements** „Testmarsch Alpha“, „Testpolka Beta“, „Testwalzer Gamma“ anlegen.

**Indizierung → gesamtes Archiv**: Auftrag abwarten. **Prüfwarteschlange**: jede
PDF wirklich ansehen, Arrangement/Stimme speichern, eigene visuelle Prüfung
ausdrücklich bestätigen, dann Freigabe beauftragen. Erst die erfolgreiche
Worker-Publikation macht Noten verwendbar. Öffnen allein ist keine Freigabe.

Projekt „Synthetische Testmappe“ erstellen, drei Stücke und eine Reserve einfügen,
drei Mitglieder auswählen. In der **Matrix** Gamma für ein Stück bewusst auf
Posaune 2 setzen. Andere Stücke bleiben fehlend. Neu laden, Override/Reserve
prüfen. **Vorprüfung**: fehlende Noten ausdrücklich anerkennen. Persönliche
Lese-PDFs, reguläre A4/A3-Druck-PDFs, Auszüge und Inhaltsverzeichnis erzeugen.
**Notenausgaben**: herunterladen, Projekt ändern, Veraltungsstatus und gezielte
Neuerstellung prüfen. Vorige Dateien/Snapshots bleiben unverändert erhalten.

OCR, Scanaufbereitung, Marschbuch-spezifisches Drucklayout und physische Drucker
bleiben mit **„Noch nicht verfügbar“** deaktiviert. Reguläre Druck-PDF bedeutet
Dateierzeugung, nicht tatsächlichen Druck. Gesamte NAS-Produktionsabnahme fehlt.

## 7. Neustart, Fehler, Update und Entfernen

Im Container Manager Logs/Zustand jedes Dienstes öffnen; Auftragsdetails im Browser.
Keine privaten Daten/Schlüssel in Fehlerberichte kopieren. `startup_rejected`:
UID/GID, Mountpfade, RAW-Rechte, HTTPS-Namen und Secret prüfen. Worker nicht bereit:
Migration, Singleton/SQLite und Logs prüfen, keine Lockdatei löschen. PDF-Fehler:
Auftragsdetails und exakte Archivversion prüfen, keine beschädigte Note ersetzen.
Login/CSRF-Fehler: Zertifikat, Host und HTTPS-Origin abgleichen, Cookies nicht unsicher machen.

```sh
sudo docker compose -f compose.yaml restart
sudo docker compose -f compose.yaml ps
sudo docker compose -f compose.yaml stop
```

Nach Neustart anmelden und gespeichertes Projekt, Freigaben, Ausgaben und Worker
prüfen. `restart` übernimmt keine geänderte YAML; dafür Projekt neu erstellen/
`up -d --force-recreate` mit den drei Dienstnamen.

**Update:** stoppen, alle acht getrennten Ordner inklusive Secret und aktiver
Konfiguration konsistent privat sichern (lokaler NAS-Snapshot/Backup bei gestoppten
Diensten), Sicherung überprüfen. Neue verifizierte Testausgabe herunterladen,
nur Image-Digest bewusst ändern; Daten/Secret und Bind-Pfade behalten. Migration
einmal mit `initialize`, dann drei Dienste neu erstellen und Funktionsprüfung.
Keine automatische Datenbank-Neuanlage oder PDF-Überschreibung.

**Rollback:** altes Image allein reicht bei Schemaänderungen nicht. Neuen Zustand
erhalten, vollständige Vor-Update-Sicherung in neue isolierte Testordner zurückspielen,
alte Konfiguration/Digest verwenden und privat prüfen. Änderungen nach Sicherung
fehlen. Nie ungeprüfte Reverse-Migration oder bestehende Daten überschreiben.

**Entfernen:** nur Projekt `notenarchiv-test` stoppen und in Container Manager
entfernen oder `docker compose -f compose.yaml down`. Bind-Daten bleiben bestehen.
Kein `prune`, keine fremden Container/Volumes löschen. Testordner nach Sicherung
bei Bedarf bewusst in File Station entfernen, nicht per pauschalem rekursivem Befehl.

**Noch auf Ihrer Hardware abzunehmen:** tatsächliche DSM/Compose-Unterstützung,
RAW-ACL inklusive Rename/Delete, HTTPS/Firewall/Loopback-Abschirmung, lokales
SQLite/WAL, RAM/OOM/Scratch, Worker-Recovery und konsistente Wiederherstellung.
Linux-CI ist Software-Nachweis, kein behaupteter Synology-Test.
