# Zuordnungsmatrix ansehen

Im Projekt **Zuordnungsmatrix öffnen** wählen. Zeilen sind die gemeinsame
Stückliste einschließlich Reserven; Spalten sind ausgewählte Teilnehmende. Jeder
Spaltenkopf zeigt den gespeicherten Projektdefault und gegebenenfalls die
musikalische Rolle, nicht eine automatisch aktualisierte Mitgliedsstimme.

Die Zelle zeigt gewünschte und tatsächliche spielbare Stimme samt Stimmung und
Schlüssel. **Stimmenherkunft** erklärt Default, persönliche Ausnahme oder Rollen-
Mapping; **Ausgabenherkunft** erklärt die konkrete Version, Projekt-/Positions-
präferenz, Archivvorgabe oder einzige passende Ausgabe. Ein bewusster Ersatz wird
deutlich angezeigt und verändert nicht die gewünschte Stammzuordnung.

Fehlende Noten, mehrere mögliche Versionen, ungültige feste Auswahl und beschädigte
Kopien werden getrennt ausgewiesen. Keine unbestätigte oder inkompatible Version
wird still eingesetzt. Nur nutzbare bestätigte Ausgaben erhalten Vorschau/Download.
Reserven bleiben ohne musikalische Zuordnung oder Bearbeitungsfelder.

Die Anzeige ist zunächst auf 25 Positionen und 10 Personen pro Seite begrenzt;
mit **Weitere Positionen/Personen** bleiben alle anderen gespeicherten Zeilen und
Spalten erreichbar. Stücknummern gelten projektweit und werden nicht auf Noten
gedruckt. Diese Ansicht ersetzt keine spätere Vollständigkeits-Vorprüfung und keine
ausdrückliche Bestätigung fehlender Noten.

## Einzelne Zuordnung ändern

In der Zelle **Spielbare Stimme und konkrete Ausgabe** wählen und **Persönliche
Ausgabe speichern**. Die Auswahl benennt Stimmung, Schlüssel und konkrete
bestätigte Version gemeinsam. Eine persönliche Wahl gewinnt auch dann, wenn eine
andere Stammstimme verfügbar wäre. Bei fremder Änderung/abgelaufener Auswahl neu
laden; keine stille Ersatzversion und kein automatischer Wiederholungsversuch.

Im Spaltenkopf **Gespeicherte Projektstimme** ändern und **Projektdefault speichern**.
Dies ändert nur diesen Projektdefault, keine Mitgliedsstammdaten oder persönlichen
Stück-Overrides. Die sichtbare Matrix und Revision werden nach erfolgreicher
Änderung aktualisiert; Reload zeigt dieselbe gespeicherte Auswahl. Ohne JavaScript
funktionieren die Formulare weiterhin mit regulärer Speicherung/Weiterleitung.

## Mehrere Zellen gemeinsam ändern oder zurücksetzen

Bei einer Person die gewünschten Zellen mit **Für Mehrfachaktion auswählen**
markieren (höchstens 25). Im Spaltenkopf **Mehrfachziel: Stimme und Notation** wählen.
Für jede markierte Position unter **Konkrete Ausgabe für Mehrfachänderung** bewusst
die passende bestätigte Version wählen, dann **Ausgewählte Zellen speichern**.
Die gemeinsame Aktion speichert entweder alle gewählten Zellen oder keine. Fehlende,
geänderte oder unpassende Ausgaben müssen zuerst korrigiert werden; unmarkierte
Zellen und andere Personen bleiben unverändert. Auswahl wird nach Fehlern nicht
automatisch wiederholt. Nach Reload bleiben gespeicherte Änderungen erhalten.

**Diesen Override zurücksetzen** betrifft nur diese eine Zelle. Alternativ Zellen
markieren und **Ausgewählte Overrides zurücksetzen**. Damit endet nur die persönliche
Stück-Ausnahme; Projektdefault und gegebenenfalls Rollenregeln gelten wieder.
Fehlende oder mehrdeutige Ausgaben werden sichtbar, nicht still ersetzt. Die
Historie bleibt erhalten. Defaultänderungen behalten die übrigen persönlichen
Overrides; Stückliste und gemeinsame Nummern werden durch keine Aktion geändert.
