# Indizierung

Diese Funktion ist im aktuellen Quellstand vorhanden. Das ältere veröffentlichte
Web-Vorschau-Image wird dadurch nicht automatisch aktualisiert oder um einen
Hintergrunddienst ergänzt. Vor echten Noten sind NAS-Rechte und Backup zu prüfen.

1. Anmelden und **Indizierung** öffnen.
2. Einen RAW-relativen Unterordner angeben oder das Feld für das gesamte Archiv
   leer lassen. Bei bekannten Ordnern kann deren Detailseite verwendet werden.
3. Die Auswahl ausdrücklich bestätigen und **Indizieren** wählen. Absolute Pfade,
   Pfadumleitungen und überschneidende laufende/ungeklärte Aufträge werden abgewiesen.
4. Auf der Auftragsseite Fortschritt und Hintergrunddienst prüfen. Ohne verfügbaren
   Hintergrunddienst bleibt der Auftrag wartend. **Abbrechen** stoppt laufende
   Arbeit kooperativ; bereits abgeschlossene Kopien werden nicht gelöscht.
5. Die Ordnerseite zeigt Inventarstatus, Fehler, fehlende Quellen und Prüfanzahl.
   **STATUS-JSON veröffentlicht und geprüft** erscheint nur bei einem passenden
   abgeschlossenen Auftrag, Publikationsbeleg und unveränderten JSON-Dateihash.
   Ein Textmarker allein ist kein Erfolgs-, Freigabe- oder Vollständigkeitsnachweis.
6. **Versionen visuell prüfen** öffnet die persistente Prüfwarteschlange. Jede neue
   oder geänderte PDF muss vollständig betrachtet und ihre Stimmenzuordnung manuell
   geprüft werden. Vorschauöffnung, Dateiname und Erkennung sind keine Freigabe.

RAW wird nie verändert. Kopien liegen zunächst getrennt in CLEAN/_Ungeprueft.
Defekte/unsichere Quellen werden gemeldet; fehlende RAW-Dateien löschen keine
historischen Kopien. Die vollständige Integritätsprüfung bleibt bis WP-27 deaktiviert.
