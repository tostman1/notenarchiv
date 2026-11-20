# Aufträge beobachten und abbrechen

Öffnen Sie **Aufträge** in der Hauptnavigation. Die Liste zeigt Status und
Fortschritt. Filtern Sie nach Status oder Auftragsart und wählen Sie einen
Auftrag aus. Mit **Aktualisieren** laden Sie den aktuellen Stand.

**Abbrechen** beendet einen wartenden Auftrag sofort. Bei laufender Verarbeitung
erscheint zunächst **Abbruch angefordert**. Erst nach dem Ende der Verarbeitung
und ihrer Teilprozesse wird **Abgebrochen** angezeigt. Bereits abgeschlossene
Änderungen bleiben erhalten. Ein Dienst, der nicht reagiert, wird nicht
fälschlich als erfolgreich abgebrochen dargestellt.

Bei **Prüfung erforderlich** erfolgen keine blinden Wiederholungen. Besonders
bei unklarer Druckannahme muss der Drucker tatsächlich kontrolliert werden;
die Anwendung sendet den Druckauftrag nicht automatisch erneut.

Ist der Hintergrunddienst nicht verfügbar, bleiben wartende Aufträge gespeichert.
Der Status ist unabhängig vom Diagnosemodus sichtbar. Archivimport, OCR oder
Ausgabe erzeugen erst Aufträge, wenn ihre jeweiligen Fachfunktionen verfügbar
sind. Die veröffentlichte Vorschau 0.1.0-preview.1 startet weiterhin keinen Worker;
dieses Handbuch beschreibt den neu implementierten Quellstand.
