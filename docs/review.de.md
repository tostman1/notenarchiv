# Einzelprüfung und Freigabe

1. **Prüfwarteschlange** öffnen und **Version prüfen und zuordnen** wählen.
2. Die tatsächliche PDF Seite für Seite betrachten. Dateiname und erkannter
   Text stehen daneben als Hinweise, nicht als Freigabe. Erkennungskonflikte
   immer manuell klären; bei Scans ersetzt ein guter Dateiname keine Prüfung.
3. Arrangement/Ausgabe, Instrumentenvarianten mit Stimmung/Notation und sämtliche
   enthaltenen Stimmen kontrolliert auswählen. Mehrfachauswahl ist möglich;
   kombinierte Stimmen bleiben eine ungeteilte PDF. **Zuordnung speichern**.
4. Alle Seiten und die jetzt gespeicherte Zuordnung visuell kontrollieren.
   Die persönliche Erklärung aktivieren und **Visuelle Prüfung speichern**.
   Ein Neuladen, Vorschauöffnung oder die Prüfung eines anderen Kontos ersetzt
   diesen Schritt nicht. Jede Korrektur erzeugt einen neuen Prüfstand.
5. Die getrennte Freigabeerklärung aktivieren und **Freigabe beauftragen**.
   Die Auftragsseite zeigt Fortschritt/Fehler. Nutzbar wird diese Version erst
   nach der sicheren, verifizierten kanonischen Publikation durch den Worker.
6. Ein falscher gespeicherter Vorschlag kann verworfen werden. PDF und Historie
   bleiben erhalten. Anschließend eine neue Zuordnung speichern und erneut prüfen.

Bei veraltetem Prüfstand oder geändertem Dateihash: Seite neu laden, Zuordnung
kontrollieren und erneut prüfen. Fehlgeschlagene oder ungeklärte Publikation
erteilt keine Freigabe. Alte bereits bestätigte Ausgaben werden durch neue
Kandidaten oder fehlende RAW-Dateien nicht gelöscht oder stillschweigend ersetzt.

RAW bleibt unverändert; nur eigene CLEAN-Kopien erhalten kanonische Namen. Die
Prüfgeschichte hält Konto, Zeit, Version und Zuordnungsereignisse fest. Export
ist hier keine automatisch verfügbare Funktion.

## Lokale OCR ausdrücklich starten

**Alle Seiten lokal mit OCR analysieren** startet einen Hintergrundauftrag für
die unveränderte, verifizierte CLEAN-Quellkopie. Auf der Auftragsseite sind
Fortschritt und Abbruch verfügbar. OCR berücksichtigt alle Quellseiten auch bei
vorhandenem PDF-Text; Dateiname und erkannte Texte bleiben lediglich Vorschläge.
Anschließend zeigt die Prüfseite lokale OCR-Evidenz mit Quellseite und Kontext.
Eine erneute Analyse verwendet passende bereits gespeicherte Seitenevidenz.

OCR verändert weder gespeicherte Zuordnungen noch eine vorhandene Freigabe und
ersetzt niemals Ihre visuelle Prüfung. Falsche Vorschläge wie gewohnt manuell
korrigieren. Die lokale OCR-Laufzeit ist zunächst im Server-Container enthalten;
eine native Windows-Verteilung und der vollständige Segmentierungseditor sind noch
nicht geliefert. Ein ungeklärter Prozessabbruch erfordert Prüfung statt eines
automatischen erneuten Versuchs.

### Quellseite und rechteckigen Bereich analysieren

Die ausgewählte OCR-Seite und die Bereichsgrenzen beziehen sich auf die
angezeigte Originalseite, nicht auf eine musikalisch bestätigte Region.
Grenzen werden als Prozentwerte von links/oben eingegeben: links und oben
`0`, rechts und unten `100` bedeuten die ganze ausgewählte Seite. Links muss
kleiner als rechts und oben kleiner als unten sein. Die Seitennummer beginnt
bei `1`. Gedrehte Seiten und abweichende Seitenformate werden anhand ihrer
Originalgeometrie berücksichtigt.

Die Analyse eines Bereichs verarbeitet nur diese Seite und dieses Rechteck.
Sie erstellt keine musikalischen Teilseiten, teilt kein Heft auf und verändert
keine bestehende Freigabe. Gespeicherte OCR-Bilder sind geschützte Auszüge der
erneut hashgeprüften Quelle. Bild, Text und Wort-Konfidenz dienen zur Erklärung
des Vorschlags; sie ersetzen weder die vollständige Sichtprüfung noch die
gesonderte Freigabe. Ein unbekannter oder widersprüchlicher Titel beziehungsweise
eine unklare Stimme muss weiterhin manuell geklärt werden.

### Rechteck ausdrücklich als unbestätigte Region speichern

Im nachfolgenden Editor-Inkrement kann derselbe Bereich mit **Region unbestätigt
speichern** dauerhaft erfasst werden. Diese Funktion ist von der OCR-Analyse
getrennt: OCR allein speichert keine musikalische Region. Die Originaldatei bleibt
unverändert; das gespeicherte Rechteck ist noch keinem Werk oder einer Stimme
zugeordnet und weder geprüft noch freigegeben.

Eine gespeicherte Region über ihre Schaltfläche laden, Grenzen kontrollieren und
erneut speichern: Es entsteht eine neue Revision derselben Region. **Neue Region**
löst die Bearbeitung von der bisherigen Region. Während die PDF lädt oder eine
andere Seite rendert, sind gespeicherte Regionsschaltflächen deaktiviert. Bei
veraltetem Stand neu laden; fremde Änderungen werden nicht überschrieben.
Fehlt die verifizierte CLEAN-Kopie oder die gespeicherte Originalgeometrie,
wird nicht gespeichert. Frühere Revisionen und historische Ausgaben bleiben
erhalten. Zusammenlegen, Reihenfolge, Dokumentvorschau und die musikalische
Regionsfreigabe sind weiterhin offene Funktionen. Die technische Browserabnahme
dieses Editor-Inkrements steht vor seiner Integration noch aus.

### Temporäre Regionsfolge vorschauen

Im nachfolgenden Vorschau-Batch lassen sich gespeicherte Regionsrevisionen über
acht Vorschauplätze ausdrücklich anordnen. Leere Plätze werden ausgelassen;
dieselbe Region darf bewusst mehrfach vorkommen. **Unbestätigte Folge vorschauen**
öffnet die sichere PDF-Ansicht dieser Reihenfolge. Dies speichert keine Edition
und ist weder musikalische Freigabe noch regulärer Archivexport. Die ausgewählten
Revisionen bleiben fest: Eine spätere Grenzkorrektur verändert diese Vorschau-URL
nicht. **Zurück zur Quellprüfung** führt zur unveränderten Originalquelle zurück.
Die native Browserprüfung dieses Folge-Batches steht noch aus.

## Navigation und Stapelfreigabe

**Vorherige Version** und **Nächste Version** wechseln durch die Prüfwarteschlange.
Die eigene visuelle Prüfung bleibt pro Version/Zuordnung gespeichert. In der
Warteschlange können nur einzeln von Ihnen geprüfte Entwürfe ausgewählt werden.
Maximal 25 Versionen auf der aktuellen Seite auswählen, die getrennte Erklärung
aktivieren und **Stapel-Freigabe beauftragen** wählen. Veraltete, geänderte,
ungeprüfte oder widersprüchliche Versionen führen zur Ablehnung des ganzen Stapels;
es werden keine Teilaufträge gespeichert. Die Auswahl läuft nach einer Stunde ab.
Nach Neuladen ist eine aktuelle Auswahl möglich. Die Dateien werden erst nach ihren
individuellen erfolgreichen Publikationsaufträgen nutzbar; der Stapel ist keine
gemeinsame atomare Dateisystempublikation.
