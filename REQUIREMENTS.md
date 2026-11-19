# Notenarchiv & Marschbuch-Generator

**Funktionales Konzept – Version 1.1**  
**Stand:** 19.11.2026  
**Status:** Funktionale Anforderungen weitgehend definiert; technische Architektur separat dokumentiert.

## 1. Zielsetzung

Eine zentrale Anwendung zur Verwaltung digitalisierter Vereinsnoten und zur Erstellung von Marschbüchern, Konzertmappen und individuellen Notensammlungen.

Digitalisierte Noten werden einmalig archiviert und anschließend für beliebig viele Projekte verwendet. Die Anwendung soll den Arbeitsaufwand der Notenarchivare reduzieren, Fehlzuordnungen vermeiden und die Erstellung sowie den Druck vollständiger Notenmappen vereinfachen.

Die Anwendung umfasst die Scanaufbereitung, das zentrale Notenarchiv, die projektbasierte Notensammlungsverwaltung und die Ausgabe von Marschbüchern und regulären Notenmappen. Sie wird als eigenständige Webanwendung für die Anforderungen des Musikvereins entwickelt.

Als spätere Laufzeitumgebung ist ein Container auf einer Synology DiskStation vorgesehen. Die technische Architektur ist im separaten Dokument `ARCHITECTURE.md` beschrieben.

## 2. Scanaufbereitung und Marschbuch-Erstellung

### Eingabe und Formate

- Digitalisierte Stücke aus dem NAS-Quellarchiv; pro Stück können mehrere Stimmen-PDFs vorhanden sein.
- Optionaler Import nummerierter Stimmenordner, beispielsweise `Altsax-1/01_Radetzkymarsch.pdf`; Nummern werden als Vorschläge für die Projektstückliste interpretiert und bestätigt.
- Schwarz-Weiß-Scans sowie digital erzeugte PDFs, insbesondere A4, A3 und Marschbuch-Sonderformat 170 × 120 mm quer.

### Anforderungen an die Scanaufbereitung

- Anzeige der PDF-Seiten und Vorschaubilder; Original und Verarbeitungsergebnis vergleichbar darstellen.
- Automatische Korrektur leichter Schieflagen anhand der Notenlinien (Deskew), Reduzierung von Scanrauschen und Randschatten, Zuschnitt und Formatnormalisierung, soweit nötig.
- Notenlinien, Vorzeichen, Dynamik- und sonstige musikalische Zeichen dürfen nicht durch Filter beschädigt oder abgeschnitten werden.
- Aufbereitung als separat abrufbare Funktion, mit anpassbaren Parametern und Vorschau; keine Veränderung von Originaldateien oder unveränderten Archivkopien.
- Marschbuch-Druckausgaben auf das projektbezogen definierte Sonderformat (Standard 170 × 120 mm quer) normieren; Seitenverhältnis und Lesbarkeit erhalten.
- Stücke gemäß gemeinsamer Projektstückliste und Nummerierung zusammenführen, Inhaltsverzeichnis erzeugen und maßstabsgetreue Druckausgabe ermöglichen.
- Hintergrundverarbeitung mit sichtbarem Fortschritt, Abbruchmöglichkeit und nachvollziehbaren Fehlern.

## 3. Zentrales Notenarchiv

- Ein Ordner pro Musikstück mit den vorhandenen Stimmen-PDFs.
- Unterstützung uneinheitlicher Datei- und Stimmenbezeichnungen, einschließlich generischer Scannernamen.
- Schnellsuche über Titel und Teilzeichenfolgen, auch innerhalb von Wörtern.
- Filter nach Instrument, Stimme und Archivvollständigkeit.
- Unterstützung verschiedener Arrangements desselben Stücks; der Arrangeur dient als Unterscheidungsmerkmal.
- Automatische Erkennung von Stücktiteln und Instrumentenstimmen anhand Dateiname, PDF-Text und OCR mit Erkennungsregeln für unterschiedliche Schreibweisen; Indizierung und OCR sind separat startbare Archivfunktionen.
- Bei jeder Erstindizierung und jeder geänderten PDF-Datei wird der tatsächliche PDF-Inhalt kontrolliert, auch bei bereits eindeutig benannten Dateien wie `Posaune1.pdf` oder `Trombone II-III.pdf`. Der Dateiname ist ein starkes Indiz, aber kein Beweis.
- Stimmen Dateiname und PDF-Inhalt überein, wird die Zuordnung als plausibler Vorschlag angezeigt. Widersprüche und nicht eindeutig lesbare Beschriftungen werden besonders hervorgehoben. Alle neuen Zuordnungen benötigen eine manuelle Freigabe; keine automatische Freigabe aufgrund des Dateinamens.
- Ein PDF kann unverändert mehreren Stimmen zugeordnet werden, beispielsweise `Trombone II/III`.
- Unsichere oder unbekannte Erkennungen erhalten einen Prüfhinweis und müssen manuell überprüft bzw. zugeordnet werden.
- Vollständigkeitsmatrix für fehlende und ungeprüfte Noten.
- Originalscans bleiben unverändert.

### Getrenntes Original- und Zielarchiv (RAW / CLEAN)

**Verbindliche Grundregel:** Das RAW-Archiv ist eine ausschließlich lesbare Quelle für die Anwendung. Das CLEAN-Archiv ist eine eigenständige, vollständig strukturierte Dateisammlung mit echten PDF-Kopien, nicht nur ein Index oder eine Verknüpfung. Beide Wurzelordner sind getrennt; Projektgenerierung verwendet ausschließlich freigegebene CLEAN-Dateien.

- CLEAN besitzt Unterordner pro Stück und Arrangement sowie standardisierte PDF-Namen mit Instrument, Stimmung/Notation und Stimme. Die Zuordnung zur Originaldatei bleibt nachvollziehbar. Auch bei bereits korrekt benannten Originaldateien wird eine separate Kopie angelegt.
- Die Anwendung erhält keine Schreibrechte auf RAW; keine Umbenennung, Löschung, Verschiebung, Überschreibung oder Scanaufbereitung an der Quelle. Statusmarker werden standardmäßig außerhalb von RAW gespiegelt. Eine physische Markierung in RAW ist nur als getrennte, nachweislich abgesicherte Ausnahme zulässig; niemals den RAW-Mount beschreibbar machen.

- Originalordner und Original-PDFs werden nicht umbenannt, überschrieben oder gelöscht.
- Die Anwendung kopiert die PDF-Dateien in ein separates, strukturiertes Zielarchiv und benennt ausschließlich die Zielkopien nach einem einheitlichen Stück-/Instrumenten-/Stimmenschema.
- Nicht eindeutig zuordenbare PDFs werden zur manuellen Prüfung separat gekennzeichnet; mehrere Stimmen können auf dieselbe Ziel-PDF verweisen.
- Nach der Indizierung wird der Originalordner sichtbar als indiziert markiert. Die konkrete technische Umsetzung (separater Statusmarker oder geschützter Marker im Originalordner) muss den Schreibschutz der Original-PDFs gewährleisten.
- Indizierung und fachliche Prüfung sind getrennte Status. Archivare erhalten einen auffälligen Hinweis, dass erkannte Stimmen kontrolliert und bestätigt werden müssen.
- Die Anwendung zeigt erkannte Zuordnungen und Originalnamen neben einer PDF-Vorschau. Korrekturen erfolgen ausschließlich im Zielarchiv.
- Bestätigte Zuordnungen werden für die Projekterstellung verwendet. Neue oder geänderte Dateien werden erneut zur Prüfung vorgelegt; unveränderte, bereits bestätigte Zuordnungen bleiben bei identischem Dateiinhalt (Hash) erhalten.
- Die Vollständigkeit eines Stücks ist unabhängig davon, ob seine vorhandenen Dateien bereits geprüft wurden.

### Beispiel des Quellarchivs

```text
Notenarchiv/
├── Böhmischer Traum/
│   ├── Klarinette 1.pdf
│   ├── Posaune 2.pdf
│   └── scan001.pdf
├── ABBA Medley/
│   ├── Flöte 1.pdf
│   └── Trombone II-III.pdf
└── Italo Pop Classics/
    └── ...
```

### Beispiel des CLEAN-Archivs

```text
Notenarchiv_Sortiert/
├── Böhmischer Traum [Arrangement-ID]/
│   ├── Klarinette_B_01.pdf
│   ├── Posaune_02.pdf
│   └── _Ungeprueft/
│       └── scan001.pdf
└── ABBA Medley [Arrangement-ID]/
    ├── Floete_01.pdf
    └── Posaune_02-03.pdf
```

Die Dateinamen dienen lediglich als illustrative Beispiele. Die tatsächliche Archivstruktur enthält uneinheitlich benannte PDFs, die nicht zwingend eine eindeutige Zuordnung erlauben.

## 4. Vereinsverwaltung

Zentrale Verwaltung von:

- Vereinsmitgliedern und ihrer regulären Instrumenten-/Stimmenzuordnung.
- Instrumenten und zugehörigen Stimmen.
- Instrumentenstimmungen und speziellen Notationsarten (z. B. Es-Klarinette, B-Klarinette oder Posaune im Bassschlüssel).
- Ersatzstimmenregeln.

Instrumente und Stimmen werden aus zentral definierten Auswahlfeldern ausgewählt. Freie, uneinheitliche Bezeichnungen in den Projekteinstellungen werden vermieden.

Jedes Mitglied hat vorerst genau eine reguläre Instrumenten-/Stimmenzuordnung. Projektspezifische und stückbezogene Abweichungen sind möglich. Aushilfen können für einzelne Projekte aufgenommen werden, ohne den regulären Vereinsbestand dauerhaft verändern zu müssen.

## 5. Projektverwaltung

Projekte können erstellt, gespeichert, geladen, verändert, dupliziert und archiviert werden.

Beispiele:

- Marschbuch 2026
- Weihnachtsensemble 2026
- Unterhaltungsmappe
- Konzertmappe

**Jedes Projekt besitzt genau eine gemeinsame Notensammlung mit identischer Stückliste, Reihenfolge und Nummerierung für alle Ausgaben.** Personalisierung betrifft ausschließlich die Instrumenten-/Stimmenzuordnung sowie das optionale Deckblatt.

Ein Projekt speichert:

- Projektname
- Gemeinsame Stückliste und Reihenfolge
- Nummerierung einschließlich reservierter Leerpositionen
- Teilnehmende Musiker (eine frei wählbare Teilmenge des Vereins)
- Projektbezogene Instrumenten- und Stimmenzuweisungen
- Individuelle Änderungen pro Person und Stück
- Ersatzstimmenregeln und Ausnahmen
- Ausgabeformat und Druckeinstellungen

Die Projekteinstellungen bleiben nach der PDF-Generierung erhalten. Eine Änderung, beispielsweise von Marinas Stimme, erfordert keine erneute Einrichtung des Projekts. Projekte können später geöffnet und gezielt neu generiert werden.

## 6. Zusammenstellung der Notensammlung

- Musikstücke über Suche und Filter auswählen; die Trefferliste aktualisiert sich unmittelbar während der Eingabe.
- Reihenfolge per Drag-and-drop festlegen.
- Stücknummern projektweit verwalten.
- Einzelne Positionen im Inhaltsverzeichnis freilassen.
- Ein Musikstück darf mehrfach vorkommen.
- Alle Teilnehmer und Stimmen erhalten dieselbe projektweite Stückliste. Individuelle Stückauswahl, Auslassungen oder Zusatzstücke sind nicht vorgesehen.
- Stimmen bzw. Teilnehmer einzeln auswählen oder über „Alle auswählen“ / „Alle abwählen“ verwalten.

**Die gemeinsame Projektnummerierung bleibt in allen persönlichen Ausgaben erhalten.**

Beispiel: Ist die Projektnummer 5 reserviert, folgt in jeder Ausgabe nach Stück Nr. 4 das Stück Nr. 6. Die Nummerierung bleibt für alle Teilnehmer gleich. Fehlt eine Stimme, bleibt die Stückposition erhalten und wird nach Bestätigung durch ein Platzhalterblatt repräsentiert.

Freie Nummern werden im Inhaltsverzeichnis berücksichtigt, erzeugen jedoch keine leeren Notenseiten.

## 7. Instrumenten- und Stimmenzuordnung

Die reguläre Instrumentenstimme eines Mitglieds kann projektbezogen und für einzelne Musikstücke geändert werden. Die reguläre Vereinsstimme bleibt unverändert.

Priorität der Zuordnung:

1. Individuelle Einstellung für einen Musiker bei einem bestimmten Stück.
2. Projektbezogene Stimmenzuweisung.
3. Reguläre Vereinsstimme.

### Schnelle manuelle Stimmenwechsel (verbindliche Bedienanforderung)

In der Projekt-Hauptansicht steht eine direkt bearbeitbare Stimmenmatrix zur Verfügung: Zeilen sind Projektpositionen, Spalten sind ausgewählte Musiker. Die Matrix zeigt die effektiv verwendete Stimme und die Herkunft der Zuordnung (Vereinsstandard, Projektstandard, persönliche Stückausnahme oder Ersatzregel). Filter nach Instrument/Person und eine fixierte Stückspalte erleichtern die Bedienung großer Projekte.

- Projektstandard je Teilnehmer direkt im Spaltenkopf oder in der Teilnehmerliste ändern.
- Einzelne Stimme direkt in der Zelle über ein Dropdown ändern, ohne Dialogkette oder Wechsel in die Vereinsverwaltung. Nur passende, tatsächlich verfügbare und bestätigte Notenfassungen werden angeboten; nicht verfügbare Zuordnungen müssen klar als solche erkennbar sein.
- Mehrere ausgewählte Zellen eines Teilnehmers in einem Schritt auf dieselbe Stimme setzen; vorhandene Ausnahmen gezielt auf den Projektstandard zurücksetzen. Massenänderungen dürfen andere Teilnehmer nicht unbeabsichtigt verändern.
- Abweichungen vom Standard sichtbar kennzeichnen; Änderungen speichern und beim erneuten Öffnen des Projekts wiederherstellen. Änderungen am Projektstandard überschreiben keine expliziten Stückausnahmen ohne ausdrückliche Bestätigung.
- Die tatsächliche PDF-Stimme bei Verwendung einer Ersatzregel und fehlende Noten deutlich anzeigen. Manuelle Auswahl einer vorhandenen Stimme darf auch dann erfolgen, wenn die Standardstimme vorhanden ist.
- Ein einzelnes geändertes Mitglied kann gezielt neu exportiert werden; weder Archivzuordnung noch gemeinsame Stückliste, Nummerierung oder reguläre Vereinsstimme ändern sich.

Beispiel: Mathias spielt alle Stücke Posaune 1, Sebi Posaune 2, Riccardo im Projekt standardmäßig Posaune 3. Für einzelne Stücke wählt der Archivar bei Riccardo Posaune 2. Alle übrigen Zuordnungen bleiben erhalten. Es handelt sich um gleichwertige musikalische Entscheidungen, nicht ausschließlich um Ersatz bei fehlenden Noten.

Fehlt die benötigte PDF-Datei, wird eine passende definierte Ersatzstimme gesucht. Auch die Ersatzregel kann stückbezogen angepasst werden.

Beispiel: Wenn die Posaune 3 nicht verfügbar ist, kann die Posaune 2 als Ersatz definiert werden.

Bei vollständig fehlendem passenden Notenmaterial:

- Deutlich sichtbare Warnung.
- Explizite Bestätigung vor der Generierung.
- Platzhalterblatt mit Stücktitel und „Noten fehlen“.

## 8. Besondere Unterstützung kleiner Ensembles

Musikalische Ensemble-Stimmen und instrumentenspezifische Notenstimmen werden unterschieden.

Beispiel Weihnachtsensemble: Es existieren vier musikalische Stimmen, die von sieben Musikern auf unterschiedlichen Instrumenten gespielt werden. Mehrere Instrumente können dieselbe musikalische Stimme übernehmen, benötigen dafür aber gegebenenfalls unterschiedlich transponierte oder notierte PDFs.

| Musikalische Stimme | Instrument | Verwendete Noten |
| --- | --- | --- |
| Stimme 1 | Flöte | Flöte 1 |
| Stimme 2 | Klarinette in B | Passende Klarinettenstimme |
| Stimme 3 | Posaune | Posaune 3 |
| Stimme 3 | Tenorhorn in B | Passende Tenorhornstimme |
| Stimme 4 | Tuba | Passende Tubastimme |

Gerade beim Weihnachtsensemble entspricht die dritte musikalische Stimme für Posaune häufig direkt der spielbaren Posaunenstimme 3. Die Zuordnung darf jedoch nicht ausschließlich aus gleichen Stimmnummern abgeleitet werden. Entscheidend ist, welche Notenfassung tatsächlich zur musikalischen Stimme und zum Instrument passt.

Projektspezifische Standardzuordnungen und Ausnahmen für einzelne Musikstücke sind vorgesehen. Die genaue Bedienung dieser Zuordnungen ist noch auszuarbeiten.

## 9. Inhaltsverzeichnis und PDF-Erstellung

- Automatisch gestaltetes Inhaltsverzeichnis mit Stücknummern und Titeln.
- Keine Seitenzahlen im Inhaltsverzeichnis.
- Reservierte Nummern bleiben frei.
- Ohne Deckblatt steht das Inhaltsverzeichnis am Anfang des PDFs.
- Bei personalisierter Ausgabe kann ein Deckblatt mit Name und Stimme vorangestellt werden.
- Ausgabe pro Instrumentenstimme oder pro Person.
- Identische Stückliste in allen Ausgaben; Unterschiede ausschließlich bei Instrumentenstimmen und optionalem Deckblatt.
- Gezielt einzelne oder sämtliche PDFs neu generieren.
- Unterstützung für A4, A3 und das Marschbuch-Sonderformat 170 × 120 mm; Ausgabeformat projektbezogen anpassbar.

Zwei getrennte Ausgabearten stehen zur Verfügung: Lese-PDF (mit Original-Seitenformaten) und Druck-PDF (mit projektspezifischer A3/A4-/Marschbuch-Anordnung). A3-Originalseiten bleiben im Lese-PDF als ganze A3-Seiten erhalten und werden nicht geteilt. Das Deckblatt ist pro Projekt optional.

## 10. Intelligente Druckausgabe

Der Archivar wählt innerhalb der Anwendung einen verfügbaren Netzwerkdrucker.

Für reguläre A4-Noten gilt:

| Anzahl Notenseiten eines Stücks | Druckanordnung |
| --- | --- |
| 1 | 1 × A4 |
| 2 | 1 × A3 quer, zwei A4-Seiten nebeneinander |
| 3 | 1 × A3 quer + 1 × A4 |
| 4 | 2 × A3 quer |
| 5 | 2 × A3 quer + 1 × A4 |
| 6 | 3 × A3 quer |

Die Seiten werden stückweise in normaler Lesereihenfolge angeordnet: links zuerst, rechts danach. Bei ungerader Seitenzahl wird die letzte Seite auf A4 gedruckt. Es ist keine spezielle Broschüren- oder Heftseitenanordnung vorgesehen.

Die automatische Umschaltung zwischen A4 und A3 wird abhängig von den Fähigkeiten des ausgewählten Druckers umgesetzt. Eine Druckvorschau soll vor dem Druck möglich sein.

Bereits als A3 vorliegende Noten werden nicht in A4-Seiten zerlegt. Die Paarung von A4-Seiten darf keine Stückgrenze überschreiten. Unterstützt der gewählte Drucker A3 nicht, wird nach Bestätigung eine geeignete A4-Ausgabe angeboten; die Originalseiten im Lese-PDF bleiben unverändert. Für Marschbücher gelten die projektspezifischen Sonderformate, insbesondere der maßstabsgetreue Ausdruck im Format 170 × 120 mm.

## 11. Qualitäts- und Vollständigkeitsprüfung

Vor der Generierung erscheint ein Prüfbericht mit:

- Anzahl der Stücke und Teilnehmer.
- Anzahl der zu erzeugenden Dokumente.
- Fehlenden Instrumentenstimmen.
- Verwendeten Ersatzstimmen.
- Ungeprüften PDF-Zuordnungen.
- Individuellen Abweichungen.
- Gegebenenfalls fehlendem Notenmaterial.

Relevante Fehler müssen vor dem Fortfahren explizit bestätigt werden. Die Anwendung soll Fehlzuordnungen nicht stillschweigend übernehmen.

Eine zusätzliche archivweite Vollständigkeitsmatrix ermöglicht eine gezielte Nachdigitalisierung fehlender Stimmen.

## 12. Typischer Workflow

1. Noten digitalisieren und im NAS-Archiv ablegen.
2. Originalarchiv einlesen, PDF-Kopien im sortierten Zielarchiv ablegen, Originalordner als indiziert markieren und die erkannten Stimmen in der Prüfwarteschlange kontrollieren und bestätigen.
3. Ein neues Projekt erstellen oder ein gespeichertes Projekt öffnen bzw. duplizieren.
4. Stücke suchen, auswählen, sortieren und nummerieren.
5. Projektteilnehmer bzw. gewünschte Stimmen auswählen.
6. Standardzuweisungen übernehmen und individuelle Stimmenwechsel direkt in der Stimmenmatrix (einzeln oder gesammelt) festlegen.
7. Prüfbericht kontrollieren und fehlende Noten bzw. Ersatzstimmen bestätigen oder korrigieren.
8. Stimmbezogene oder personalisierte PDFs mit Inhaltsverzeichnis und gegebenenfalls Deckblatt generieren.
9. PDFs exportieren oder über den ausgewählten Netzwerkdrucker ausgeben.
10. Projekt speichern und später bei Bedarf ändern oder erneut generieren.

## 13. Betriebsmodi und Diagnose

- Standardbetrieb (Deploy), wenn `DEBUG_MODE` nicht gesetzt oder auf `"FALSE"` gesetzt ist. Die reguläre Oberfläche zeigt weiterhin verständliche Job-Fortschritte, Warnungen und Fehler; normale Container-Logs bleiben verfügbar.
- Optionaler Debug-Modus durch `DEBUG_MODE: "TRUE"` in der Compose-Umgebung. Derselbe Container-Build wird für beide Modi eingesetzt; Änderungen erfordern eine Neuerstellung der betroffenen Container, keinen Image-Neubau.
- Im Debug-Modus erscheint eine zusätzliche, ausführliche Diagnoseansicht im GUI mit Live-Logs, Verarbeitungsschritten, Laufzeiten, OCR-Erkennungskandidaten und Fehlerdetails. Filter nach Job, Komponente, Schweregrad und Zeitraum sowie ein manueller Log-Download sind vorgesehen.
- Web- und Hintergrundworker schreiben bei aktivem Debug-Modus zusätzlich persistente, rotierende Debug-Logdateien in das Anwendungsdatenverzeichnis auf der DiskStation. Die Logs bleiben nach Container-Neuerstellung erhalten. Alte Dateien werden begrenzt aufbewahrt.
- Debug-Modus darf weder Zugriffsrechte noch sonstige Sicherheitsmaßnahmen ändern. Keine Secrets, vollständigen OCR-Rohtexte, PDF-Inhalte oder unnötigen Mitgliederdaten in allgemeinen Logs. Diagnoseansicht und Log-Download nur für angemeldete Archivare.
- Debug-Modus und fachlicher Prüfstatus sind unabhängig: Eine automatische Erkennung muss auch ohne Debug-Modus überprüfbar und manuell bestätigbar bleiben.

## 14. Benutzerkreis und Abgrenzung

Die Anwendung wird ausschließlich durch Notenarchivare bedient.

Nicht Teil des derzeit vorgesehenen Funktionsumfangs sind:

- Unterschiedliche Benutzerrollen und ein separates Musikerportal.
- Musiker-Self-Service.
- Mehrere eigenständige Notensammlungen innerhalb eines Projekts.
- Individuelle Stücklisten und Zusatzstücke pro Teilnehmer.
- Mehrere reguläre Instrumenten-/Stimmenzuordnungen pro Vereinsmitglied.
- Broschüren- oder Heftseitenanordnung beim A3-Druck.

## 15. Noch offene Detailentscheidungen

- Genaue Regeln für die Übernahme von Ensemble-Stimmenzuordnungen in einzelne Musikstücke.
- Gestaltung von Deckblättern und Inhaltsverzeichnissen.
- Verhalten bei nicht unterstützten A3-Druckfunktionen.
- Konkrete Exportablage und gegebenenfalls Aufbewahrung erzeugter PDFs.
- Erkennung nachträglich ausgetauschter Archivscans, sofern ohne zusätzliche Bedienkomplexität umsetzbar.
- Weitere Details der Benutzeroberfläche über die bereits verbindlich definierte Stimmenmatrix hinaus.
- Technische Architektur und Implementierung für den Containerbetrieb auf der Synology DiskStation.

Dieses Dokument definiert die funktionalen Anforderungen. Die technische Zielarchitektur, Bibliotheken, Implementierungsphasen und Deployment-Vorgaben sind in `ARCHITECTURE.md` dokumentiert.
