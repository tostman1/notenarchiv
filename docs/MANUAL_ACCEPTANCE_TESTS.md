# Manuelle Produktabnahme — Notenarchiv & Marschbuch-Generator

**Dokument:** `docs/MANUAL_ACCEPTANCE_TESTS.md` · **Version:** 1.0 — 2026-11-28
**Grundlage:** WP-54/55-Softwarebasis `b536d8d` (siehe `docs/wp54-55-acceptance.md`) plus erster OCR-Inkrement `a2e178fd90f0a276e54e5ed932f048303c7c1910` auf `feat/ocr-product-phase`, PR #95, CI-Lauf 46073430077. Integration und manuelle Abnahme sind getrennte Schritte.
**Status:** Abnahmeplan. **Keine** der folgenden manuellen Tests wurde ausgeführt. Jeder Fall beginnt mit Status **nicht ausgeführt**; „bestanden" wird nur nach tatsächlicher Durchführung vermerkt.

## Zweck, Rolle und Regeln

Gemeinsamer, praxisnaher Abnahmeplan für **Product Owner und Archivar:innen** — von der Indizierung über Prüfung und Projekte bis zu Mappen, Druckvorschau und physischer Abnahme. Maßgeblich sind `REQUIREMENTS.md` (stabile IDs), `IMPLEMENTATION_PLAN.md` (Arbeitspakete) und `DECISIONS.md`. DEC-16 bestimmt: Dieses Dokument ist der Belegplan der manuellen Abnahme; synthetische CI-Ergebnisse errichten **nie** einen manuellen Abnahmestatus.

**Verfügbarkeitskennzeichnung (jeder Fall trägt genau eine):**
1. **Verfügbar — lokal prüfbar:** umgesetzt im aktuellen Quellstand; Abnahme mit synthetischen Testdaten auf einer lokalen/Container-Installation möglich.
2. **WP-54/55-Basis (synthetisch verifiziert):** Softwarebestand (Regionen, Editionen, Sammlungen, gemeinsame Seiten-Strategie, 125-Edition-Publikation) ist durch synthetische CI-Nachweise verifiziert; die manuelle Produktabnahme ist offen.
3. **Nicht implementiert (WP-x):** Zielzustand des genannten Pakets; der Fall wird erst nach Umsetzung des Pakets abgenommen.
4. **Hardware-/Physische Abnahme (eigenes Gate):** erfordert genehmigten echten DS224+, echten Drucker bzw. Windows-Umgebung (DEC-15, WP-22/44/46/52).
5. **Teilweise implementiert:** die im Fall benannten Teilfunktionen sind prüfbar; offene Schritte werden separat protokolliert, nicht als bestanden gewertet.
6. **Blockiert:** eine konkrete fehlende Voraussetzung verhindert die Durchführung; Grund und nächster Schritt werden im Protokoll festgehalten.

**Allgemeine Voraussetzungen (sofern nicht anders angegeben):**
- Angemeldetes Archivar:innen-Konto (einziger Rechtyp), deutsche Weboberfläche, Desktop-Browser.
- Nur synthetische, deterministische Testdaten (keine echten Vereinsdaten, keine realen Noten); fiktive Namen sind zulässig.
- Hintergrunddienst (Worker) verfügbar, soweit der Fall Aufträge erzeugt.
- Getrennte synthetische Wurzeln: RAW (nur lesen), CLEAN, PROCESSED, EXPORT, STATUS.

**Durchführungsprotokoll — am Ende jedes Falls (Pflichtfelder):**
- **Manueller Status:** `nicht ausgeführt` (initial) / `bestanden` / `fehlgeschlagen` / `blockiert`
- **Tatsächliches Ergebnis:** Datum, Prüfer:in, Build/Commit, Stichworte des Beobachteten
- **Defekt:** Kennung im Format `MA-0XX-F<nn>` oder „—"
- **Notizen je Fall:** Beobachtungen, offene Teilprüfungen, Abweichungen und nächste Aktion; initial „—“. Zweck, Voraussetzungen/Daten, Handlung und Erwartet/Kriterien enthalten auch die relevanten Randfälle. Bei teilweiser Verfügbarkeit jeden durchgeführten Teil ausdrücklich benennen.

Empfohlene Reihung: A → K. Hardware-Fälle (Abschnitt K) nur mit genehmigtem Zugriff auf echtes Gerät.

## A — Umgebung, Zugriff und RAW-Schutz

#### MA-001 — Anmelden, deutsche Navigation, ehrliche Leerzustände
- **Zweck:** Nur authentifizierte Archivare erreichen Geschäftsansichten; die deutsche Navigation ist vollständig; nicht umgesetzte Module werden nicht als verfügbar dargestellt.
- **Anforderungen / WP:** UI-01, UI-02, UI-03; WP-03, WP-03a.
- **Voraussetzungen / Daten:** Frische Installation mit leerem synthetischem Archiv.
- **Handlung:** 1) Geschäftsanfrage ohne Anmeldung stellen. 2) Mit Archivar-Konto anmelden, abmelden, erneut anmelden. 3) Alle Hauptmenüs durchlaufen (Übersicht, Notenbibliothek, Indizierung, Prüfwarteschlange, Projekte, Scanaufbereitung, Mitglieder, Instrumente und Stimmen, Aufträge, Einstellungen). 4) Übersicht bei leeren Daten öffnen.
- **Erwartet / Kriterien:** Unangemeldete Anfragen werden abgewiesen (Login, CSRF aktiv). Alle zehn Menüpunkte deutsch vorhanden. Übersicht zeigt Prüfzähler/leere Zustände mit nächstem Schritt, keinen Fehler. Keine externen Netzwerkequests (lokale Assets). Steuerung per Tastatur erreichbar; Status nicht nur farbcodiert.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-002 — DEBUG_MODE: Deploy-Default und Debug-GUI
- **Zweck:** `DEBUG_MODE` abwesend/`FALSE` ⇒ Deploy (keine neuen Debug-Dateien, keine Debug-Routen); `TRUE` ⇒ authentizierte Live-Log-GUI; Django `DEBUG` immer `False`; keine Secrets/OCR-Texte in Logs.
- **Anforderungen / WP:** GR-13, OP-04, GR-14; WP-02, WP-04a, WP-04b.
- **Voraussetzungen / Daten:** Gleiche Image für beide Modi; Start mit und ohne Variable.
- **Handlung:** 1) Start ohne Variable: prüfen, dass keine neuen Debug-Dateien entstehen und Debug-Routen verweigert werden. 2) Start mit `DEBUG_MODE="TRUE"`: anmelden, Debug/Logs öffnen, nach Auftrag/Level filtern, Log-Download anstoßen. 3) Log-Inhalt auf Secrets, Passwörter, echte OCR-Texte prüfen. 4) Start mit leerem/ungültigem Wert.
- **Erwartet / Kriterien:** Ungültige/leere Werte scheitern klar. Deploy verweigert Debug-Routen auch bei vorhandenen alten Logs. Filterung, Pagination und begrenzter Download funktionieren. Django-`DEBUG` in beiden Modi aus (kein Traceback-Detailleak).
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-003 — RAW-Schutz in allen Arbeitsabläufen
- **Zweck:** RAW bleibt über Indexierung, Prüfung, Exporte und Wiederherstellung unverändert; keine Statusmarker in RAW; Schreibversuche an der Mount-/NAS-Grenze werden verweigert.
- **Anforderungen / WP:** GR-01, OP-03; WP-09, WP-14, WP-15 (synthetisch); physische DSM-ACL = eigenes Gate (MA-047).
- **Voraussetzungen / Daten:** Synthetische RAW-Wurzel mit Hash-Inventar (alle Pfade + SHA-256) vor Testbeginn dokumentiert.
- **Handlung:** 1) Inventar aufnehmen. 2) MA-004 bis MA-011 nacheinander durchführen. 3) Inventar erneut aufnehmen und vergleichen. 4) Als Serviceidentität per App und direkt am Mount Erzeugen/Umbenennen/Löschen in RAW versuchen. 5) STATUS-Baum auf Marker prüfen.
- **Erwartet / Kriterien:** Inventar bitgenau unverändert. Alle Schreibversuche werden verweigert (App und Mount). Marker/STATUS-JSON erscheinen nur im getrennten STATUS-Baum, nie in RAW.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar (synthetische Wurzeln); physische Verifizierung an DSM/NTFS nur in MA-047/MA-053.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## B — Normaler Archivfluss: Indizieren, prüfen, freigeben, suchen, laden

#### MA-004 — Indizierung eines ausgewählten Ordners (mehrere PDFs, durchmischte Benennung)
- **Zweck:** Zielordner wird inventarisiert; verifizierte Byte-identische CLEAN-Kopien entstehen; STATUS-Marker im getrennten Baum; Prüfung wird angestoßen; RAW bleibt unverändert.
- **Anforderungen / WP:** AR-01–04, AR-06, GR-01–02; WP-14, WP-15, WP-16.
- **Voraussetzungen / Daten:** Synthetischer Unterordner mit 8–12 PDFs: Scans (monochrom) und Vektor-PDFs, A4 Hochformat/Querformat und A3; Namen mit Titel, Stimme, Scanner-Junk (`scan_0042.pdf`), durchmischter Kodierung; bereits korrekt benanntes PDF ebenfalls enthalten.
- **Handlung:** 1) **Indizierung** öffnen, Unterordner angeben, bestätigen, **Indizieren** wählen. 2) Auftragsseite: Fortschritt und Worker beobachten. 3) Ordnerseite: Inventarstatus, Prüfanzahl, **STATUS-JSON veröffentlicht und geprüft** prüfen. 4) STATUS-Baum auf Textmarker + maschinenlesbarem JSON prüfen. 5) CLEAN: Kopien existieren, auch das korrekt benannte wurde kopiert; Namen sicher/lesbar. 6) Einmal RAW-Inventar abgleichen.
- **Erwartet / Kriterien:** Auftrag durchläuft wartend → aktiv → abgeschlossen; Fortschritt sichtbar; Abbrechen ist möglich (keine halben Publikationen). SHA-256 der CLEAN-Kopien identisch mit Quelle. STATUS-Marker und JSON im STATUS-Baum, nie in RAW. Korrekt benanntes PDF wurde trotzdem kopiert. Unbekannte Zuordnungen liegen in `CLEAN/_Ungeprueft` (umkehrbar), keine davon ist für Generation nutzbar. Absolute Pfade/Überschneidungen werden abgewiesen.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-005 — Vollarchive-Indizierung, große PDF und Fortschritt/Abbrechen
- **Zweck:** Ganzer RAW-Baum wird inventarisiert; große/geometrisch gemischte PDFs bleiben begrenzt und abbrechbar; Fehler werden klar benannt.
- **Anforderungen / WP:** AR-01, AR-04, OP-02; WP-15, WP-16, WP-17, WP-05c.
- **Voraussetzungen / Daten:** Gesamter synthetischer RAW-Baum; eine 400+ Seiten PDF; eine PDF mit ungewöhnlicher Größe/Drehung (z. B. 45°/90°/180°/270°); ein defektes PDF (unlesbar).
- **Handlung:** 1) Feld leer lassen → **Indizieren** wählen. 2) Auftragsseite: Fortschritt, dann **Abbrechen** wählen. 3) Laufende Abgeschlossenheit prüfen (bereits kopierte Dateien bleiben). 4) Erneut komplett indizieren, diesmal durchlaufen lassen. 5) Fehlerliste für das defekte PDF prüfen.
- **Erwartet / Kriterien:** Abbruch stoppt kooperativ; fertige Kopien bleiben; erneut Start arbeitet idempotent. Fortschritt und Abbruchknopf für lange Aufträge sichtbar; Web bleibt reaktionsfähig. Defektes PDF: klarer Fehler, Auftrag/Datei nicht als erfolgreich markiert. Gedrehte Seiten werden mit Original-Geometrie aufgenommen, nicht stillschweigend „repariert".
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-006 — Einzelprüfung und Freigabe (inkl. konflizierender Vorschlag, Kombi-Stimme)
- **Zweck:** Jede neue/geänderte PDF wird visuell geprüft, bevor sie nutzbar wird; Vorschläge sind Hinweise, keine Freigabe.
- **Anforderungen / WP:** AR-08–13, GR-03–04; WP-19, WP-20a, WP-18.
- **Voraussetzungen / Daten:** Drei Fälle: (a) Scan mit eindeutigem Namen, Inhalt stimmt; (b) Scan, Name `Posaune 2`, Inhalt ist `Posaune 1`; (c) Vektor-PDF mit Textschicht `Trombone II/III`. Scaninhalt ausdrücklich per OCR analysieren oder manuell vergleichen; reine Dateinamenerkennung kann den Konflikt nicht beweisen.
- **Handlung:** 1) **Prüfwarteschlange** öffnen, **Version prüfen und zuordnen**. 2) PDF vollständig durchblättern/zoomen; Name + erkannter Text nur als Hinweis. 3) Fall (b): Konflikt erkennen, Arrangement/Stimme manuell korrigieren, **Zuordnung speichern**. 4) Fall (c): beide Stimmen auswählen (eine ungeteilte PDF bleibt beiden Stimmen). 5) Persönliche Erklärung aktivieren → **Visuelle Prüfung speichern** → getrennte Freigabeerklärung → **Freigabe beauftragen**. 6) Worker-Publikation abwarten. 7) Fehlerpfad: Freigabe beauftragen, Worker simuliert fehlschlagen (bzw. defekte Quelle), Zustand prüfen, danach korrigiert erneut freigeben.
- **Erwartet / Kriterien:** Nur nach geprüfter Version und erfolgreicher Publikation ist die Version nutzbar; bis dahin für Generation gesperrt. Öffnen der Vorschau oder hohe Konfidenz genügen nicht. Freigeschlagene Freigabe macht nicht nutzbar; Historie bleibt. Mehrfachzuordnung möglich; kombinierte Stimme wird nicht aufgeteilt. Prüfhistorie hält Konto, Zeit, Version, Zuordnung. RAW bleibt unverändert; kanonische Namen tragen nur CLEAN-Kopien.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-007 — Stapelfreigabe und ihre Schutzregeln
- **Zweck:** Stapelfreigabe deckt nur einzeln geprüfte, gültige, unveränderte Versionen ab; sonst wird klar abgelehnt.
- **Anforderungen / WP:** AR-13, GR-04; WP-20b.
- **Voraussetzungen / Daten:** Mindestens 30 geprüfte Entwürfe auf mehreren Seiten; darunter bewusst: eine ungeprüfte Version, eine geänderte/veraltete Version, ein Widerspruch.
- **Handlung:** 1) Geprüfte Versionen auswählen, Erklärung, **Stapel-Freigabe beauftragen** → Erfolg. 2) Misch-Auswahl (mit ungeprüfter) erneut versuchen. 3) Nach Änderung einer gespeicherten Zuordnung erneut Stapel wählen. 4) Auswahl eine Stunde verfallen lassen, erneut versuchen. 5) Neuladen und frische gültige Auswahl bilden.
- **Erwartet / Kriterien:** Stapel 1 wird akzeptiert (max. 25 Versionen/Seite; Rest in weiteren Seiten). Stapel 2/3/4 werden mit klarer Begründung abgelehnt; es entstehen keine Teil-Aufträge. Nach Neuladen frische Auswahl möglich. Jede Datei wird erst nach individuellem erfolgreichen Publikationsauftrag nutzbar; Stapel ist keine gemeinsame atomare Dateisystempublikation.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-008 — Bibliothekssuche, Gleichnamigkeit, Vollständigkeit
- **Zweck:** Suche findet Titel/Alias auch mitten im Wort; gleiche Titel bleiben getrennte Werke; Vollständigkeit unterscheidet bestätigbar/ungeprüft/fehlend/nicht benötigt/unknown.
- **Anforderungen / WP:** AR-15 (Basis), AR-16, GR-05; WP-11, WP-21.
- **Voraussetzungen / Daten:** Zwei Werke mit gleichem Titel (verschiedene Komponisten/Arrangemente); ein Titel `ABBA Medley`; ein Titel `Fuchsgraben Polka`; Arrangemente mit Erwartungsschablonen (inkl. optionaler Stimmen) und ohne Erwartungsdaten.
- **Handlung:** 1) Suche `ab` → beide Treffer (`ABBA Medley`, `Abel Tasman` o. ä.). 2) Suche `uchs` → Treffer mitten im Wort. 3) Beide gleichnamigen Werke öffnen: eigene IDs, keine Zusammenführung. 4) Vollständigkeitsansicht je Arrangement × Stimme prüfen. 5) Erwartungs-Template anwenden und anpassen (optionale Stimme).
- **Erwartet / Kriterien:** Normalisierte, groß-/kleinschreibungsunabhängige Teilstringsuche. Vollständigkeit unterscheidet: bestätigt verfügbar, ungeprüft, fehlend, nicht erforderlich, Erwartung unbekannt; „vollständig geprüft" ≠ „vollständig". Ohne Erwartungsdaten: Vollständigkeit unbekannt. Unicode-/Akzentfälle separat in MA-058 prüfen; keine unbelegte Umlautumschrift voraussetzen.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-009 — Archiv-Editionen und direkte Noten-Downloads
- **Zweck:** Mehrere bestätigte Versionen koexistieren; eine Archiv-Präferenz pro Arrangement/Stimme; direkte Downloads ohne Projekt/Mitglied; keine stillschweigenden Ersetzungen.
- **Anforderungen / WP:** AR-17, AR-18, EX-03, EX-07; WP-23a, WP-23b.
- **Voraussetzungen / Daten:** Zwei bestätigte Versionen derselben Stimme (alter/aktiver Scan); eine zweite, inkompatible Stimme; ein bereits festgewähltes Projekt mit expliziter Version (siehe MA-035).
- **Handlung:** 1) Beide Versionen im Arrangement anzeigen; eine als Archiv-Präferenz setzen. 2) Inkompatible/in Prüfung befindliche Auswahl versuchen (muss abgelehnt werden). 3) Aus der Bibliothek 1 + mehrere bestätigte Stimmen/Versionen auswählen, Vorschau anzeigen, einzeln und als ZIP herunterladen. 4) Dieselbe physische PDF zweimal wählen: Kopienzahl klar anzeigen. 5) Nicht bestätigte Version laden versuchen.
- **Erwartet / Kriterien:** Nur bestätigte, gültige Versionen wählbar. Einzeldownload-Bytes entsprechen der gespeicherten, verifizierten Version; kein direkter Dateisystemzugriff durch Nutzende und keine Modifikation. Kombinierte Stimmen bleiben eine PDF. Mehrfachwahl derselben Datei zeigt Kopienzahl; keine versehentlichen Duplikate. Nicht bestätigte Auswahl wird verweigert.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-010 — Geänderte/fehlende Quellen, Integrität, Historie
- **Zweck:** Unveränderte bestätigte Versionen werden nicht erneut bearbeitet; geänderte Versionen brauchen neue Prüfung; gelöschte RAW löst keine Löschung aus; Integritätsjob findet identische Bytes bei gleicher Größe/mtime.
- **Anforderungen / WP:** AR-05, AR-14, GR-05–06; WP-27 (Zustand), WP-15 (Scan).
- **Voraussetzungen / Daten:** Bestätigte Quelle; Version mit geänderten Bytes, aber gleichem Namen; RAW-Datei, die nach Freigabe aus RAW entfernt wurde; zwei unterschiedliche Inhalte mit gleicher Dateigröße und gleichem Änderungszeitpunkt. Änderungen nur in genehmigten synthetischen Testquellen, nicht über die read-only App-Identität.
- **Handlung:** 1) Gleiche Quelle erneut indizieren → prüfen, dass bestätigt/unchanged nicht erneut in die Warteschlange kommt. 2) Geänderte Bytes indizieren → neue wartende Version, alte bestätigt bleibt referenzierbar. 3) RAW-Datei entfernen (synthetisch) und erneut scannen → fehlend wird gemeldet. 4) Integritätsprüfung ausführen (falls im Build verfügbar), Hashes und DB-Beziehungen prüfen. 5) Historische Version erneut öffnen/laden.
- **Erwartet / Kriterien:** Unveränderte bestätigt ⇒ keine Routine-Neuprüfung/-OCR. Geänderte Version ⇒ neue Prüfung; alte bestätigte Version bleibt für Historie referenzierbar. Fehlende RAW ⇒ keine automatische CLEAN-Löschung; Status „fehlend" getrennt. Integritätsjob erkennt unterschiedliche Hashes trotz gleicher Größe/mtime; Routine-Scan kann size/mtime nur als Hinweis verwenden. **Hinweis:** Der vollständige manuelle Integritätsjob ist in WP-27 (aktuell deaktiviert, siehe docs/indizierung.de.md) — bis dahin nur Scan-Verhalten abnehmen.
- **Verfügbarkeit:** Teilweise: Scan-/Verhaltensaspekte Verfügbar — lokal prüfbar; vollständiger Integritätsjob nicht implementiert (WP-27).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-011 — Mitglieder-, Instrumenten- und Ensemble-Stammdaten
- **Zweck:** Stammfunktionen: gleiche Namen, gleiche Titel, UUID-Identität, genau eine reguläre Stimme pro Mitglied, Gäste, Deaktivierung statt Löschung.
- **Anforderungen / WP:** CAT-01–04, PR-04; WP-11, WP-12, WP-34.
- **Voraussetzungen / Daten:** Zwei Mitglieder „Anna Berger" (gleicher Name, unterschiedliche Stimmen); Instrumente „Posaune B" vs. „Posaune C" (gleichnamig, unterschiedliche Notation); zwei gleichnamige Werke; Gastmusiker mit gültiger Stimme.
- **Handlung:** 1) Beide „Anna Berger" anlegen, beide regulär einer Stimme zuordnen; prüfen, dass sie nicht zusammengeführt werden. 2) B-/C-Posaune in Zuordnungs-Dropdowns unterscheidbar auswählen (kein Freitext). 3) Gast für ein Projekt anlegen (ohne dauerhafte Mitgliederveränderung). 4) Referenzierte Mitglieder deaktivieren; Schutz der Referenz prüfen. 5) Ensemble-Rollen: Rolle 3 ↔ Posaune 3 (Posaunist) und Rolle 3 ↔ passendes Tenorhorn (anderer Spieler), unterschiedliche Notation; Positions-Ausnahme anlegen.
- **Erwartet / Kriterien:** Gleiche Namen/Titel erlauben separate Datensätze (UUID-Identität). Dropdowns durchgehend kontrolliert; Freitext nur für freie Felder/Aliasse. Genau eine reguläre Stimme pro aktivem Mitglied. Gast erscheint nur im Projekt. Deaktivierung erhält Referenzen. Gleiche Rollenzahl ≠ Kompatibilität; persönliches Auswahl schlägt Ensemble-Mapping; keine automatische Transposition.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## C — Intaktes 125-Stücke-A5-Buch: optionaler Index und Drucken

#### MA-012 — Intaktes A5-Buch: Indizierung ohne Segmentierung
- **Zweck:** Ein A5/Buch-Scan (125 kurze Stücke, 4–6 pro Seite) bleibt als eine unveränderliche Quelle je Instrument les- und exportierbar; Segmentierung ist optional; kein Zwang zum Aufteilen.
- **Anforderungen / WP:** AR-25, AR-26, GR-16; WP-54/55 (synthetisch verifiziert); Segmentierungseingabe später WP-56.
- **Voraussetzungen / Daten:** Synthetisches A5-Buch mit 32 Seiten, 4 Karten/Seite (128 Felder, 125 Werke + Titel/Nummern), zwei Instrumentenversionen (gleiche Titel/Nummern, unterschiedliche Seiten-/Koordinatenpositionen); Titel- und Nummernauftritt pro Seite, ggf. Titel nur im Cover (Instrumentennachweis).
- **Handlung:** 1) Buch als Ganzes indizieren; neutrale, menschenlesbare Quellenidentität + kollisionssicherer CLEAN-Pfad prüfen (eine byte-identische BASE je Instrument, keine 125 Duplikat-Quellen). 2) Vorschau des kompletten Buchs in ursprünglicher Seitenfolge öffnen. 3) Export des kompletten Buchs (Seitentreu-Modus) anstoßen und herunterladen. 4) Gleiche Operation für beide Instrumente.
- **Erwartet / Kriterien:** Eine ungeteilte Quelle je Instrument; Original-Seitenfolge und Original-Geometrie im Lese-Export; keine automatische Aufteilung; Werk-/Stimmbezüge bleiben Metadaten. Deckblatt mit Instrumentennachweis wird akzeptiert. BASE-Kopie bleibt ungenehmigte Quelle; Export verlangt ausdrücklich bestätigte Inhalte (MA-013) oder die Ganzbuch-Verwendung gemäß Freigabe.
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert); manuelle Produktabnahme offen. Automatische Segmentierung nicht implementiert (WP-56).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-013 — Buch mit Einzelwerk-Index: Auswahl, Fortsetzungen, gemeinsame Seiten
- **Zweck:** Jeder der 125 Werke ist einzeln über Identität + originale Song-Nummer wählbar, auch bei unterschiedlichen Seiten/Koordinaten je Instrument; Fortsetzungen über Seiten; explizite Strategie für gemeinsame Seiten.
- **Anforderungen / WP:** AR-25, AR-20, AR-21, EX-11, EX-12, EX-13; WP-55, WP-54 (synthetisch verifiziert).
- **Voraussetzungen / Daten:** Aus MA-012 geindexte Instrumente; mehrere Werke mit mehrseitiger Fortsetzung; ein Werk, das auf derselben Seite in beiden Instrumentenversionen vorkommt; mindestens zwei gleichnamige Werke.
- **Handlung:** 1) Per Song-Nummer/Suche ein Werk in beide Instrumenten aufrufen; Original-Kontext (Seite, Region) anzeigen. 2) Einzelwerk als bestätigt exportieren (Region extrahieren) — Vorschau der Konsequenz (ausgegebene Seiten) prüfen. 3) Gemeinsame Seite in drei Strategien testen: Region extrahieren / komplette Seite einmal behalten / komplette Seite wiederholen; bei Seite-mal-/-wiederholen: unabhängige Ganzdatei-Freigabe erforderlich, Teilbestätigung reicht nicht. 4) Export zweier Werke aus derselben Seite; Vorkommensreihenfolge und -Identität prüfen. 5) Gleichnamige Werke getrennt halten.
- **Erwartet / Kriterien:** Suche findet Werk über Song-Nummer und Identität; Seitennumerengleichheit ist keine musikalische Identität. Regionen behalten explizite Reihenfolge und Original-Quellen-Hashes. Vor der Freigabe wird die Konsequenz (Seitenzahl) angezeigt; keine stillschweigende Auslassung/Duplikation. Ganzseiten-Modus ohne vollständige Ganzdatei-Freigabe: Verweigerung. Historische Pins bleiben nach Region-Änderungen reproduzierbar; geänderte Revisionen schließen nur betroffene Inhalte aus.
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert); manuelle Produktabnahme offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-014 — Buch in Projektliste: A4/A3, ein-/zweiseitig, Blattfüllung
- **Zweck:** A5-Buchinhalte werden in Druckvorlagen zu A4/A3 zusammengesetzt (einfach/doppelseitig, n-up, Blattfüllung/Blanks) ohne Aufteilung echter A3-Inhalte und ohne Zahlen auf Noten.
- **Anforderungen / WP:** PT-06–10, EX-13, SC-03, GR-12, GR-11; WP-57 (Vorlagen), WP-42 (Heftgeometrie) — beides noch nicht implementiert.
- **Voraussetzungen / Daten:** Aus MA-013 bestätigte Inhalte; Vorlagen: A5→A4 einfach (2 pro Blatt), A5→A4 doppelseitig (4), A5→A3 einfach (4), A5→A3 doppelseitig (8); ein Mix mit eingebetteten echten A3-Seiten; ungerade Seitenzahlen.
- **Handlung:** 1) Jede Vorlage als Projektanordnung bzw. Direktexport erstellen; 2) Vorschau: logische Seiten, physische Blätter, Vorder-/Rückseite, Bindungsränder, Füllseiten prüfen; 3) PDF herunterladen; 4) Blattformat messen (Toleranz); 5) Füllseiten ein- und ausschalten; 6) echte A3-Seite im A5-Mix kontrollieren.
- **Erwartet / Kriterien:** N-up-Kennzahlen korrekt (2/4 bzw. 4/8); Seitenzahlen nur im Inhaltsverzeichnis/UI/Metadaten, nie auf Noten. A5-Seiten passen proportional in den bedruckbaren Bereich (kein Dehnen, kein Zuschneiden); ungerade Fülle mit konfigurierbaren Füllseiten; echte A3 bleibt vollständig; Vorschau unterscheidet Quelle/letzte Seite/Blatt beidseitig; Manifest enthält Vorlagenrevision, Warnungen, Füllseiten.
- **Verfügbarkeit:** Nicht implementiert (WP-57, WP-42); numerische CI-Vorabnahme separat; physische Papierabnahme MA-049/MA-050.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-015 — Buch-Abgrenzung: Lese- vs. Druck-Artefakt, Marschbuchmaße
- **Zweck:** Lese-PDF behält Originalseitenformate; Druck-PDF ist ein separates Artefakt; Marschbuch-Standard 170 × 120 mm, pro Projekt anpassbar.
- **Anforderungen / WP:** EX-07, SC-03, GR-11; WP-42 (noch offen).
- **Voraussetzungen / Daten:** Projekt im Marschbuch-Format mit A5-Buchinhalten und gemischten A4/A3-Quellen.
- **Handlung:** 1) Lese-PDF erzeugen: Seitenformate/Orientierung der Originalen prüfen (inkl. A3 vollständig). 2) Druck-PDF mit Marschbuch-Format 170 × 120 mm und 180 × 125 mm erzeugen; 3) Skalierung/Seitenlesbarkeit und Ränder prüfen; 4) Vorschau mit Rand-/Bindungsanzeige öffnen.
- **Erwartet / Kriterien:** Lese- und Druck-Artefakte sind getrennt; keine Zahlen auf Noten; Marschbuchmaße exakt in Toleranz; Seitenverhältnis und Lesbarkeit erhalten, kein Zuschneiden; Vektorwo möglich; Cover/Inhaltsverzeichnis im gewählten Projektformat.
- **Verfügbarkeit:** Nicht implementiert (WP-42); Lese-PDF-Prinzip teilweise über EX-07 (WP-37a) abnehmbar, sobald die Projekt-Verknüpfung zu Buchinhalten aktiviert ist.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## D — Zusammengesetzte Scans, Regionen, Fortsetzungen und Ablehnung

#### MA-016 — Zusammengeführter Scan: Segmentierungsvorschlag und Gruppen
- **Zweck:** Ein komplettes Mehrteil-/Mehrwerk-Scan-Dokument wird in überprüfbare Gruppen aufgeteilt (1–3/4–5/6–8/leer-9/10–11 ⇒ vier Teilgruppen + Leerklassifikation); Fortsetzungen ohne wiederholte Kopfzeile bleiben zusammen.
- **Anforderungen / WP:** AR-19, AR-20, SC-05; WP-56 (noch offen).
- **Voraussetzungen / Daten:** Synthetischer Scan mit exakt diesem Seitenmuster, inklusive Leerseite 9 und fehlendem wiederholten Titel auf den Fortsetzungsseiten 2–3. Zweite Variante mit bewusst falscher Gruppengrenze für manuelle Korrektur.
- **Handlung:** 1) Manuellen Batch-Eingang ausführen (unabhängig von Inbox). 2) Segmentierungsvorschlag im Editor anzeigen: Thumbnails, Vollauflösung, Gruppen, Konfidenz, zugeordnete Musik. 3) Ausgangsmuster mit vier Gruppen prüfen; anschließend in der fehlerhaften Variante benachbarte Gruppen zusammenlegen, eine aufteilen und Reihenfolge korrigieren. 4) Seiten 2–3 als Fortsetzung von Seite 1 markieren. 5) Leerseite 9 klassifizieren. 6) Ergebnis als überprüfbaren Vorschlag (noch nicht bestätigt) speichern.
- **Erwartet / Kriterien:** Vorschläge ≠ Bestätigung. Vier Teilgruppen + Leerklasse; fehlende Kopfzeile allein trennt keine Teil. Gruppen/Regionen haben stabile Identität; Original-Seiten und -Hashes bleiben erhalten. Editor: verschieb-/vergrößerbare Rechtecke, Zuordnung zu Werk/Teil/Ausgabe, Dokumentvorschau.
- **Verfügbarkeit:** Nicht implementiert (WP-56); Eingabegrundlagen (WP-15/17/18/19) verfügbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-017 — Regionen, native A3 und Mischformate
- **Zweck:** Mehrere logische Seiten können auf einen Scan verweisen (2×A4 auf A3, 4 Karten, gegenüberliegende Buchseiten); nur Maßstab trennt niemals echte A3; Mischgröße/Orientierung bleibt unterstützt.
- **Anforderungen / WP:** AR-20, GR-11, AR-01; WP-54 (verifiziert), WP-56 (Editor).
- **Voraussetzungen / Daten:** Echte A3-Notenseite; A3-Scan mit 2 A4-Bildern; A5-Buch mit 4 Karten; Misch-Scan mit A4 Hoch-/Querformat, A3 und Buchformat, teils gedreht.
- **Handlung:** 1) Jede Quelle indizieren und in der Vorschau öffnen; 2) Logische Seiten/Regionen anzeigen (Geometrie, Einheiten, Transformation); 3) Eine echte A3 explizit mit und ohne Regionen exportieren; 4) Misch-Scan: Orientierung pro Seite prüfen, Drehung korrigieren (nicht-destruktiv).
- **Erwartet / Kriterien:** Echte A3 bleibt eine ganze logische Einheit; Trennung nur durch überprüfte Regionen. Karten/Buchseiten referenzieren denselben Scan mit korrekter Geometrie (CropBox/UserUnit, Vierteldrehungen). Mischformate bleiben intakt; Rotation wird als korrigierbare Eigenschaft gespeichert, Original-Byte bleibt unverändert.
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert); graphischer Editor: nicht implementiert (WP-56).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-018 — Doppelungen und Leerseiten: erkennen, nie automatisch entfernen
- **Zweck:** Identische Bytes/Seiten werden deterministisch erkannt; exakt-Duplikat, mögliches optisches Duplikat, wiederholte Seite, Teil-Duplikat und andere Ausgabe bleiben unterscheidbar; keine automatische Löschung/Zusammenführung.
- **Anforderungen / WP:** AR-22; WP-56 (Basis) / WP-40d (fortgeschritten, sekundär).
- **Voraussetzungen / Daten:** Byte-identische Doppelung eines Scans; optisch gleiche, aber neu komprimierte Version; bewusste wiederholte Seite; zwei Editionen desselben Stücks.
- **Handlung:** 1) Alle Varianten in denselben Batch geben; 2) Duplikaterkennung anzeigen; 3) Jede Variante klassifizieren; 4) Löschen/Zusammenführen nur manuell und explizit versuchen; 5) Historie der Entscheidungen prüfen.
- **Erwartet / Kriterien:** Exakt-Duplikat (gleiche Bytes) wird als solches markiert; optisch ähnliche nur als Warnung; wiederholte Seiten und andere Editionen werden nicht mit exakten Duplikaten verwechselt. Kein automatisches Entfernen/Überschreiben; unklare Ähnlichkeit ⇒ Warnung, nicht Entscheidung. Fortgeschrittene optische Erkennung (neu komprimierte Kopien vs. andere Ausgabe) ist WP-40d (sekundär) — bis dahin nur Warnung erwarten.
- **Verfügbarkeit:** Grundfunktionen nicht implementiert (WP-56); fortgeschrittene Erkennung: WP-40d (sekundär).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-019 — Alle Vorschläge ablehnen: Original bleibt, ohne Reparatur
- **Zweck:** Der Archivar kann alle Segmentierungs-/Zuordnungsvorschläge zurückweisen; Originalseiten bleiben unversehrt, Regionen werden nicht einzeln „repariert"; bestätigte Teilkorrekturen folgen den bestehenden Revisions-/Prüfregeln.
- **Anforderungen / WP:** SC-05, AR-21; WP-56 (noch offen).
- **Voraussetzungen / Daten:** Segmentierung mit mehreren fehlerhaften Vorschlägen aus MA-016; zusätzlich ein korrekt bestätigter Teilbereich.
- **Handlung:** 1) Alle Vorschläge einzeln bzw. gesammelt ablehnen; 2) Originaldokument und -Seiten vor/nachher vergleichen (Hash, Reihenfolge); 3) Bestätigten Teilbereich in einem Export verwenden; 4) Den Rest als sichtbar unvollständig markieren; 5) Eine Region nachträglich ändern ⇒ neue Revision, frühere bleibt erhalten.
- **Erwartet / Kriterien:** Ablehnung ändert keine Originaldaten; Vorschlags-/Bestätigungsvermutung getrennt. Konfidenz, Thumbnails und Sammel-Auswahl genehmigen nie. Korrekt bestätigte Anteile dürfen verwendet werden, während der Rest sichtbar unvollständig ist. Regionen-/Zuordnungsänderungen invalidate nur die betroffenen Bestätigungen; frühere Revisionen und historische Snapshots bleiben erhalten.
- **Verfügbarkeit:** Nicht implementiert (WP-56); Bestätigungs-/Revisionsmodell (WP-54) synthetisch verifiziert.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-020 — Große PDFs und leere Sammlungen
- **Zweck:** Große PDFs (viele Seiten, große Bytes) bleiben in begrenztem Speicher/Zeit verarbeitbar; leere Sammlungen/Projekte zeigen vorhersehbare Leerzustände ohne Fehler.
- **Anforderungen / WP:** OP-02, OP-09, AR-01, UI-03; WP-17, WP-56 (begrenzte Analyse).
- **Voraussetzungen / Daten:** 1.000+ Seiten-PDF; 200 MB+ PDF; leere Sammlung ohne Werke; leeres Projekt ohne Teilnehmer.
- **Handlung:** 1) Große PDF indizieren/vorschauen; Speicher und Antwortzeiten beobachten; 2) Begrenzungen der Seiten-/Piksel-/Zeit-/Scratch-Begrenzungen in der Vorschau prüfen; 3) Leere Sammlung öffnen (Suche, Seiten); 4) Leeres Projekt: Stückliste, Matrix, Vorprüfung öffnen.
- **Erwartet / Kriterien:** Web bleibt reaktionsfähig (ein schwerer Worker, begrenzter Parallelbetrieb); Rendering/Parsing ist begrenzt und schlägt kontrolliert fehl, nicht mit Absturz. Leerzustände sind klar, mit Handlungsoptionen; keine 500er; Suche auf leeren Daten liefert vorhgesagbar leeres Ergebnis mit Zähler 0.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar (grundlegende Grenzen); vollständige Begrenzung von Segmentierung: WP-56.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## E — OCR, Textschichten und Unsicherheit

#### MA-021 — OCR anstoßen: unabhängig von Indizierung und Regeln
- **Zweck:** OCR ist eine eigenständige, lokal laufende Funktion: für gewählte ungeprüfte Dateien, nach Regel-/Alias-Änderungen oder als Folge der Indizierung; schwache/konflizierende Beweise bleiben unentschieden.
- **Anforderungen / WP:** AR-08–11, SC-06; WP-24, WP-25 (erster Inkrement implementiert, Gesamtumfang offen).
- **Voraussetzungen / Daten:** Ungeprüfte Scans: (a) sauberer Titel, (b) verrauschte/geschrägte Kopfzeile, (c) Titel nur auf Zusatzseite, (d) zweideutige Abkürzungen (`Pos. 2`, `Trb. 2`, `B. Bass`); eine Regel/Alias-Änderung nach der ersten Analyse.
- **Handlung:** 1) Auf der Prüfseite **Alle Seiten lokal mit OCR analysieren** für einzelne Dateien starten, ohne erneut zu indizieren. 2) Ordnerstart und Indizierung mit OCR-Option erst nach deren Implementierung prüfen. 3) Regeln/Aliase ändern, erneute Analyse auslösen. 4) Für (d) die Behandlung der zweideutigen Abkürzungen prüfen. 5) Auftragsseite: Seitenfortschritt und Abbruch prüfen; Wiederanlauf mit bereits gespeicherter Evidenz testen. Verbliebener aktiver Prozessmarker muss eine Eigentumsprüfung verlangen, nicht automatisch gelöscht werden. Regionsfortschritt separat nach Implementierung prüfen.
- **Erwartet / Kriterien:** OCR wird nie allein wegen eines eindeutigen Dateinamens übersprungen. Lokale Ausführung ohne Netz. Text und Konfidenz bleiben Hinweise, keine musikalische Bestätigung. Abbruch/Neustart: abgeschlossene Seiten verwenden passende Cache-Einträge erneut. Änderungen an Runtime, Profil, Geometrie oder Regeln erzeugen neue Evidenzidentitäten; historische Evidenz bleibt erhalten. Regionsanalyse bleibt späterer Umfang.
- **Verfügbarkeit:** Teilweise implementiert: Einzeldatei-Start, alle Seiten, lokales Tesseract, Cache, Fortschritt/Abbruch und geschützter Wiederanlauf sind implementiert und synthetisch CI-verifiziert. Ordner-/Indexintegration, Regionsstart und vollständige Erkennungsziele bleiben offen (WP-24/25).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-022 — OCR-Beweis-Prüfung: Regionen, Konflikte, Fortsetzungen
- **Zweck:** Die Prüfwarteschlange zeigt OCR-Auszug/Region, Quelle, Konfidenz, Fortsetzungs- und Konfliktgründe; Freigabe erfordert weiterhin Sichtprüfung.
- **Anforderungen / WP:** AR-12, AR-13, AR-21; WP-26 (noch nicht implementiert).
- **Voraussetzungen / Daten:** Aus MA-021: Dateiname ≠ Inhalt; Titel erst auf Seite 2; Fortsetzungsregion ohne eigenen Titel; konflizierende Beweise (Name sagt Werk A, Text sagt Werk B).
- **Handlung:** 1) Prüfwarteschlange öffnen, je Fall: PDF, OCR-Excerpt/Region, Methode, Konfidenz, Konfliktgrund anzeigen lassen. 2) Konflikte manuell korrigieren (Meisterdaten-Dropdowns). 3) Sichtprüfung speichern, freigeben. 4) Technische/OCR-Volltexte in den Logs prüfen.
- **Erwartet / Kriterien:** Beweise in Deploy und Debug verfügbar; Fortsetzungen mit Bezug zum Anfang; Konflikt prominent markiert (kein stilles Mischen). Korrekturen über kontrollierte Auswahl. Freigabe nur nach visueller Prüfung der konkreten Region/Seite; Konfidenz oder Thumbnail genügen nie. Kein vollständiger OCR-Text in technischen Logs (sanitisiert).
- **Verfügbarkeit:** Teilweise implementiert: OCR-Text, Quellseite, Methode, Kontext und bestehende Korrektur/Prüfung sind verfügbar. Bildregionen-Overlay und vollständige Fortsetzungs-/Mehrwerktitel-Evidenz bleiben offen (WP-26/56).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-023 — Textschicht: fehlend, gemischt, irreführend
- **Zweck:** Scans ohne Textschicht, PDFs mit unzuverlässiger Teil-Textschicht und digitale Vektor-PDFs werden unterschiedlich behandelt; eine irreführende Teil-Textschicht verhindert nicht die notwendige lokale OCR.
- **Anforderungen / WP:** AR-08, AR-10, AR-11; WP-17, WP-19 (verfügbar), WP-24/25 (OCR-Vertiefung).
- **Voraussetzungen / Daten:** (a) reiner Scan ohne Textschicht, (b) PDF, deren Textschicht auf einigen Seiten falsch/teilweise ist, (c) Vektor-PDF mit vollständiger, korrekter Textschicht.
- **Handlung:** 1) Alle drei indizieren und jeweils auf der Prüfseite OCR ausdrücklich starten. 2) Bei (a): OCR-Text und Vorschlag bzw. Unsicherheit prüfen. 3) Bei (b): prüfen, dass die Teil-Textschicht OCR nicht verhindert; widersprüchliche Beweise manuell vergleichen. 4) Bei (c): Textschicht- und OCR-Evidenz prüfen. 5) In allen Fällen die tatsächliche PDF zur Sichtprüfung öffnen. Automatische Index-/OCR-Verknüpfung erst nach deren Umsetzung prüfen.
- **Erwartet / Kriterien:** Keine automatische Bestätigung aus Dateiname, Text oder OCR. (a) bleibt unentschieden, bis geprüft (bisheriger Zustand; mit OCR: Kandidat). (b) wird als Konflikt/Ungewissheit markiert, OCR wird nicht unterdrückt. (c) liefert plausible Vorschläge. Sichtprüfung ist in allen Fällen Pflicht.
- **Verfügbarkeit:** Teilweise implementiert: Textschicht und ausdrücklich gestartete OCR für (a)/(b)/(c) sind implementiert; automatische Index-Verknüpfung und vollständige Konfliktvisualisierung bleiben offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-024 — Neuanalyse bestätigt unveränderter Dateien
- **Zweck:** Explizite Neuanalyse einer bestätigten, unveränderten Datei widerruft ihre Freigabe nicht und ersetzt ihre Zuordnung nicht; geänderte Vorschläge brauchen neue Prüfung.
- **Anforderungen / WP:** AR-09, AR-11, GR-06; WP-25, WP-27.
- **Voraussetzungen / Daten:** Bestätigte Datei; danach Regeländerung oder neue OCR-Profilversion; eine zweite Datei mit geänderten Bytes.
- **Handlung:** 1) Bestätigte unveränderte Datei explizit neu analysieren; 2) Freigabestatus und Zuordnung vor/nachher vergleichen; 3) Bei gleichem Ergebnis: keine neue Prüfpflicht (Bestätigung bleibt); 4) Bei neuem Vorschlag (anderer Kandidat): neue Prüfung verlangen; 5) Geänderte Bytes: neue wartende Version, alte bleibt.
- **Erwartet / Kriterien:** Bestätigung unveränderter bestätigter Version bleibt erhalten; nichts wird stillschweigend ersetzt. Neue/konfliktbehaftete Kandidaten werden eingesehen; ihre Übernahme erfordert ausdrücklich eingeleitete Korrektur und erneute Sichtprüfung. Automatisches Erzeugen neuer Prüfaufgaben ist hier nicht als implementiert nachgewiesen. Unveränderter Hash ⇒ keine Routine-Neubearbeitung beim Scan (GR-06).
- **Verfügbarkeit:** Verfügbar — lokal prüfbar: explizite Ganzseiten-Neuanalyse unveränderter bestätigter Dateien und Schutz von Zuordnung/Freigabe sind implementiert. Vollständiger Integritätsjob bleibt WP-27.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## F — Metadaten, Klassifikationen, Dauer und Facettensuche

#### MA-025 — Klassifikationen: Kategorien, Genres, Tags und Dauer
- **Zweck:** Kategorien/Genres/Tags sind getrennte, optionale, mehrfach zuordenbare Klassifikationen; sie verschieben/rennen/duplizieren keine PDFs und implizieren keine Sammlungs-/Projektmitgliedschaft; Dauer ist optionale Sekunden (MM:SS), unbekannt ≠ 0.
- **Anforderungen / WP:** CAT-08; WP-60a (Kern gemäß DEC-16; aktuell noch nicht implementiert).
- **Voraussetzungen / Daten:** Werke mit: Kategorie „Marsch", Genre „Unterhaltung", Tags `2026`, `A-dur`, `schwer`; ein Werk mit Dauer 150 s, eines mit 905 s, eines unbekannt; ein Arrangement mit Override-Dauer.
- **Handlung:** 1) Klassifikationen anlegen (Autocomplete, Normalisierung: gleiche Schreibweise/Leerzeichen ⇒ eindeutig, „Marsch" ≠ „marsch " nicht dupliziert). 2) Mehrfachzuordnung je Werk; Bulk-Zuordnung/-Entfernung. 3) Ähnlich geschriebene, aber verschiedene Bedeutungen nicht zusammenführen lassen. 4) Klassifikation umbenennen/löschen: Musik/Quellen bleiben. 5) Dauer in MM:SS eingeben (02:30, 15:05), Anzeige prüfen, Override je Arrangement setzen.
- **Erwartet / Kriterien:** Alle Metadaten optional — normale Archivierung/Freigabe bleibt ohne sie möglich. Umbenennung/Entfernung ist sicher (keine Datenverlust). Dauer: Ganzzahl ≥ 0 Sekunden, unbekannt getrennt von 0; längere Werke korrekt; Arrangement-Override schlägt Werdauer. Vererbung aus Sammlungen mit expliziten lokalen Overrides (CAT-06).
- **Verfügbarkeit:** Nicht implementiert (WP-60a, Kern-Promotion durch DEC-16); Vererbungsmodell (WP-55) synthetisch verifiziert.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-026 — Facettensuche: UND/OR, alle-Tag-Modus, Bereiche
- **Zweck:** Implementierte Facetten kombinieren: UND über Dimensionen, OR innerhalb einer Dimension; optionale „alle gewählten Tags"; Bereiche inkludierend mit einseitigen Grenzen und explizit unbekannt.
- **Anforderungen / WP:** AR-15, CAT-08; WP-21 (Basis-Suche verfügbar), WP-60a (Facetten, offen).
- **Voraussetzungen / Daten:** Katalog mit kombinierbaren Werten, z. B.: Kategorie {Marsch, Polka}, Genre {Unterhaltung, Feiertag}, Tag {2026, A-dur, schwer}, Dauer {150, 905, unbekannt}; Titel `Fuchsgraben Polka`.
- **Handlung:** 1) Suche `ab` + Kategorie {Marsch, Polka} + Genre {Unterhaltung, Feiertag}: OR innerhalb, UND über Dimensionen erwarten. 2) Alle-Tag-Modus: {2026, A-dur} — Treffer nur bei beiden Tags. 3) Dauerbereich 100–200 s (einschließend), dann nur Untergrenze, dann nur Obergrenze; 4) „Dauer unbekannt" als eigenen Wert filtern; 5) Leeres Ergebnis (z. B. unmögliche Kombination) anzeigen.
- **Erwartet / Kriterien:** Zähler, Paginierung und Sortierung korrekt; leeres Ergebnis vorhersehbar (keine Fehler). Arrangement-/Ausgabeattribute passen nur zum selben zutreffenden Arrangement/Ausgabe, nicht zu fremden Geschwistern. Ergebnisliste und Detailansicht behalten Such- und Filterzustand über Navigation.
- **Verfügbarkeit:** Basis-Suche Verfügbar — lokal prüfbar; Facetten/Kategorien/Tag-/Dauerräume nicht implementiert (WP-60a).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-027 — Suchzustand: Chips, gespeicherte Facetten, „Alle Filter anzeigen"
- **Zweck:** Entfernbare aktive Chips, Zurücksetzen, Zustandsbeibehaltung; benutzerindividuell gespeicherte bevorzugte Facetten; temporärer Vollzugang überschreibt keine Einstellungen; Ein-/Ausklappen deaktiviert keine Werte.
- **Anforderungen / WP:** AR-15; WP-60a (offen).
- **Voraussetzungen / Daten:** Zwei Archivar-Konten mit unterschiedlichen Facetten-Einstellungen.
- **Handlung:** 1) Mehrere Filter setzen, Chips anzeigen, einzeln entfernen, **Zurücksetzen**. 2) Ergebnisseite öffnen und zurückkehren: Zustand erhalten. 3) `Weitere Filter` aufklappen: bevorzugte Facetten des Kontos anzeigen; Einstellungen ändern (z. B. Dauer-Facette einblenden), Standard wiederherstellen. 4) `Alle Filter anzeigen` temporär öffnen; 5) Kontrollen einklappen, bei denen Werte gesetzt sind; 6) Mit zweitem Konto dasselbe anzeigen: andere bevorzugte Facetten.
- **Erwartet / Kriterien:** Chips entsprechen den aktiven Werten; Entfernen/Reset nur die jeweiligen Werte. Ein-/Ausklappen ändert nie den Wert der Filter. Temporärer „Alle Filter" überschreibt die gespeicherten Einstellungen nicht; Zurückstellen funktioniert. Einstellungen sind pro Konto persistent. Responsive Layout (Schmal/Weite), keine neuen Such-Subsysteme.
- **Verfügbarkeit:** Nicht implementiert (WP-60a).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## G — Mehrbewegungs-Hierarchien und Teilfreigabe

#### MA-028 — Werk-Hierarchie: Sammlung, Elternwerk, Sätze, gleichnamige Sätze
- **Zweck:** Sammlungen unabhängiger Werke werden von Elternkompositionen mit Sätzen/Teilen unterschieden (Messen, Suiten, Medleys); Sätze sind einzeln such- und exportierbar; gleichnamige Sätze bleiben getrennt; Zyklen und versehentliche Titel-Zusammenführung werden abgewiesen.
- **Anforderungen / WP:** CAT-05, CAT-06; WP-55 (synthetisch verifiziert).
- **Voraussetzungen / Daten:** „Deutsche Messe" als Elternwerk mit drei Sätzen, davon zwei mit identischem Sattitel; eine Sammlung unabhängiger Werke mit gleichem Werktitel wie ein Satz; eine relationale Zyklusversuch (A → B → A).
- **Handlung:** 1) Elternwerk mit Sätzen anlegen/verifizieren; Elternkontext und beabsichtigte Sätze-Reihenfolge anzeigen. 2) Satz über Suche direkt öffnen (Titel, inkl. gleichnamige). 3) Sammlungsmitgliedschaft eines Werks einsehen; getrennt von Elternbeziehung prüfen. 4) Zyklusversuch über Beziehungsanlage auslösen. 5) Vererbung: Sammlungs-Werte (Herausgeber, Ausgabe) auf Werke anzeigen, lokalen Override setzen; Herkunft (Provenance) prüfen.
- **Erwartet / Kriterien:** Satz und Elternwerk sind getrennte Identitäten; gleichnamige Sätze durch UUID/Reihenfolge unterscheidbar. Elternkontext und Sätze-Reihenfolge sichtbar. Zyklus abgewiesen. Vererbte Werte mit explizitem lokalen Override und nachvollziehbarer Provenance (Rezept pro Revision).
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert); manuelle Produktabnahme offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-029 — Teilfreigabe: Satz bestätigt, Elternwerk nicht
- **Zweck:** Ein bestätigter Satz bestätigt nicht das Elternwerk; eine vollständige Werk-Ausgabe begründet keine eigenständig bestätigten Satz-Editionen; korrekt bestätigte Sätze sind nutzbar, während der Rest sichtbar unvollständig bleibt.
- **Anforderungen / WP:** CAT-05, AR-21, AR-20; WP-54/55 (synthetisch verifiziert).
- **Voraussetzungen / Daten:** „Deutsche Messe": drei Sätze mit unabhängig geprüften Editionen über zwei publizierte Quellen; gemeinsame Seiten und Fortsetzungen; ein Satz nur zu 50 % bestätigt.
- **Handlung:** 1) Zwei Satzeditionen vollständig bestätigen, dritte nur teilweise (eine Region). 2) Elternwerkstatus prüfen: Satzbestätigung darf keine vollständige Werkedition automatisch bestätigen. 3) Bestätigten Einzel-Satz exportieren. 4) Unbestätigte Gesamtwerkedition exportieren versuchen: verweigert. 5) Eine unabhängig visuell geprüfte vollständige Werkedition bestätigen und auswählen; dies bestätigt nicht automatisch einzelne Satzeditionen. 6) Dritten Satz später vollständig prüfen und unabhängig bestätigen.
- **Erwartet / Kriterien:** Satz-Export zeigt exakte, geprüfte Reihenfolge. Bestätigung der vollständigen Werkedition und einzelner Satzeditionen ist unabhängig; keine automatische gegenseitige Freigabe. Neue Exporte verwenden nur die tatsächlich bestätigte gewählte Edition. Fortsetzungen und gemeinsame Seiten werden mit expliziter Reihenfolge wiedergegeben.
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert, inkl. `test_mass_content_sequences.py`); manuelle Produktabnahme offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-030 — Korrektur, Rückzug und Historie von Sammlungs-/Werksbelegen
- **Zweck:** Explizite, begründete Rücknahme und Ersetzung von Mitgliedschaften/Beziehungen; alte Belege bleiben als Historie; aktuelle Leseansichten schließen abgeschlossene Ereignisse aus.
- **Anforderungen / WP:** CAT-05, CAT-06; WP-55 (synthetisch verifiziert, `test_catalog_corrections.py`, Browser-Test in CI).
- **Voraussetzungen / Daten:** Werksammlung mit Mitgliedschaften; ein falscher Mitgliedschaftseintrag; ein abzuspeichernder Alternativ-Titel.
- **Handlung:** 1) Falsche Mitgliedschaft über Korrektur-Editor ersetzen (Grund + Revisionsgrenzschutz). 2) Doppelte/veraltete Ersetzung erneut einreichen ⇒ abgelehnt. 3) Ersetzung rückgängig machen (Rückzug); ursprüngliche Historie bleibt. 4) Werkdetail: aktuelle und beibehaltene Belege getrennt anzeigen. 5) GET-Anfrage muss nichts verändern.
- **Erwartet / Kriterien:** Atomare Ersetzung: schlägt die Ersetzungsprüfung fehl, wird der Rückzug zurückgerollt. Historie beibehalten (Alter Provenance-Beleg, beide Ereignisse sichtbar). Aktuelle Ansichten zeigen nur aktive Belege. CSRF-/Login-Schutz aktiv; Revisionsgrenzschutz verweigert veraltete Einreichungen.
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert, inkl. Browser-Nachweis in exakter CI); manuelle Produktabnahme offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## H — Instrumentenspezifische Buch-Positionen, Ausgaben und Präferenzen

#### MA-031 — Dasselbe Werk an unterschiedlichen Instrumenten-Buchpositionen
- **Zweck:** Ein Werk findet sich in mehreren Instrumenten-Büchern an unterschiedlichen Seiten/Koordinaten; Auswahl erfolgt über Werk-/Satz-Identität, nicht über Seitenzahlen; die exportierte Stimme stammt aus dem gewählten Instrumenten-Buch.
- **Anforderungen / WP:** AR-25, AR-20, CAT-01; WP-54/55 (synthetisch verifiziert, `test_full_instrumental_booklet.py`).
- **Voraussetzungen / Daten:** Aus MA-012/013: zwei Instrumentenversionen desselben Buchs; Werk Nr. 87 auf Seite 22 (Karte 3) in Buch A und Seite 19 (Karte 1) in Buch B; Fortsetzungen unterscheiden sich in der Seitenzahl.
- **Handlung:** 1) Werk 87 im Projekt/Export für beide Instrumente auswählen. 2) Matrix/Vorschau: Herkunft (welches Buch, welche Region) pro Zeile anzeigen lassen. 3) Export beider Versionen; Reihenfolge, Orientierung, Fortsetzungen vergleichen. 4) Falsche Zuordnung erzeugen (Werk 88 statt 87), prüfen dass die Prüfung dies auffängt.
- **Erwartet / Kriterien:** Identität über UUID und musikalische Zuordnung; Song-Nummer liefert ergänzenden Sammlungskontext, ist keine globale Werkidentität. Seitennummerngleichheit ist nie musikalische Identität. Pro Instrument: exakte geprüfte Edition mit Original-Kontext. Falsche Zuordnung muss bei Sichtprüfung korrigiert werden; die Anwendung kann musikalische Richtigkeit nicht allein aus Koordinaten garantieren.
- **Verfügbarkeit:** WP-54/55-Basis (synthetisch verifiziert); manuelle Produktabnahme offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-032 — Archiv-Präferenzen: setzen, ändern, nicht stillschweigend ersetzen
- **Zweck:** Eine Archiv-Präferenz pro Arrangement/Stimme (oder Inhalt-Edition); explizite Projekt-/Positionswahl schlägt die Präferenz; geänderte Präferenz ersetzt keine gefestigte Auswahl oder alten Export; betroffene Ausgaben werden als veraltet markiert.
- **Anforderungen / WP:** AR-17, AR-10, AS-05; WP-23a, WP-35 (verfügbar), WP-55 (Inhalt-Präferenz, synthetisch verifiziert).
- **Voraussetzungen / Daten:** Zwei bestätigte Versionen (alte/neue Ausgabe); ein Projekt mit expliziter Version in einer Position; bestehender Export, der die alte Version pinnt.
- **Handlung:** 1) Präferenz auf neue Version setzen; Projekt mit expliziter Auswahl prüfen (ändert sich nicht). 2) Projektzelle ohne explizite Auswahl: neue Präferenz wirkt. 3) Bestehenden Export erneut öffnen/laden: alte Bytes/Version bleiben. 4) Neue Generation aus aktuellem Projekt: neue Version. 5) Inkompatible/in Prüfung befindliche Präferenz setzen versuchen (abgelehnt). 6) Inhalt-Präferenz (WP-55): exakte Arrangement/Teil-Präferenz setzen/löschen, veraltete Revision wird abgelehnt, Historie bleibt.
- **Erwartet / Kriterien:** Präferenz wird nie zu stillschweigender Ersetzung. Explizite Auswahl gewinnt; ungelöste Mehrdeutigkeit ohne Präferenz wird als ungelöst gemeldet (keine ratende Auswahl). Veraltete Ausgaben sind gekennzeichnet, nicht überschrieben. Präferenz-Editor: Login/CSRF, Revisionsgrenzschutz, GET ohne Wirkung.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar (klassische Ausgaben); Inhalt-Editions-Präferenzen: WP-54/55-Basis (synthetisch verifiziert).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-033 — Ersetzungsregeln und nicht verfügbare Stimmen
- **Zweck:** Explizite Ersetzungsregeln (z. B. Posaune 3 → Posaune 2) mit Projekt-/Positions-/Global-Scope; niemals aus Instrument/Nummer allein raten; fehlende Stimme ⇒ Fehlnoten-Workflow, keine stille Substitution.
- **Anforderungen / WP:** AS-06, AS-05, CAT-03, GR-09; WP-35, WP-32 (verfügbar).
- **Voraussetzungen / Daten:** Regel Posaune 3 → Posaune 2 (global); eine Position mit Projekt-Regel Posaune 3 → Tenorhorn B; eine Stimme ohne jede Regel und ohne bestätigte PDF; ein Regelkreis A → B → A.
- **Handlung:** 1) Matrix mit Posaunist ohne Posaune 3-PDF: Substitution gemäß Regel anzeigen (Herkunft sichtbar). 2) Positionsregel schlägt Projekt-/Globalregel. 3) Kreis: anlegen ⇒ abgelehnt. 4) Fehlsituation ohne Regel: ungelöst/fehlend anzeigen; keine Substitution aus bloßer Nummer. 5) Explizit verfügbare Auswahl: Substitution wird nicht aktiv.
- **Erwartet / Kriterien:** Substitution nur für nicht verfügbare gewünschte Teile; tatsächlicher ersetzter Teil + Ursprung sichtbar; keine Zyklen; keine stille Fallback-Kette; explizite verfügbare Auswahl gewinnt immer (GR-10). Fehlt alles: Fehlnoten-Workflow (siehe MA-036).
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-034 — Falsche Region/Vererbung: unklare Beweise und Ersetzungs-Zuordnung
- **Zweck:** Unklare Region-/Beweiszusammenhänge (z. B. Region, die einem Satz zugeordnet wurde, aber zu einem anderen gehört) werden als Konflikt/ungeprüft behandelt; vererbte Metadaten verdecken lokale Overrides nicht; keine Vererbung über falsche Region.
- **Anforderungen / WP:** AR-21, CAT-06, SC-05; WP-55 (synthetisch), WP-56 (Editor).
- **Voraussetzungen / Daten:** Region aus Buchseite, die visuell zu Satz B gehört, aber auf Satz A gemappt wurde; Sammlung mit ererbtem Komponisten und einem Satz mit Override.
- **Handlung:** 1) Falsch gemappte Region in Prüfung zeigen: Konflikt/Hinweis, kein stilles Exportieren. 2) Korrektur: Region Satz B zuordnen (neue Revision); alte Bestätigung bleibt Historie. 3) Export mit korrigierter Region. 4) Vererbung prüfen: Override sichtbar, Herkunft unterscheidbar (Sammlung vs. lokal).
- **Erwartet / Kriterien:** Unbestätigte Region niemals in neuen Exporten. Revisionen: Änderung inaktiviert nur die betroffenen Bestätigungen. Vererbte Werte mit Provenance; Override schlägt ererbtes; Snapshot-Werte reproduzierbar.
- **Verfügbarkeit:** Revisionen/Vererbung: WP-54/55-Basis (synthetisch verifiziert); graphische Korrektur: nicht implementiert (WP-56).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## I — Projekte: gemeinsame Liste, Matrix, Vorprüfung, Mappen, Nachdrucke

#### MA-035 — Gemeinsame Stückliste: Nummerierung, Reserven, Ersetzen
- **Zweck:** Eine gemeinsame geordnete Liste je Projekt; automatische Nummerierung inkl. Reserve-Slots; Ersetzen erhält Positionsidentität/Nummer; keine persönlichen Listen.
- **Anforderungen / WP:** GR-07, PR-01–03, GR-12; WP-29, WP-30 (verfügbar).
- **Voraussetzungen / Daten:** Projekt „Marschbuch 2026" mit 8 Stücken, darunter dasselbe Arrangement zweimal und eine Reserve an Position 5; Teilnehmer aus MA-011.
- **Handlung:** 1) Stück aus Bibliothek hinzufügen (Live-Suche `ab`), konkretes Arrangement wählen. 2) Position 7 an Position 1 verschieben (Drag-and-Drop-Vorschau, speichern); Nummerierung prüfen. 3) Reserve am Ende hinzufügen und in Position 2 verschieben: Reserve verbraucht Nummer, liefert keine Notenseite; nachfolgendes Stück rückt. 4) Reserve füllen (bestehende Position behalten). 5) Arrangement an Position 4 ersetzen (bewusst bestätigen); zugehörige Overrides/Versionen werden neu geprüft (nicht automatisch fortgeführt). 6) Position entfernen; Nummern rücken auf, Historie bleibt.
- **Erwartet / Kriterien:** Alle Teilnehmenden sehen dieselbe Liste/Nummern. Verschieben 3 → 1 führt zu automatischer Umnummerierung; Reserven bleiben als Slots. Ersetzen erhält Nummer und Positions-ID. Inhaltsvorschau zeigt Nummern und Reserven; Zahlen nie auf Noten.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-036 — Matrix: Zuordnung, Prioritäten, Batch, Reset (Mathias/Sebi/Riccardo)
- **Zweck:** Matrix zeigt wirksame Stimme, Ausgabe, Notation/Stimmung und Herkunft; persönliche Positionsoverride > gespeichertes Projekt-Default; Batch-Edit und Reset; Konfliktprüfung bei veralteten Änderungen.
- **Anforderungen / WP:** AS-01–08, GR-10, PR-04, PR-07; WP-31, WP-33a–d, WP-32 (verfügbar).
- **Voraussetzungen / Daten:** Mathias (regelmäßig Posaune 1), Sebi (Posaune 2), Riccardo (Posaune 3); ABBA-Medley an mehreren Positionen; bestätigte Posaune-2-PDF mit Bass- und mit Violinschlüssel-Variante.
- **Handlung:** 1) Matrix öffnen: gespeicherte Defaults in Kopfzeilen, wirksame Stimme + Ausgabe-Herkunft pro Zelle. 2) Riccardo an ABBA-Medley + weiteren Stücken auf Posaune 2 setzen (bewusste Wahl der Bass-/Violinschlüssel-Variante). 3) Neuladen: Persistenz. 4) Mehrere Zellen eines Teilnehmenden batch-weise setzen; eine ungültige Position einschließen ⇒ klare Fehlerbehandlung, keine Teiländerung. 5) Eine Zelle zurücksetzen; andere Overrides bleiben (explizite Overrides überleben Default-Änderungen). 6) Parallel in zweiter Sitzung eine Zelle ändern und speichern ⇒ veraltete Speicherung der ersten Sitzung wird abgelehnt; **Projekt neu laden**, fremde Änderung prüfen, bewusst erneut speichern.
- **Erwartet / Kriterien:** Nur Riccardo geändert; andere Zellen/Masterdaten/RAW unverändert. Herkunft sichtbar (Default, Ensemble, persönliches Override, Substitution, fehlend). Reserven-Zeilen nicht zuordenbar. Abweichungen visuell hervorgehoben (nicht nur Farbe). Veraltete Schreibende werden abgelehnt (PR-07), keine stille Überschreibung. 100×50-Synthesematrix bleibt bedienbar (Performance-Beobachtung notieren).
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-037 — Teilnehmer, Gäste und Übernahme aktueller Defaults
- **Zweck:** Teilnehmerauswahl (Untermenge/alle/keine, Instrumentfilter); Gast ohne dauerhafte Mitgliederveränderung; später geänderte Stammdaten ändern keine bestehenden Projekt-Zuordnungen; explizite Übernahme aktueller Defaults.
- **Anforderungen / WP:** PR-04, CAT-02, AS-01; WP-31 (verfügbar).
- **Voraussetzungen / Daten:** Projekt mit 5 von 12 Mitgliedern; Gastmusiker mit gültiger Stimme; danach Stammdaten-Änderung (Mitglied wechselt reguläre Stimme).
- **Handlung:** 1) Teilnehmende über Auswahl/Filter setzen; alle/keine wählen. 2) Gast hinzufügen. 3) Stammdaten-Änderung durchführen; bestehendes Projekt prüfen. 4) Explizite Übernahme aktueller Defaults auslösen; bewusste persönliche Overrides bleiben, es sei denn, sie werden zurückgesetzt.
- **Erwartet / Kriterien:** Bestehende Projektzuordnung kopiert die reguläre Stimme bei Aufnahme; spätere Stammdaten-Änderungen wirken nicht automatisch. Gast bleibt projektbegrenzt. Übernahme ist eine explizite Aktion; Overrides bleiben erhalten, außer zurückgesetzt.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-038 — Vorprüfung: Fehlnoten, Platzhalter, blockierende Fehler
- **Zweck:** Vorprüfung zeigt gewählte Personen/Positionen, fehlende Teile, Substitutionen, ungesicherte Kandidaten, mehrdeutige Ausgaben, Layouthinweise; fehlende Noten erfordern explizite Bestätigung; ungültige Eingaben sind handlungsbezogene Fehler.
- **Anforderungen / WP:** EX-08, GR-09; WP-36a (verfügbar).
- **Voraussetzungen / Daten:** Projekt mit: fehlender bestätigter Posaune-3-PDF an einer Position, ungesichertem Kandidaten, mehrdeutiger Ausgabe, korrupter Eingabe-Datei, Reserve-Position.
- **Handlung:** 1) Personen/Positionen wählen, **Auswahl prüfen**. 2) Bericht gegen Matrix abgleichen (gleiche gewünschte/tatsächliche Stimmen). 3) Fehlende Zuordnung einzeln als fehlend mit Platzhalter bestätigen; **Prüfergebnis und Platzhalter bestätigen**. 4) Korrupte Datei: nicht als fehlende Note bestätigen lassen. 5) Projekt ändern, Vorprüfung erneut starten (alte Bestätigung ist ungültig).
- **Erwartet / Kriterien:** Bericht und Matrix stimmen überein. Fehlende ⇒ Warnung + Platzhaltersseite „Noten fehlen" an der Position; nie stille Auslassung, nie ungesicherter Ersatz. Blockierende Fehler müssen vor Generierung korrigiert werden; unleserliche Eingaben lassen sich nicht über die Fehlnoten-Bestätigung hinwegbestätigen. Reserven erhalten keine Notenseite. Änderungen erfordern neue Vorprüfung.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-039 — Vollmappen: ein PDF je Teilnehmer, identische Reihenfolge
- **Zweck:** Ein Lese-PDF je ausgewähltem Teilnehmer; identische gemeinsame Reihenfolge/Nummern; unterschiedliche Stimmen; Platzhalter; unveränderliche alte Artefakte.
- **Anforderungen / WP:** EX-01, EX-05, GR-07–09; WP-37a, WP-37b, WP-36b (verfügbar).
- **Voraussetzungen / Daten:** Aus MA-038 bestätigt; 2–3 Teilnehmer; optional Deckblatt; Reserve; eine fehlende (bestätigte) Note.
- **Handlung:** 1) Generierung beauftragen (Signatur-Autorisierung); Fortschritt im Auftrag beobachten. 2) Nach Abschluss alle Mappen herunterladen und öffnen. 3) Pro Mappe prüfen: gemeinsame Reihenfolge/Nummern, eigene Stimme, Platzhaltersseite, optionales Deckblatt (Name, Projekt, Stimme/Rolle — keine irreführende „alle Stücke" -Aussage). 4) Nummer nicht auf Notenseiten; nur im Inhaltsverzeichnis. 5) Projekt nachträglich ändern; alte Mappen erneut öffnen.
- **Erwartet / Kriterien:** Alle Mappen: identische Positionsreihenfolge/-Nummern, unterschiedliche Stimmen. Deckblatt optional; ohne Deckblatt beginnt das PDF mit dem Inhaltsverzeichnis (mehrseitig erlaubt). Fehlende ⇒ Platzhalter. Abbruch erzeugt kein „falsch vollständiges" Ergebnis. Alte Dateien unverändert (GR-15); neue Generation nutzt aktuelle Daten.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-040 — Auszüge, Nachdrucke und nur-Inhaltsverzeichnis
- **Zweck:** Einzelne Positionen × Personen als Auszug/Nachdruck, ohne Änderungen an der gemeinsamen Sammlung; ersetzende Nachdrucke behalten Position/Nummer; Inhaltsverzeichnis getrennt aktualisierbar.
- **Anforderungen / WP:** EX-02, EX-04, EX-06; WP-37c (verfügbar).
- **Voraussetzungen / Daten:** Projekt aus MA-039; Riccardo „hat sein ABBA-Medley (Posaune 2) verloren"; eine Position wurde ersetzt und muss unter derselben Nummer neu gedruckt werden.
- **Handlung:** 1) Aus MA-039/Matrix: Position + Riccardo wählen, Auszug erzeugen (ohne Deckblatt/Inhaltsverzeichnis per Voreinstellung). 2) Ersetzte Position als Nachdruck an derselben Stelle erzeugen. 3) Nur-Inhaltsverzeichnis des Projekts erzeugen. 4) Historische exakte Re-Ausgabe eines bereits generierten Exports wählen (früherer Snapshot). 5) Gemeinsame Liste/Nummering nach 1–4 prüfen (unverändert).
- **Erwartet / Kriterien:** Auszug verwendet dieselben wirksamen Zuordnungen wie die Vollmappe; keine Listenänderung. Nachdruck an gleicher Nummer; historische Ausgabe exakt (früherer Snapshot, keine aktuelle Substitution). Nur-Inhaltsverzeichnis ist ein eigenes Artefakt; Vollmappenregenerierung nicht nötig.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-041 — Exportbibliothek, veraltete Ausgaben, gezielte Regeneration
- **Zweck:** Einheitliche Lauf-/Artefaktliste mit Manifest und Downloads; Teilwechsel markiert betroffene Ausgaben als veraltet (alte Bytes unverändert); gezielte Regeneration einer Person.
- **Anforderungen / WP:** EX-10, GR-15; WP-39 (verfügbar).
- **Voraussetzungen / Daten:** Zwei abgeschlossene Generierungen desselben Projekts (vorher/nach Teiländerung).
- **Handlung:** 1) Exportbibliothek öffnen: Status, Manifest, Pfade je Person. 2) Teiländerung im Projekt vornehmen; betroffenen alten Export als veraltet markiert prüfen (Grund sichtbar). 3) Alte Mappe erneut herunterladen (Bytegleiche mit erstem Download). 4) Gezielte Regeneration nur für eine Person auslösen. 5) Ungenutzte/fehlgeschlagene Artefakte als vollständig dargestellt suchen (müssen nicht existieren).
- **Erwartet / Kriterien:** Veraltete Kennzeichnung nach relevanten Änderungen (Projekt, Katalog, Präferenzen); alte Ausgaben bleiben verfügbar. Gezielte Regeneration erfolgreich für eine Person; keine fehlgeschlagene/teilweise Artefakte als vollständig ausgestellt. Menschliche Namensgebung/Kollisionschutz; Batch-ZIP möglich; Druck ist für Download nicht erforderlich.
- **Verfügbarkeit:** Verfügbar — lokal prüfbar.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-042 — Projekt-Dauer und Geschätzte Gesamtdauer
- **Zweck:** Geschätzte Dauer aus wirksamen Arrangement-/Werk-Metadaten; wiederholte Positionen zählen, Reserven nicht; vollständige/bekannte/unbekannte Summen getrennt; keine erfundenen Werte.
- **Anforderungen / WP:** PR-07 (erweitert), CAT-08; WP-60a/b (Dauermetadaten offen); Grunddaten aktuell nicht implementiert.
- **Voraussetzungen / Daten:** Projekt mit bekannten Dauern (150 s, 905 s), einem Werk mit unbekannter Dauer, einem wiederholten Arrangement und einer Reserve.
- **Handlung:** 1) Dauer je Werk/Arrangement pflegen (siehe MA-025); 2) Projektansicht: geschätzte Gesamtdauer anzeigen lassen; 3) Wiederholtes Arrangement: zählt doppelt; Reserve: zählt nicht; 4) Einsetzen einer unbekannten Dauer: Kennzeichnung „mit unbekannter Dauer" statt 0; 5) MM:SS-Darstellung inkl. langer Werke prüfen.
- **Erwartet / Kriterien:** Drei Zustände unterscheidbar: vollständig bekannte Summe, teilweise bekannte Summe, Zählung mit unbekannten Dauern. Keine impliziten Ankündigungen/Pausen/Übergänge. Werte werden nie erfunden; unbekannt ≠ 0.
- **Verfügbarkeit:** Nicht implementiert (WP-60a, Kern gemäß DEC-16).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## J — Snapshots, Abbruch/Wiederherstellung, fehlende CLEAN-Kopien, Sicherung

#### MA-043 — Unveränderliche Snapshots: Änderung während der Generierung
- **Zweck:** Generierungen sind an einen validierten, unveränderlichen Snapshot gebunden (Projektrevision, Positionen, Personen, Stimmen, exakte Datei-Revisionen/Hashes, Layout); Änderungen während eines Laufs ändern den Lauf nicht; manipulierte/veraltete Authorisierungen werden abgelehnt.
- **Anforderungen / WP:** EX-09, EX-13, GR-15; WP-36b (verfügbar), WP-54/55 Inhalts-Pins (synthetisch verifiziert).
- **Voraussetzungen / Daten:** Bestätigtes Projekt mit Vorprüfung; ein Projekt mit gemischten Eingaben (eine Position als Ganzdatei, eine als Region-Edition).
- **Handlung:** 1) Vorprüfung bestätigen, Generierung beauftragen. 2) Während des Laufs eine Matrix-Zelle/Stimme ändern. 3) Lauf abschließen: Artefakt entspricht dem alten Stand (Snapshot), nicht der neuen. 4) Veraltete/abgeänderte Authorisierung erneut einreichen ⇒ abgelehnt. 5) Historischen Lauf erneut laden/wiedergeben (Replay): exakt dieselben Inhalte, auch nach nachträglichen Region-/Ausgabe-Änderungen.
- **Erwartet / Kriterien:** Alle Dokumente eines Laufs nutzen denselben Snapshot; Änderungen vor dem Enqueue invalidieren die Vorprüfung; Server lehnt Bypass/veraltete Bestätigungen ab; Pinned-Eingaben sind geschützt; Re-Ausgabe reproduziert exakt (inkl. Reihenfolge, Reserven, Platzhaltern, Orientierung).
- **Verfügbarkeit:** Verfügbar — lokal prüfbar; Inhalts-Region-Pins: WP-54/55-Basis (synthetisch verifiziert).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-044 — Aufgaben: Abbruch, Wiederherstellung, ein schwerer Worker
- **Zweck:** Persistente Warteschlange mit Fortschritt, sicherem Abbruch, Wiederherstellung nach Neustart; ein zeitintensiver Hintergrundjob gleichzeitig; Web bleibt reaktionsfähig; Druck wird nie automatisch wiederholt.
- **Anforderungen / WP:** OP-02, PT-05, UI-03; WP-05a–c (verfügbar); erster OCR-Auftrag WP-25 implementiert, Segmentierungsaufträge WP-56 offen.
- **Voraussetzungen / Daten:** Langer Indizierungs- bzw. Generierungsauftrag; simulierter Worker-Neustart während des Laufs.
- **Handlung:** 1) Zwei schwere Aufträge nacheinander anstoßen: zweiter bleibt wartend (kein paralleler schwerer Lauf). 2) Laufenden Auftrag **Abbrechen**: kooperativer Stopp, bereits abgeschlossene Teile bleiben. 3) Worker während eines Laufs neu starten (simuliert); nach Wiederherstellung: Fortschritt/Verbleib prüfen, keine doppelte Publikation. 4) Fehlerfall: klarer, sanitierter Fehler ohne Stacktrace in der Oberfläche. 5) Druckstatus nach unklarem Annahme-Timeout: Status „unbestimmt", keine automatische Wiederholung.
- **Erwartet / Kriterien:** Globale Single-Heavy-Job-Lease; abgelaufene/veraltete Versuche können keinen Zustand commiten. Fortschritt/Abbruch/Neuladen in der Auftrags-UI; Web bleibt bei langen Aufträgen reaktionsfähig. Keine halben/doppelten Publikationen; idempotente, stadienbasierte Operationen. Unbestimmte Druckannah ⇒ bewusstes erneutes Anstoßen nach Druckerprüfung.
- **Verfügbarkeit:** Teilweise implementiert: Indizierung, Generation und Ganzseiten-OCR sind prüfbar; Segmentierung und reale Druckannahme bleiben offene Pakete. OCR-Prozessmarker nach Unterbrechung verlangen ggf. Eigentumsprüfung statt automatischen Neustart.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-045 — Fehlende CLEAN-Kopie: Wiederherstellung, Konflikte, keine Blind-Ersetzung
- **Zweck:** Eine fehlende bestätigte CLEAN-Kopie wird nur an ihrem akzeptierten Pfad aus exakt verifizierten Quellen wiederhergestellt; besetzte Pfade oder fehlender Eigentumsnachweis erlauben keine Ersetzung; CLEAN darf die letzte überlebende historische Kopie bleiben.
- **Anforderungen / WP:** GR-02, OP-05, DEC-15 (Recoverability); WP-06p `restore_clean_copy` (synthetisch verifiziert, POSIX).
- **Voraussetzungen / Daten:** Bestätigte CLEAN-Publikation; dessen Datei wird (synthetisch) entfernt; Fall B: Ziel-Pfad wird zwischen der Akzeptanz und dem Lauf von einem anderen Prozess belegt.
- **Handlung:** 1) Fehlende Kopie erkennen (Bestätigung bleibt, Status „nicht verfügbar"). 2) Wiederherstellungsauftrag für die exakte Akzeptanz anstoßen; Worker wiederherstellt aus exakter, verifizierter Quelle (historische Publikation bzw. gepinnte RAW-Version). 3) SHA-256, Pfad und Beleg der Wiederherstellung prüfen; Bestätigung/Revision bleibt gepinnt. 4) Fall B: belegter Pfad ⇒ Auftrag schlägt fehl, keine Ersetzung, Originalbeleg bleibt. 5) RAW-Vorgabe fehlt: Wiederherstellung aus RAW nicht möglich, klarer Hinweis; keine erfundenen Bytes.
- **Erwartet / Kriterien:** Wiederherstellung nur über geprüfte, exakte Quellversion; physikalisch unabhängige Zwischenkopie; no-clobber-Publikation mit beständigem Intent. Besetzter/unklarer Pfad ⇒ blockiert, nie Blind-Ersetzung. Historie/Bestätigungen bleiben geschützt. (Prozess-/Neustart-Evidenz; physischer Stromausfall = separates Gate, MA-047.)
- **Verfügbarkeit:** Verfügbar — lokal prüfbar (synthetische Wurzeln, Worker); physische Stromausfall-/NAS-Abnahme: MA-047.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-046 — Sicherung und Wiederherstellung: konsistent, isoliert, verifiziert
- **Zweck:** DB + CLEAN/PROCESSED + Konfiguration/Secrets werden konsistent gesichert; Wiederherstellung in isolierter Umgebung mit Hash-/Zuordnungsprüfung; Manifest ohne tatsächliche Dateien wird abgelehnt; RAW wird nicht in die App-Sicherung übernommen (eigene NAS-Sicherung).
- **Anforderungen / WP:** OP-05, OP-08; WP-47a (Schnittstelle verfügbar), WP-47b (vollständig, zukünftig); physisches Sicherungsziel: eigenGate des Inhabers.
- **Voraussetzungen / Daten:** Vollständiger synthetischer Workflow (Indexierung → Freigabe → Projekt → Export); anschließend geänderte Stammdaten.
- **Handlung:** 1) Konsistente Sicherung anstoßen (Quiesce/Schreibbarriere). 2) In isolierte Umgebung wiederherstellen; DB und tatsächliche Dateien gemeinsam prüfen (Hashes, Zuordnungen, Manifest). 3) Sicherung mit Manifest, aber fehlenden Dateien anstoßen ⇒ abgelehnt. 4) Gezielte Wiederherstellung eines einzelnen Exports/Artefakts prüfen. 5) Live-Archiv nach Sicherung/Wiederherstellung prüfen (unverändert). 6) Rollback-Grenzen prüfen: keine Downgrade-Autorisierung nach Schreiboperationen neuer Schemata / wiederverwendete zurückgezogene Positionen.
- **Erwartet / Kriterien:** Wiederherstellung reproduziert DB + Dateien zusammen (keine Manifest-Ohne-Dateien). Live-RAW/CLEAN nicht überschrieben. Referenzierte Archivversionen bleiben geschützt; Historische Ausgaben bleiben verfügbar. Verlustrisiko nach Sicherung (Daten zwischen Sicherung und Störung) wird im Runbook erklärt.
- **Verfügbarkeit:** Teilweise: Grund-Sicherung/Restore-Befehle verfügbar — lokal prüfbar (synthetisch); vollständige Retention/Hyper-Backup-Integration: nicht implementiert (WP-47b); physisches Ziel: eigenes Inhaber-Gate.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## K — Physische Abnahme: DS224+, echte Drucker, Windows (eigene Gates)

> Alle Fälle dieses Abschnitts erfordern **genehmigten Zugriff auf die reale Umgebung** (DS224+, genehmigte Drucker, Windows-Arbeitsplatz). Synthetische/mocked CI-Evidenz ersetzt sie nicht. Es gelten die Voraussetzungen des jeweiligen Falls; Installation und Drucker-Fähigkeitsermittlung benötigen nicht den Abschluss aller späteren Produktpakete. Standard sind genehmigte synthetische Testdaten. Reale Vereinsdaten nur für separat genehmigte private Realtests.

#### MA-047 — DSM/DS224+-Installation, Rechte, Stromausfall (synthetisches Testvolumen)
- **Zweck:** Reale Installation auf DS224+ (Linux amd64, Docker Compose): Service-Konto mit numerischem UID/GID, separate synthetische Wurzeln, read-only RAW an DSM- und Mount-Grenze, SQLite-WAL lokal, Neustart-/Stromausfallverhalten.
- **Anforderungen / WP:** OP-01–03, GR-01, OP-05; WP-22, WP-07/09, WP-50 (Sicherheit), WP-52 (Last).
- **Voraussetzungen / Daten:** Genehmigter DS224+ (RAM/DSM-Version vorab dokumentiert), synthetisches Testvolumen (keine echten Daten), Compose-Stack, Reverse-Proxy/TLS.
- **Handlung:** 1) Installation gemäß Runbook (docs/INSTALL.md); Start ohne echte Daten. 2) Service-Rechte/ACL verifizieren; Schreib-/Umbenenn-/Löschversuche in RAW an DSM- und Mount-Grenze ausführen (müssen fehlschlagen). 3) Web-/Worker-Gesundheit, Moduswechsel, SQLite-WAL/Busy-Timeout prüfen. 4) Geplante Neustarts der Container; 5) Stromausfall-Simulation (sofern genehmigt) mit anschließender Inventar-/Integritätsprüfung; 6) RAM/CPU/IO während eines Indexier-/Generierungslaufs messen.
- **Erwartet / Kriterien:** Keine privilegierten Container; Non-Root; RAW-Schutz an beiden Schichten nachweisbar. Kein OOM/DB-Lock-Fehlschlag im vereinbarten Arbeitslastfenster (sonst Limitierung dokumentieren). Abbruch/Neustart: keine halben Publikationen, keine verlorenen historischen Inhalte. Messwerte in PROGRESS/RELEASES dokumentiert.
- **Verfügbarkeit:** Hardware-/physische Abnahme (eigenes Gate).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-048 — Reale Drucker-Fähigkeiten (Spike) und Adapter
- **Zweck:** Reale Drucker werden ermittelt (IPP/CUPS, Formate, Ränder, Medienwechsel, Status); Adapter nutzt internes Netzwerk-Allowlist; `PRINT_ENABLED` default aus; keine Annahmen über DSM-Druckdienste.
- **Anforderungen / WP:** PT-03, PT-04, OP-03; WP-44a (Spike), WP-44b (Adapter — beide noch offen).
- **Voraussetzungen / Daten:** Genehmigte interne Drucker; sichere Testblätter; `PRINT_ENABLED=0` während der Erkennung.
- **Handlung:** 1) Drucker in der Umgebung dokumentieren (Modell, Netzwerk, Formate, Doppel-Seitigkeit, Custom-Media). 2) Adapter-Fähigkeiten in der UI anzeigen lassen (Medien/Walzen/Ränder). 3) Externe/ungeregelte Endpunkte: Allowlist-Verweigerung prüfen. 4) `PRINT_ENABLED` umschalten (nach Freigabe).
- **Erwartet / Kriterien:** Tatsächliche Fähigkeiten und gewählter Adapter (oder exakter Blocker) dokumentiert. Keine Produktionssubmission ohne Freigabe. UI zeigt Medien/Status korrekt; keine stille Annahme über Medienwechsel.
- **Verfügbarkeit:** Nicht implementiert (WP-44a/b) + Hardware-Gate.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-049 — Echter Druck: A4/A3, Reihenfolge, Duplex, Status, kein Auto-Retry
- **Zweck:** Echte Druckaufträge aller Ausgabetyppen (Direktnoten, Auszüge, Vollmappen, nur-Inhaltsverzeichnis): korrekte Blattformate, Seitenreihenfolge bei gemischten Formaten, Duplex-Konfiguration, Job-ID/Status, unklare Annahme ⇒ kein automatisches Wiederholen.
- **Anforderungen / WP:** PT-01–05, GR-11, OP-02; WP-45 (noch offen); physische Abnahme eigenes Gate.
- **Voraussetzungen / Daten:** Aus MA-039/040 generierte PDFs; Stücke mit 1, 3, 5 A4-Seiten; ein natives A3; Marschbuch 170×120 mm (falls Medium unterstützt); Drucker mit und ohne A3.
- **Handlung:** 1) Pro Fall Vorschau + Kopienzahl, dann drucken. 2) Papier ausmessen (A3/A4/Toleranz), Seitenreihenfolge/-anzahl prüfen (PT-01-Tabelle). 3) Duplex (lange/kurze Kante) prüfen; Seiten links/rechts korrekt. 4) A3-Drucker: natives A3 ganzzu bleiben; A4-Drucker: Fallback-Vorschau + explizite Bestätigung (kein stilles Schrumpfen). 5) Drucker aussetzen/Zeitüberschreitung während des Jobs: Status „unbestimmt" anzeigen; bewusst erneutes Anstoßen nach Druckerprüfung. 6) Gemischte Medien: fortlaufende Blöcke + Warnung, falls Misch-Job unzuverlässig.
- **Erwartet / Kriterien:** Keine Aufteilung nativer A3; keine Kreuzpaarung über Stückgrenzen; keine Zahlen auf Noten; Reihenfolge wie im Manifest. Fallback erfordert explizite Bestätigung; LesepDF unverändert. Job-ID/Status sichtbar; niemals automatische Wiederholung nach unklarer Annahme.
- **Verfügbarkeit:** Nicht implementiert (WP-45/46) + Hardware-Gate.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-050 — Marschbuch physisch: 170 × 120 mm, Bindung, Füllseiten, Heftmodus
- **Zweck:** Echte Marschbuch-Druckabnahme: exakte Maße, Bindungsgeometrie (gerade/ungerade pro letzter Seite), Füllseiten, Schnitte-/Falt-Modi (Cut-and-Stack, ggf. gefaltete Hefte), keine Überlagerung/Zuschnitte.
- **Anforderungen / WP:** SC-03, PT-06–10, EX-14; WP-42, WP-57 (noch offen); physisch eigenes Gate.
- **Voraussetzungen / Daten:** Marschbuch-Projekt (A5-Buch + A4-Stücke + natives A3); Drucker mit Custom-Media 170 × 120 mm bzw. genehmigtes alternatives Medium; Schere/Lochring für Prüfung.
- **Handlung:** 1) Vorschau: logische Seiten, Blätter, Vorder-/Rückseite, Bindungsränder, Füllseiten, Schnitthilfen prüfen. 2) Einfach- und Duplex-Job drucken; 3) Maße/Ränder ausmessen; Bindungsseite (alle vier Kanten testen) prüfen; 4) Füllseiten ein/aus: Seitenpaarität und Verschwendung; 5) A5-Buch-Sequenz im Heft: mehrere indizierte Werke pro A5-Seite bleiben lesbar, keine Einzelauswahl erforderlich.
- **Erwartet / Kriterien:** Exakte Maße in Toleranz; maximale proportionale Anpassung ohne Verzerrung; gerades/ungerades Bindungsmaß pro letzter Seite (unabhängig von Quellen-Seitenzahlen); Füllseiten deterministisch (Startseite, Umseit-Vermeidung); keine Überlagerung/Zuschnitte (unsichere Schränke können nicht stillschweigend Inhalt beschneiden); Manifest enthält Vorlage/Modus/Füllseiten/Warnungen.
- **Verfügbarkeit:** Nicht implementiert (WP-42/57) + Hardware-Gate.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-051 — Scanaufbereitung physische Qualitätsabnahme
- **Zweck:** Reale Scans (genehmigte, repräsentative, private): Schräglage-Entfernung, Rauschen/Schatten, Zuschnitt; Notenzeichen/Verzierungen/Tempo/Händisches bleiben erhalten; Derivate sind separate, freizugebende Ausgaben.
- **Anforderungen / WP:** SC-01–03, AR-23; WP-40a–c, WP-41, WP-40f (alle noch offen); private reale Messung eigenes Gate.
- **Voraussetzungen / Daten:** Genehmigte reale Scans auf NAS (nie im Repository/CI); Vorher/Nachher-Vergleich; Parameterprofile.
- **Handlung:** 1) Pro Stufe Vorher/Nachher-Vorschau; 2) Schräge Seite: Winkelkorrektur in Toleranz, unsichere Winkel mit Warnung; 3) Randnotensatz: Zuschnitt konservativ, Auslassung möglich, keine Verzerrung; 4) Freigabe des Derivats als bevorzugte Edition; 5) Geschwindigkeit/Speicher auf NAS messen; 6) Aggregierte Ergebnisse dokumentieren (nur zusammengefasst, keine Rohdaten).
- **Erwartet / Kriterien:** Originalbytes (RAW/CLEAN) unverändert; Derivat in PROCESSED mit Quelle/Einstellungen/Algorithmusversion/Hash. Keine destruktiven Standardfilter; unsichere Zuschnitte/Schrägen warnen. Archivar-Acceptance oder explizite Grenzen dokumentiert; synthetische Tests werden nicht als reale Scanvalidierung ausgegeben.
- **Verfügbarkeit:** Nicht implementiert (WP-40a–c/41/40f) + privates reales Gate.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-052 — OCR-Qualität an realen Beständen (privat)
- **Zweck:** Reale OCR-Messung (genehmigte Scans): Region-/Schwellenwert-Verhalten, Sprache, Threads, Speicher, Timeouts; bekannte Fehlschläge dokumentiert; keine universelle Genauigkeitsaussage.
- **Anforderungen / WP:** AR-08, OP-02; WP-28 (noch offen); OCR selbst WP-24/25.
- **Voraussetzungen / Daten:** Genehmigte, repräsentative reale Scans (privat, nie in Repository/CI); Messprotokoll.
- **Handlung:** 1) Nach WP-24/25-Implentierung: OCR auf repräsentativem Satz ausführen (Kopfzeilen, Fortsetzungen, mehr Titel pro Seite). 2) Ressourcen messen (Speicher, Dauer, Threads) und Grenzen (Timeouts, Seitenbegrenzung) auf DS224+ verifizieren. 3) Fehlschläge (Sprachpack, unlesbare Region) protokollieren. 4) Standardwerte anpassen; Ergebnisse in PROGRESS dokumentieren.
- **Erwartet / Kriterien:** Ergebnisse + bekannte Fehlschläge dokumentiert; Web bleibt reaktionsfähig (ein schwerer Worker); keine echten Scans in Repository/CI/externen Diensten; keine universelle Genauigkeitsaussage.
- **Verfügbarkeit:** Blockiert für reale Abnahme: erster Ganzseiten-OCR-Inkrement ist implementiert; repräsentative Qualitäts-/DS224+-Messung WP-28 erfordert gesonderte Autorisierung. Vollständige Regions-/Mehrwerkanalyse bleibt offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-053 — Windows-Edition: Installation, lokale Verzeichnisse, Lesezugriff auf Quellen
- **Zweck:** Einzlarbeitsplatz-Windows-Installation: Executable + Shortcut, gebundenes Laufzeitumgebung, lokale Archive-/Daten-/Exportverzeichnisse wählbar; Start/Stopp vom App verwaltet; kein Docker/Python/OCR-Setup durch Endanwender; Windows-Schreibpfade erst nach DEC-15-Abnahme.
- **Anforderungen / WP:** OP-07, DEC-15; WP-06p (gemeinsame Basis verifiziert; native Windows-Schreibzugänge deaktiviert), Endpackaging zukünftig.
- **Voraussetzungen / Daten:** Windows-Arbeitsplatz; Installer-Kandidat; lokale synthetische Verzeichnisse; read-only Quellordner mit dedizierter Nicht-Administrator-Identität.
- **Handlung:** 1) Installation und Start (Shortcut); Verzeichnisse in den Einstellungen wählen. 2) Vollständigen Workflow mit lokalen Daten: Indizieren → Prüfen → Projekt → Export (synthetisch). 3) Start-/Stopp-Zyklen; SQLite-Isolierung/Restore; 4) Reparse-/Symlink-Flucht an synthetischen Ordnern (muss abgewiesen werden); 5) Schreibversuche in Quellordner (read-only NTFS) ⇒ verweigert; 6) Debug-/Deploy-Modus wie MA-002.
- **Erwartet / Kriterien:** Gemeinsame UI/Geschäftslogik/Data-Modell mit Serverausgabe identisch. Isolierte sichere Plattform-Dateioperationen; vertrauenswürdige Ausführungspfade; Reparse-/Symlink-Flucht und Kollisionen abgelehnt; Original unverändert. Native Windows-Schreibveröffentlichung bleibt deaktiviert, bis die DEC-15-Abnahme bestanden ist; keine installierten Dienste/Endanwender-Setup.
- **Verfügbarkeit:** Teilweise: gemeinsame Basis + Read-only Quellzugriff synthetisch verifiziert (WP-06p); native Windows-Schreibzugänge/Endpackaging: nicht verfügbar (eigenes Gate).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-054 — Reale Migration/Erstinbetriebnahme auf dem Archiv (genehmigt)
- **Zweck:** Geplante, genehmigte erste Indizierung der echten Bestände: Backup vorher, Inventar vor/nachher, Prüfung des echten Umfangs (Anzahl, Größe), Fehlerbehandlung realer Dateien; keine unsicheren Massenoperationen.
- **Anforderungen / WP:** OP-05, OP-06, AR-01, AR-04, GR-01; WP-15/22/47a; eigenGate des Inhabers.
- **Voraussetzungen / Daten:** Genehmigter Zugriff; vollständige Sicherung (MA-046) direkt vorher; RAW-Inventar (Pfad+Hash) dokumentiert.
- **Handlung:** 1) Nach Sicherungsbestätigung: Indizierung des echten Archivs (in Stufen nach Ordner). 2) Fortschritt/Abbruch auf echtem Umfang beobachten. 3) Fehler/unklare Dateien (defekt, schreibgeschützt, exotische Namen) protokollieren. 4) Prüfwarteschlange: echte Stichprobe vollständig visuell prüfen. 5) RAW-Inventar nachher abgleichen. 6) Status-/Fehlertexte auf deutsche Nutzertauglichkeit prüfen.
- **Erwartet / Kriterien:** RAW bleibt bitgenau unverändert. Keine automatische Massenfreigabe; echte Dateien durchlaufen dieselben Prüfungsschleifen. Alle Fehler sind handlungsbezogen (keine Stacktraces). Messwerte (Dauer, Speicher) dokumentiert. Bei Problemen: Auftragsabbbruch, keine unvollständigen Publikationen.
- **Verfügbarkeit:** Hardware-/physische Abnahme (eigenes Gate).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-055 — Physische Archivorte, Bestandsberichte (sekundär)
- **Zweck:** Konfigurierbare, durchsuchbare Lagerort-Hierarchie (Gebäude/Raum/Schrank/Regal/Fach/Mappe/Kiste); physische und digitale Verfügbarkeit unabhängig; Inventarberichte (vollständig, Orte, fehlende/defekte Teile, fehlende digitale Kopien, digitale Unvollständigkeit, Erwerbungshistorie).
- **Anforderungen / WP:** CAT-07; WP-58 (noch offen, sekundär).
- **Voraussetzungen / Daten:** Lagerortstruktur des Vereins; Werke mit physischer Verfügbarkeit (teilweise fehlend/defekt) und digitaler Verfügbarkeit unabhängig.
- **Handlung:** 1) Hierarchie anlegen, Werke/Sätze zuordnen; 2) Suche über Orte; 3) Verfügbarkeit physisch/digital getrennt setzen; 4) Alle Berichte erzeugen/drucken/exportieren.
- **Erwartet / Kriterien:** Orte durchsuchbar und konfigurierbar; Unabhängigkeit der Verfügbarkeiten (physisch vorhanden ≠ digital vorhanden); Berichte vollständig und exportierbar; keine Verletzung von Kernarbeitsabläufen (Leihe ist WP-61e, separater).
- **Verfügbarkeit:** Nicht implementiert (WP-58, sekundär).
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-056 — Endabnahme: kompletter privater Workflow auf dem NAS
- **Zweck:** Gesamtabnahme: Indexierung → Prüfung → Projekt → Matrix → Vorprüfung → Vollmappen/Auszüge → Marschbuch → Druck (alle Ausgabetyppen) auf genehmigtem NAS mit realen Druckern; Blocker und tatsächlich umgesetzter Umfang dokumentiert; Freigabe-Empfehlung.
- **Anforderungen / WP:** Alle Kern-IDs; WP-53 (Abnahmepaket, zukünftig).
- **Voraussetzungen / Daten:** Anwendbare Kernprüfungen aus MA-047–MA-054 abgeschlossen; genehmigte reale (repräsentative) Daten; Drucker verfügbar. Separate Windows-Abnahme und sekundäre Lagerortverwaltung sind keine pauschalen NAS-Kern-Voraussetzungen.
- **Handlung:** 1) Vollständigen Workflow durchlaufen (einschließlich Fehlpfade: Fehlende Noten, Konflikt, Abbruch, Wiederherstellung). 2) Alle Output-Arten auf reale Drucker drucken. 3) Sicherung/Wiederherstellung einmal live üben. 4) Blocker, Grenzen, fehlende optionale Funktionen aufzeichnen. 5) Abnahmeprotokoll + Release-Empfehlung (Version, Commit/PR/Tag, Rollbackpunkt).
- **Erwartet / Kriterien:** Alle erforderlichen Kern-Gates nachgewiesen oder in einer separat genehmigten begrenzten Freigabe explizit ausgeschlossen; optionale WP-43 kein Blocker. Keine Extrapolation aus Mocks; lokale Erfolg ≠ NAS/Physische Abnahme; CI-Erfolg ≠ manuelle Abnahme.
- **Verfügbarkeit:** Hardware-/physische Abnahme (eigenes Gate); hängt von allen vorangehenden Kern-WPs ab.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

#### MA-057 — Windows × NAS: gemeinsame Daten, getrennte Abnahme
- **Zweck:** Windows-Edition und Serverausgabe teilen UI/Datenmodell, aber die Abnahme bleibt getrennt: Windows-Pakete/lokale Ablage (MA-053) und NAS/Physisch (MA-047–MA-056) werden unabhängig signiert; kein gegenseitiges Ersetzen der Nachweise.
- **Anforderungen / WP:** OP-07, DEC-15; WP-06p, WP-53.
- **Voraussetzungen / Daten:** Beide Umgebungen in Abnahmefähigkeit.
- **Handlung:** 1) Denselben Workflow auf beiden Plattformen mit identischen synthetischen Daten durchführen. 2) Ergebnisse vergleichen (Zuordnung, Exporte, Manifeste). 3) Abnahmestatus getrennt dokumentieren.
- **Erwartet / Kriterien:** Identische Geschäftslogik für gemeinsam verfügbare Funktionen; plattformspezifische Grenzen (z. B. Windows-Schreibzugänge deaktiviert) explizit benannt. Schreibende Windows-Workflows erst nach deren eigenem Gate durchführen; eine NAS-Abnahme ersetzt dieses Gate nicht.
- **Verfügbarkeit:** Teilweise: gemeinsame Basis synthetisch verifiziert; beide physischen Gates offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** —

## L — Ergänzende Alltagsszenarien

#### MA-058 — Unicode, Aliase, Bibliotheksnavigation und optionale Metadaten
- **Zweck:** Sonderzeichen, alternative Titel und fehlende Angaben verhindern keine normale Nutzung; die Rückkehr aus einem Detail erhält den Suchzustand.
- **Anforderungen / WP:** AR-15, CAT-08, UI-03; WP-21, WP-60a.
- **Voraussetzungen / Daten:** Titel mit Umlauten, Akzenten und Unicode-Zusammensetzungsvarianten; Alias; Komponist und Arrangeur; zwei gleichnamige Werke; ein Werk ohne optionale Metadaten.
- **Handlung:** 1) Titel, Alias und Komponist suchen; später auch Arrangeur, Verlag und Kennung. 2) Detail öffnen und zur gefilterten Liste zurückkehren. 3) Nach Titel, Komponist und später Dauer sortieren, Seiten wechseln und Trefferzahl prüfen. 4) Werk ohne optionale Angaben archivieren und bestätigen. 5) Vollständigkeit sowie tatsächlich verfügbare Instrument-/Notations-/Transpositionsfilter kombinieren; nicht implementierte Filter dürfen nicht vorgetäuscht werden.
- **Erwartet / Kriterien:** Normalisierte Suchvarianten finden das richtige Werk ohne Identitäten zu verschmelzen; aktive Filter und Pagination bleiben nachvollziehbar. Unbekannte Angaben bleiben unbekannt. Ein Arrangement mit Instrument A und ein anderes mit Notation B darf nicht fälschlich als gemeinsamer Treffer A+B gelten. Fehlende optionale Metadaten blockieren keine Freigabe.
- **Verfügbarkeit:** Teilweise implementiert: Basis-Titel-/Aliassuche und Archivierung verfügbar; zusätzliche Metadaten, Facetten und konfigurierbarer Suchzustand WP-60a offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** — · **Notizen:** —

#### MA-059 — OCR-Qualitätsreihe mit unterschiedlichen Druckbildern
- **Zweck:** Praktische Grenzen statt unbelegter Genauigkeitsversprechen ermitteln.
- **Anforderungen / WP:** AR-08–12, SC-06; WP-24/26/28.
- **Voraussetzungen / Daten:** Synthetische Überschriften in verschiedenen Schriftarten, klare digitale PDF, hoch-/niedrigauflösende Scans, schiefe Seiten, blasse Schrift und Schatten; `Pos. 2`, `Posaune II`, `2. Trombone`, `Trb. 2`, `B. Bass`; mehrere Titel auf einer Seite, irreführender Dateiname.
- **Handlung:** 1) Jede Datei ausdrücklich per OCR analysieren. 2) Erkannte Texte, Methoden, Konfidenz und Unsicherheit mit sichtbarer Quelle vergleichen. 3) Falschen Vorschlag korrigieren oder ablehnen. 4) Mehrere Titel und gedruckte Komponisten-/Verlagsangaben separat protokollieren; fehlende automatische Zuordnung nicht als korrekte Erkennung werten.
- **Erwartet / Kriterien:** Jeder Fehler bleibt nachvollziehbar und korrigierbar; unbekannte/zweideutige Instrumente werden nicht musikalisch freigegeben. Qualität pro Dokumentklasse und benötigte Korrekturen notieren. Mehrwerktitel-/Regionsvorschläge sind eigener offener Umfang; echte Vereinsnoten nur nach separater privater Autorisierung in MA-052.
- **Verfügbarkeit:** Teilweise implementiert: Ganzseiten-OCR/Textvorschläge verfügbar; vollständige musikalische Erkennungsziele, Bildauszüge und Mehrwerk-/Regionsworkflow offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** — · **Notizen:** —

#### MA-060 — Fehlende Buchseite, zusätzliche Stimme und korrigierte Ausgabe
- **Zweck:** Ein lückenhafter Scan oder abweichendes Arrangement wird nicht stillschweigend als vollständig behandelt.
- **Anforderungen / WP:** AR-14, AR-16, AR-17, AR-25, CAT-05; WP-21/23/55/56.
- **Voraussetzungen / Daten:** Buch mit einer fehlenden physischen Seite; anderer Scan mit vertauschten Seiten; Arrangement mit zusätzlichem Instrument; historische und korrigierte bestätigte Ausgabe.
- **Handlung:** 1) Quelle und Fortsetzungen visuell kontrollieren; fehlende Seite dokumentieren. 2) Vertauschte Reihenfolge im späteren Editor korrigieren, Original unverändert lassen. 3) Zusätzliche Stimme in den Arrangement-Erwartungen pflegen. 4) Korrigierte Ausgabe unabhängig prüfen und bevorzugen. 5) Historischen Export erneut öffnen und neue Ausgabe erzeugen.
- **Erwartet / Kriterien:** Fehlender Inhalt wird nicht erfunden oder aus einem anderen Instrument übernommen. Vollständigkeit richtet sich nach passenden Erwartungen; neue Präferenz ändert keine historischen Pins. Reihenfolgekorrektur erzeugt nachvollziehbare neue Revisionen.
- **Verfügbarkeit:** Teilweise implementiert: Erwartungen, klassische Editionspräferenzen und Historie verfügbar; grafische Buchkorrektur WP-56 offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** — · **Notizen:** —

#### MA-061 — Gleichzeitige Archivkorrektur und versehentlich falsche Region
- **Zweck:** Zwei authentifizierte Personen verlieren keine Änderungen durch stille Überschreibung; falsche Region lässt sich vor Freigabe revidieren.
- **Anforderungen / WP:** AR-13, AR-21, SC-05, CAT-06; WP-20/54/55/56.
- **Voraussetzungen / Daten:** Zwei getrennte Konten/Sitzungen, gleicher Prüfentwurf bzw. Regionsvorschlag; eine bewusst falsch gewählte Region.
- **Handlung:** 1) In beiden Sitzungen gleichen Stand öffnen. 2) In Sitzung A korrigieren und speichern. 3) Alten Stand aus B speichern versuchen, Konflikt prüfen und neu laden. 4) Falsche unbestätigte Region verschieben/vergrößern, teilen/zusammenlegen, Reihenfolge ändern und Ergebnis vorschauen. 5) Inspektionsstatus nach relevanter Änderung prüfen; frühere bestätigte Revision separat öffnen.
- **Erwartet / Kriterien:** Veraltete Speicherung wird abgewiesen, fremde Korrektur bleibt erhalten. Geänderte relevante Zuordnung/Geometrie braucht neue Sichtprüfung; keine automatische Freigabe. Frühere bestätigte Revision und historische Ausgabe bleiben erhalten.
- **Verfügbarkeit:** Teilweise implementiert: Revisions-/Konfliktschutz verfügbar; grafische Regionsbearbeitung WP-56 offen.
- **Manueller Status:** nicht ausgeführt · **Tatsächliches Ergebnis:** — · **Defekt:** — · **Notizen:** —

## M — Abdeckungsübersicht

| Abschnitt | Szenario-Gruppe | Fälle |
| --- | --- | --- |
| A | Umgebung, Zugang, RAW-Schutz, Modus | MA-001 – MA-003 |
| B | Normaler Archivfluss (Indexierung, Prüfung, Stapel, Suche, Download, Änderungen) | MA-004 – MA-011 |
| C | 125-Stücke-A5-Buch (ohne/mit Index, A4/A3, einfach/doppelseitig, Blattfüllung, Marschbuch) | MA-012 – MA-015 |
| D | Zusammengesetzte Scans (Regionen, Fortsetzungen, natives A3, Mischformat, Leerseiten, Rotation, Doppelungen, vollständige Ablehnung, große PDF/leere Sammlung) | MA-016 – MA-020 |
| E | OCR/Textschicht/Unsicherheit (Anstoß, Beweise, Konflikte, Neuanalyse) | MA-021 – MA-024 |
| F | Metadaten, Klassifikationen, Dauer, Facettensuche, Chips/Einstellungen | MA-025 – MA-027 |
| G | Mehrbewegungs-Hierarchie, Teilfreigabe, Korrektur/Rückzug | MA-028 – MA-030 |
| H | Instrumentenspezifische Buchpositionen, Ausgaben, Präferenzen, Ersetzungen, falsche Region/Vererbung | MA-031 – MA-034 |
| I | Projekte: gemeinsame Liste/Reserven, Matrix, Vorprüfung, Vollmappen, Auszüge/Nachdruck, Exportbibliothek, Dauer | MA-035 – MA-042 |
| J | Snapshots, Abbruch/Wiederherstellung, fehlende CLEAN, Sicherung | MA-043 – MA-046 |
| K | Physisch: DS224+, Drucker, Marschbuch, Scanaufbereitung, OCR-Real, Windows, Reale Migration, Lagerorte, Endabnahme | MA-047 – MA-057 |
| L | Unicode/Navigation, OCR-Druckbilder, unvollständige Bücher, gleichzeitige Korrekturen | MA-058 – MA-061 |

**Traceability:** Die konkreten Anforderungs-/WP-Verweise stehen je Fall; die Übersicht gruppiert Szenarien, behauptet keine vollständige Abdeckung aller IDs. Zurückgestellte Erweiterungen (z. B. Leihe, QR, Lizenzunterlagen, externe Metadaten und forScore) behalten ihre Roadmap-Priorität und benötigen bei späterer Umsetzung eigene Fälle.

**Abgrenzung der Nachweise (bindend):**
1. **Verifizierte WP-54/55-Softwarebasis** (synthetische CI): Region-/Logikseitenmodell, Editionen, Sammlungen/Sätze, gemeinsame Seiten-Strategie, 125-Edition-Publikation, gemeinsame Projektinhalte (synthetisch). Dies ist **kein** Nachweis manueller Abnahme. Service-/Modelltests bedeuten nicht automatisch, dass jeder Erfassungsweg bereits ohne technische Hilfe in der Oberfläche verfügbar ist; solche Schritte bleiben bis zum jeweiligen Editor teilweise implementiert.
2. **Aktuell abnehmbar** (mit synthetischen Daten, lokal): Fälle mit Kennzeichnung „Verfügbar — lokal prüfbar".
3. **Offene Pakete/Restumfang:** WP-24/25/26 (erster Ganzseiten-OCR-Inkrement implementiert, Regions-/Mehrwerk-Evidenz und Gesamtakzeptanz offen), WP-27 (Integrität), WP-56 (Segmentierung), WP-40a–c/41/40f (Scanaufbereitung), WP-42/57 (Marschbuch/Vorlagen), WP-44b/45/46 (Druck), WP-47b (Sicherung), WP-58/59/60a/b (sekundär/Kern gemäß DEC-16).
4. **Physische/Realabnahme** (eigene Inhaber-Gates): MA-047 – MA-057; nur mit genehmigtem Zugriff und anwendbaren Voraussetzungen je Fall, standardmäßig synthetische Daten. Echte Vereinsdaten ausschließlich in separat genehmigten privaten Realtests, nie in Repository/CI/externen Diensten.

Synthetische CI errichtet nie einen manuellen Abnahmestatus (DEC-16). Jeder Fall ist initial **nicht ausgeführt**; „bestanden" wird nur nach tatsächlicher Durchführung mit Datum, Prüfer:in und Build vermerkt.
