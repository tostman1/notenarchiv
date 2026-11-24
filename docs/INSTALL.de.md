# Notenarchiv auf der Synology installieren

**Aktuelle Funktionen bis WP-39 testen:** verwenden Sie die eigenständige
[Synology-Testanleitung](../deploy/synology-test/README.de.md) und deren neue
verifizierte Testausgabe. Die folgende Anleitung beschreibt weiterhin das
historische web-only Preview und aktualisiert dessen Image nicht.

Diese Anleitung richtet eine **neue, leere Testinstallation** ein. Verbinden Sie
noch keine echten Noten oder Mitgliederdaten. Die mitgelieferte `configuration.yaml`
verwendet ein festes, veröffentlichtes Image. Im aktuellen Quellpaket ist dies
`0.1.0-preview.1`: Anmeldung, deutsche Oberfläche und Diagnose; noch kein nutzbares
Notenarchiv. Neuere Quellcode-Funktionen sind darin nicht enthalten.

Sie benötigen Container Manager, ein Administratorkonto für die Einrichtung und
einen privaten HTTPS-Namen mit einem vom Browser akzeptierten Zertifikat. Die
Einrichtung benötigt einmalig eine private SSH-Konsole. Es gibt keine automatische
Migration und kein vorgegebenes Anwendungspasswort.

## 1. Installationsdateien herunterladen

Laden und entpacken Sie die [aktuellen Installationsdateien als ZIP](https://github.com/tostman1/notenarchiv/archive/refs/heads/main.zip).
Benötigt werden `configuration.yaml` und der Ordner `scripts`. Kopieren Sie das
entpackte Paket über File Station in einen nur für Administratoren zugänglichen
Downloadordner auf der NAS. Öffnen Sie dort eine SSH-Konsole.

Das bereits veröffentlichte Preview-Installationspaket bleibt unverändert und
enthält diese vereinfachten Dateien noch nicht. Künftige freigegebene Pakete
enthalten sie direkt. Sie brauchen keine Entwicklungsdokumente zu lesen.

## 2. Dienstkonto und Ordner vorbereiten

Legen Sie in **Systemsteuerung → Benutzer und Gruppe** einen Benutzer
`svc_notenarchiv` und eine eigene Gruppe `notenarchiv_service` an. Nur dieser
Benutzer gehört in die Dienstgruppe. Er erhält keine Administrator-, Docker-
oder sonstigen unnötigen Anwendungsrechte.

Ermitteln Sie in der privaten Konsole mit `id svc_notenarchiv` dessen **UID** und
die **GID der eigenen Dienstgruppe**. Die allgemeine Gruppe `users` ist ungeeignet.
Ersetzen Sie im folgenden Befehl die beiden Zahlen durch Ihre tatsächlichen IDs:

```sh
sudo sh scripts/prepare-install.sh 1026 65536
```

Der Helfer legt `/volume1/docker/notenarchiv` mit `raw`, `clean`, `processed`,
`status`, `export`, `data`, `secrets` und `config` an. Er erstellt einen zufälligen
Schlüssel direkt in einer geschützten Datei. Vorhandene Dateien, Schlüssel und
Berechtigungen werden nicht überschrieben oder rekursiv geändert. Eine erneute
Prüfung einer korrekt vorbereiteten Installation ist möglich.

**Pflicht:** RAW muss auch in den DSM-Dateirechten nur lesbar sein. Der Dienst
darf weder RAW noch einen übergeordneten Ordner umbenennen können. DATA muss ihm
gehören und beschreibbar sein; der Schlüssel ist nur lesbar. Der Helfer prüft diese
Zugriffe als Dienstkonto. Bei geerbten DSM-ACLs kann eine gezielte Korrektur im
Berechtigungseditor nötig sein. Beheben Sie die gemeldete Ursache; verwenden Sie
kein `chmod 777` und ändern Sie keine bestehenden Archivfreigaben pauschal.

Die Beispielzahlen sind keine Standardwerte. Nicht vorhandene oder ungeeignete
Konten werden abgewiesen. Andere Volumes oder vorhandene Installationen gehören
zur [erweiterten Einrichtung](INSTALL.md), nicht zu dieser Erstinstallation.

## 3. Nur drei Werte in configuration.yaml ändern

| Markierung | Eintrag |
| --- | --- |
| EDIT 1 | `user`: die vom Helfer ausgegebene Zeichenfolge `UID:GID` |
| EDIT 2 | `APP_ALLOWED_HOSTS`: Ihren privaten HTTPS-Namen einsetzen; `localhost,127.0.0.1` behalten |
| EDIT 3 | `APP_CSRF_TRUSTED_ORIGINS`: derselbe Name mit `https://`, ohne abschließenden Schrägstrich |

Beispiel: `notenarchiv.verein.intern` und `https://notenarchiv.verein.intern`.
Hostliste und HTTPS-Ursprung erfüllen unterschiedliche Sicherheitsprüfungen und
müssen deshalb beide angegeben werden. Pfade, Image und Port bleiben im
Standardfall unverändert. **Keine `.env`, Passwörter oder Schlüssel in der YAML.**


## 4. Projekt in Container Manager anlegen

Wählen Sie **Container Manager → Projekt → Erstellen**:

- Projektname: `notenarchiv`.
- Projektordner: `/volume1/docker/notenarchiv/config`.
- Quelle: Compose-Datei hochladen oder im Editor erstellen. Fügen Sie den
  vollständigen Inhalt Ihrer angepassten `configuration.yaml` ein.
- **Nach dem Assistenten noch nicht starten.** Die Werkzeugdienste `migrate`
  und `admin` dürfen nicht als dauerhafte Dienste aktiviert werden.

Container Manager speichert die Projektdatei üblicherweise als `docker-compose.yml`.
Verwenden Sie anschließend genau diese Projektdatei; pflegen Sie keine zweite
abweichende Kopie. Die folgenden Konsolenbefehle werden im Projektordner ausgeführt:

```sh
cd /volume1/docker/notenarchiv/config
sudo docker compose config --quiet
sudo docker compose pull
```

Die Prüfung muss erfolgreich sein. Das veröffentlichte Image ist derzeit öffentlich
abrufbar; keine Registry-Zugangsdaten gehören in die YAML. Bei abweichender
Dateibenennung ergänzen Sie bei jedem Compose-Befehl `-f DATEINAME`.

## 5. Datenbank initialisieren

Das Projekt bleibt gestoppt. Führen Sie einmal aus:

```sh
sudo docker compose --profile tools run --rm migrate
```

Ein erneuter Migrationslauf ist möglich, aber nur bei gestopptem Webdienst.
Die Anwendung startet ohne initialisierte Datenbank bewusst nicht.

## 6. Erstes Archivistenkonto erstellen

```sh
sudo docker compose --profile tools run --rm admin
```

Geben Sie Benutzername und ein starkes Passwort **interaktiv** ein. Das Passwort
wird verdeckt eingegeben; dieser Werkzeugdienst speichert keine Containerlogs.
Es gibt kein Standardkonto. Weitere Archivisten haben dieselben fachlichen Rechte.

## 7. Privaten HTTPS-Zugang einrichten

Richten Sie in **Systemsteuerung → Anmeldeportal → Erweitert → Reverse Proxy**
Ihren HTTPS-Namen mit vertrauenswürdigem Zertifikat ein. Ziel ist
`http://127.0.0.1:8085`. Setzen Sie den weitergegebenen Header
`X-Forwarded-Proto` fest auf `https`. Namen und Zertifikat müssen zu Schritt 3 passen.

Der Zugang bleibt privat: keine Router-Portweiterleitung und keine direkte
Freigabe von Port 8085 ins LAN/Internet. Prüfen Sie die tatsächliche
Docker-/DSM-Abschirmung auch von einem anderen LAN-Gerät: direkte unverschlüsselte
Zugriffe auf NAS-Port 8085 und Containeradressen müssen gesperrt sein. Ältere
Docker-Versionen können trotz Loopback-Bindung zusätzliche Firewall-/Hersteller-
Korrekturen benötigen; [technische Einzelheiten](INSTALL.md#private-network-boundary).
Sicherheitsprüfungen, CSRF und sichere Cookies bleiben eingeschaltet.

## 8. Starten und prüfen

Starten Sie das Projekt in Container Manager. Regulär laufen nur `web` und
`gateway`. Warten Sie auf den Zustand **healthy** und öffnen Sie Ihren privaten
HTTPS-Namen im Browser. Prüfen Sie:

- Anmeldung und Abmeldung funktionieren; `https://IHR_NAME/healthz` meldet `ok`.
- Nach einem Projektneustart ist Ihr Konto weiterhin vorhanden.
- Noch nicht verfügbare Funktionen bleiben klar deaktiviert.
- Eine isolierte Sicherung/Wiederherstellung funktioniert vor dem ersten Update.

Damit ist der Software-Erststart geprüft. **Die tatsächliche DS224+/DSM-Version,
ACLs, TLS-Abschirmung, SQLite-Persistenz und Wiederherstellung müssen auf Ihrer
NAS noch privat geprüft werden.** Linux-CI ersetzt diese Hardware-Abnahme nicht.
Der Anschluss echter Daten benötigt eine eigene Freigabe und weitere Archiv-Sicherheitsgates.

Optional: [Diagnosemodus](DEBUG_MODE.md). Für den späteren Betrieb:
[Sicherung/Wiederherstellung](RESTORE.md), [Updates](UPDATE.md).
Fehler zu Mounts, Identität oder Schlüsseln werden durch Korrektur der Einrichtung
behoben; Schutzprüfungen werden nicht abgeschaltet.
