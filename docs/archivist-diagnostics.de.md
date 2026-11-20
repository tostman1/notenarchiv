# Diagnosemeldungen ansehen

Im Diagnosemodus steht nach der Anmeldung **Debug / Logs** in der Navigation.
Die Kennzeichnung oben zeigt den aktiven Modus. Im Deploy-Modus sind die
Ansicht und ihre Downloads gesperrt, auch wenn frühere Logdateien vorhanden sind.
Der Modus kann nicht in dieser Ansicht umgeschaltet werden.

1. Wählen Sie den Dienst **web** oder **worker**.
2. Grenzen Sie die Meldungen bei Bedarf nach Stufe, Komponente, Auftrags-ID
   oder Zeitraum ein und wählen Sie **Filtern**. Die Zeitfelder verwenden
   die konfigurierte Ortszeit; die Tabelle zeigt UTC.
3. Standardmäßig beginnt die Ansicht mit einem begrenzten aktuellen Ausschnitt.
   Für ältere Meldungen aktivieren Sie **Ab ältester gespeicherter Meldung
   lesen**. Über **Weitere Meldungen laden** gehen Sie schrittweise weiter.
4. **Live-Aktualisierung starten** lädt neue Meldungen alle zwei Sekunden nach.
   Die Tabelle behält höchstens 200 Meldungen. Mit **Live-Aktualisierung stoppen**
   halten Sie das Nachladen an.
5. Der Download enthält einen bereinigten Ausschnitt ab der angezeigten
   Leseposition: höchstens 1000 Meldungen und höchstens 1 MiB eingelesene Daten.
   Ein Download ist deshalb kein vollständiges Backup aller Logdateien.

Die Ansicht zeigt technische Ereignisse und interne Kennungen. Freitext,
Noteninhalte, OCR-Texte, Dateipfade, Passwörter und Exception-Texte werden
nicht übernommen. Fehlerhafte Einträge werden übersprungen. Das Lesen
verändert oder löscht keine Logdateien.

Bei einer abgelaufenen Leseposition laden Sie die Seite neu. Sind alte
Meldungen durch Rotation nicht mehr vorhanden, weist die Ansicht auf den
Neustart am aktuellen Ausschnitt hin. Regulärer Fortschritt und fachliche
Prüfungen gehören weiterhin in die jeweiligen Anwendungsbereiche.
