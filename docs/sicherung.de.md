# Sicherung und Wiederherstellung

Die neuen Befehle sind im aktuellen Quellcode enthalten, **nicht** im bisher
veröffentlichten Preview-Image. Installation/Update erfordern eigene Freigabe.

Vor echten Archivimporten muss eine vollständige Sicherung eingerichtet und
privat auf dem NAS geprüft werden. Dieses Entwicklungspaket richtet weder ein
NAS-Ziel noch eine automatische Sicherung ein.

## Sicherung

1. Web, Gateway und Worker kontrolliert stoppen; Verwaltungsbefehle beenden.
   Während der Sicherung auch keine externen Änderungen über SMB durchführen.
2. Ein neues, geschütztes Sicherungsverzeichnis außerhalb aller aktiven
   Archiv-/Datenverzeichnisse auswählen. Alte Sicherungen nie überschreiben.
3. Vollständige aktive Konfiguration, passende Geheimnisse und exakten
   Image-Digest bereitstellen. Eine bestehende unabhängige RAW-Sicherung muss
   als lesbarer Dateibaum vorliegen; der Befehl prüft sie ausschließlich lesend.
4. `backup_installation` mit explizitem Ziel, `--config-dir`, `--raw-backup`
   und `--image` aufrufen; technische Beispiele stehen in [BACKUP.md](BACKUP.md).
5. Den ausgegebenen Manifest-SHA-256 separat und geschützt aufbewahren.
   Erfolgreich gesichert werden Datenbank, echte CLEAN-/PROCESSED-Dateien,
   STATUS, dauerhafte Daten und Konfiguration/Schlüssel. Ausgaben nur mit
   `--include-exports`; Caches und Logs sind standardmäßig ausgeschlossen.

Aktive Dienste, unklare Dateioperationen, fehlende/veränderte Dateien und
überschrittene Grenzen führen zum Abbruch. Erst reguläre Wiederherstellung der
Worker-Operationen durchführen. Niemals Sperrdateien löschen oder Fehler umgehen.
Ein abgebrochenes Teilverzeichnis ist keine gültige Sicherung.

## Wiederherstellungsprobe

`restore_installation` benötigt das Sicherungsverzeichnis, ein **neues isoliertes**
Ziel und `--manifest-sha256` aus dem separat geschützten Nachweis. Es prüft alle
Dateien und Datenbankreferenzen und überschreibt keine aktive Installation.
RAW wird weder angelegt noch verändert; dafür bleibt die unabhängige NAS-Sicherung
zuständig.

Die kopierte Konfiguration kann noch aktive Pfade enthalten: **nicht unverändert
starten**. Alle Pfade, Projektname, Port und Schlüssel bewusst auf isolierte Ziele
umstellen; unabhängiges RAW nur lesend einbinden. Passendes freigegebenes Image
verwenden, Berechtigungen und Vorprüfung kontrollieren. Danach Anmeldung,
Zuordnungen und repräsentative PDF-Vorschauen prüfen und privat dokumentieren.

Softwaretests mit synthetischen Dateien ersetzen keine NAS-Abnahme von Ziel,
Aufbewahrung, ACLs, Speichermedium und tatsächlicher Wiederherstellbarkeit.
