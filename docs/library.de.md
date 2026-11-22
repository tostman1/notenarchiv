# Notenbibliothek und Vollständigkeit

**Notenbibliothek** zeigt aktive Werke mit ihren getrennten Arrangements/Ausgaben.
Die Live-Suche findet Titel und Aliasse ohne Beachtung der Großschreibung auch
mitten im Wort: `ab` findet z. B. ABBA, Abel Tasman und Fuchsgraben. Unicode-
Schreibweisen werden normalisiert. Ohne JavaScript bleibt **Suchen** verfügbar.

Mit Arrangement, Instrumentenvariante, Stimme, Archivmaterial und Vollständigkeit
filtern. Eine Stimme muss zur gewählten Instrumentenvariante passen. Gleichnamige
Werke/Ausgaben werden nicht zusammengelegt.

Auf der Arrangementseite werden **Erwartung** und **Material** getrennt gezeigt:

- **Erwartung unbekannt:** Es ist keine verbindliche Besetzung festgelegt.
  Auch vorhandene bestätigte Noten machen das Werk dann nicht „vollständig“.
- **Erforderlich:** Diese Stimme gehört zur festgelegten Besetzung.
- **Nicht erforderlich / optional:** Fehlendes Material blockiert die definierte
  Besetzung nicht; die Materialanzeige bleibt trotzdem separat sichtbar.
- **Bestätigt verfügbar laut Archivstatus:** Eine kontrollierte Freigabe mit
  Publikationsbeleg liegt vor. Weitere ungeprüfte Vorschläge werden zusätzlich
  angezeigt und ersetzen die bestätigte Version nicht.
- **Ungeprüft:** Nur ein Entwurf oder Erkennungsvorschlag liegt vor, keine nutzbare
  Stimme. Die Prüfwarteschlange führt zur erforderlichen visuellen Prüfung.
- **Fehlend:** Kein bestätigtes verfügbares Material für diese Stimme vorhanden.

**Erwartete Stimmen bearbeiten** und **Arrangement und Erwartungen bearbeiten**
verwenden die vorhandenen Stammdaten. Eine Besetzungsvorlage wird als unabhängige
Erwartungsliste kopiert; spätere Vorlagenänderungen wirken nicht automatisch nach.

Die Liste „Bestätigte Archivversionen“ enthält nur freigegebene Versionen. Ihre
konkreten Dateihashes werden beim Aufruf dieser Seite geprüft. Fehlende oder
beschädigte Kopien werden ausdrücklich **nicht nutzbar** gezeigt und erhalten
keinen Vorschau-Link. Unter **Ausgaben und Bevorzugung** kann je spielbarer Stimme
eine passende bestätigte Ausgabe ausdrücklich bevorzugt oder die Vorgabe
zurückgesetzt werden; siehe [ausgaben.de.md](ausgaben.de.md). Keine explizite
Auswahl wird still ersetzt. Direkter PDF-/ZIP-Download ohne Projekt ist verfügbar;
siehe [download.de.md](download.de.md). Projektregeln folgen separat.

Der Archiv-Vollständigkeitsstatus beruht auf gespeicherten Belegen, nicht auf
einem vollständigen Integritätsscan. Projekt-Preflight, NAS-Integrität/Last und
Backup vor echten Noten bleiben eigenständige Prüfungen. Diese Bildschirme ändern
RAW/CLEAN/PROCESSED nicht.
