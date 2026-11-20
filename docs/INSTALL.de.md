# Kurzanleitung: erste Notenarchiv-Vorschau

Diese Version dient zum Einrichten und Prüfen der Installation. Anmeldung,
Abmeldung, deutsche Oberfläche, Systemprüfung und Diagnoseansicht sind
verfügbar. Archivimport, Mitglieder, Projekte, OCR, PDF-Ausgabe und Drucken
sind **noch nicht verfügbar**. Es läuft kein Hintergrunddienst.

**Verwenden Sie nur neue, leere Verzeichnisse oder synthetische Testdaten.
Verbinden Sie Ihr echtes Notenarchiv noch nicht.**

1. Laden Sie die Installationsdateien der freigegebenen GitHub-Vorabversion
   herunter. `release-digest.txt` enthält erst nach erfolgreicher Veröffentlichung
   das tatsächlich verfügbare Image. Ein vorgeschlagener Tag genügt nicht.
2. Erstellen Sie in DSM einen eigenen Benutzer ohne Administratorrechte,
   beispielsweise `svc_notenarchiv`, und eine eigene Dienstgruppe ohne weitere
   Benutzer. Ermitteln Sie die tatsächliche UID und die GID dieser Dienstgruppe.
3. Legen Sie getrennte Ordner für RAW, CLEAN, PROCESSED, STATUS, EXPORT und
   DATA an. Der Dienst erhält auf RAW auch in DSM nur Leserechte. DATA gehört
   dem Dienst; der geheime Schlüssel liegt getrennt und geschützt.
4. Entpacken Sie die Installationsdateien in einen privaten Projektordner.
   Kopieren Sie `.env.example` nach `.env` und tragen Sie Image-Digest, IDs,
   neue Testpfade und den privaten HTTPS-Namen ein. Der Port bleibt an
   `127.0.0.1` gebunden. Passwörter und Schlüssel gehören nicht in `.env`.
5. Führen Sie die Host-Prüfung als Dienstbenutzer und `docker compose config`
   aus. Die genauen Befehle und Berechtigungen stehen in [INSTALL.md](INSTALL.md).
6. Laden Sie das Image. Bei privatem GHCR-Zugriff verwenden Sie eine privat
   gespeicherte Registry-Anmeldung mit `read:packages`; geben Sie diese Daten
   niemals im Chat oder im Repository weiter.
7. Führen Sie bei gestopptem Webdienst einmal `migrate` und anschließend
   `admin` über das Compose-Profil `tools` aus. Der Benutzer wird interaktiv
   angelegt, das Passwort verdeckt eingegeben und nicht in Containerlogs gespeichert.
8. Importieren Sie in Container Manager ein Projekt aus `compose.yaml` und
   starten Sie danach Webdienst und Gateway. Das kleine Gateway verwendet dasselbe
   Image, hat keine Daten-/Schlüssel-Mounts und macht nur den Loopback-Zugang
   erreichbar. Die Werkzeugdienste starten nicht automatisch.
9. Richten Sie in DSM den privaten HTTPS-Reverse-Proxy auf
   `http://127.0.0.1:8085` ein. Er muss `X-Forwarded-Proto` fest auf `https`
   setzen. Verwenden Sie ein vom Browser akzeptiertes Zertifikat.
10. Prüfen Sie Anmeldung, Abmeldung, mobile Darstellung, Neustart und
    `https://IHR_PRIVATER_NAME/healthz`. Die Anwendung muss ihre Konten nach
    einem Neustart behalten. Testen Sie die Wiederherstellung in getrennten Ordnern.

Die verbindlichen technischen Details stehen in [INSTALL.md](INSTALL.md),
[UPDATE.md](UPDATE.md), [RESTORE.md](RESTORE.md) und [DEBUG_MODE.md](DEBUG_MODE.md).
Ändern Sie keine Schutzmaßnahmen, um eine fehlgeschlagene Prüfung zu umgehen.
Ein tatsächlicher NAS-Test oder der Anschluss realer Noten benötigt eine
gesonderte Freigabe; beides wird durch die Veröffentlichung nicht ausgeführt.
