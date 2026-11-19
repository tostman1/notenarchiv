# Notenarchiv & Marschbuch-Generator – Technisches Konzept

**Version 1.1 · 19.11.2026**  
**Status:** Architekturvorschlag, noch nicht implementiert oder auf der DiskStation getestet.  
**Basis:** `REQUIREMENTS.md` – funktionale Anforderungen Version 1.1.

## 1. Architekturentscheidung

Eine eigenständige lokale Webanwendung für Notenarchivare auf der Synology DS224+. Bedienung im Browser; keine Cloud, keine Telemetrie, kein externer OCR-Dienst. Die Originalscans werden ausschließlich gelesen. Die Anwendung erzeugt ein separates kuratiertes Archiv und davon unabhängige Projektausgaben.

Empfohlen: modularer Python-Monolith mit Django, serverseitigen Templates, HTMX, SQLite und genau einem persistenten Hintergrundworker. Web und Worker können als zwei Container desselben Images laufen. Das vermeidet Redis, Celery und PostgreSQL im ersten Release. Optional ein isolierter CUPS-Druckdienst oder ein vorhandener IPP-Printserver. Alle Container laufen ohne privilegierten Modus, Docker-Socket oder Zugriff auf andere NAS-Freigaben.

```
Browser (LAN / privater Remotezugriff, HTTPS)
   │
   ▼
Django + Gunicorn ── SQLite (lokales NAS-Dateisystem)
   │                         │
   │                    persistente Jobs
   │                         ▼
   └────────────────── Python-Worker (1 parallel)
                             │
         ┌───────────────────┼────────────────────┐
         ▼                   ▼                    ▼
    Originale :ro       Zielarchiv :rw        Ausgaben :rw
                             │
                             ▼
                      IPP/CUPS → Drucker
```

Die DS224+ hat einen x86-64 Intel Celeron J4125 (4 Kerne) und serienmäßig 2 GB RAM, offiziell bis 6 GB erweiterbar. Daher zunächst nur ein OCR-/PDF-Job gleichzeitig, seitenweise Verarbeitung, temporäre Dateien statt kompletter Bildstapel im RAM; RAM-Erweiterung erst bei Bedarf oder bei umfangreichen parallelen NAS-Diensten. Keine GPU erforderlich. Die aktuelle RAM-Ausstattung und DSM-Version sind noch nicht bekannt.

## 2. Empfohlene Bibliotheken

| Bereich | Bibliothek / Werkzeug | Aufgabe |
|---|---|---|
| Runtime | Python 3.12 oder 3.13, nach Kompatibilitätstest | gemeinsamer Core und Server |
| Webframework | Django, unterstützte LTS-Version | ORM, Migrationen, Sessions, Auth, Formulare, CSRF |
| Webserver | Gunicorn | WSGI-Server im Container |
| UI | Django Templates, HTMX, Bootstrap oder eigenes CSS | Suche, Dialoge, Prüfmatrix, Projekteditor ohne SPA |
| Drag-and-drop | SortableJS | Stückliste und Reihenfolge |
| Vorschau | PDF.js (lokal ausgeliefert), Pillow | PDF-Anzeige und Thumbnails |
| PDF lesen/mergen | pypdf | PDF-Seiten, Seitenmaße, Rotation, Merge, A3-Layout |
| PDF rendern | pypdfium2 | Rasterung für OCR, Thumbnails und Deskew |
| Scanaufbereitung | opencv-python-headless, NumPy, Pillow | Hough-Linien, Deskew, Rauschen, Kontrast; nur wenn sinnvoll |
| PDF erzeugen | ReportLab | Deckblätter, Inhaltsverzeichnisse, Platzhalter, Seitengrößen |
| Lokale OCR | Tesseract 5 + pytesseract | OCR-Text, Bounding Boxes, Confidence; Sprachdaten deu/eng/ita/fra nach Bedarf |
| Erkennung | re, unicodedata, RapidFuzz | Normalisierung, Aliasregeln, Kandidatensuche |
| Identität | uuid, hashlib, pathlib, shutil | UUID, SHA-256, sichere Pfade, Dateikopien |
| Druck | CUPS-Client (lp, lpstat, lpoptions) oder IPP-Adapter | Druckerfähigkeiten, Druckaufträge, Status |
| Tests | pytest, pytest-django, Playwright (CI) | Logik, DB, Browser-Workflows |
| Qualität | Ruff, pip-audit, Trivy | Linting, Abhängigkeits-/Image-Prüfung |
| Dependency-Lock | uv mit uv.lock oder pip-tools | reproduzierbare Builds |

Alle JavaScript-/CSS-Assets werden lokal mitgeliefert, nicht von CDNs geladen. Bibliotheksversionen werden nach einem Proof of Concept festgeschrieben, nicht unkontrolliert auf `latest` aktualisiert.

### PDF- und Scanverarbeitung

Die PDF-Pipeline wird als eigenständiges, GUI-unabhängiges Python-Modul entwickelt. Empfohlen ist `pypdf` für PDF-Struktur und Layout, `pypdfium2` für Rasterung, OpenCV/NumPy für Bildverarbeitung, Pillow für Bildkonvertierung und ReportLab für generierte Seiten. Diese Bibliotheken bilden den vorgesehenen Stack; Lizenz- und Notice-Pflichten einschließlich transitiver Abhängigkeiten sind vor Veröffentlichung zu prüfen.

Die Module bieten klar definierte Funktionen für PDF-Validierung, Vorschaurendering, seitenweises OCR-Preprocessing, Deskew anhand horizontaler Notenlinien, konservative Rausch- und Randschattenreduktion, Zuschnitt, Seitenformatnormalisierung, PDF-Merge und Drucklayout. Die Bildverarbeitung ist separat aufrufbar und arbeitet mit abgeleiteten Dateien. Vektor-PDFs möglichst ohne Rasterung weiterverarbeiten. Die Verarbeitung darf keine musikalischen Zeichen verändern oder abschneiden; repräsentative Scan-Fixtures und visuelle Vergleichstests sind erforderlich. Für das Marschbuch wird die Seite standardmäßig auf 170 × 120 mm quer normiert. CLI-Kommandos für Tests und Batch-Verarbeitung sind sinnvoll.

## 3. NAS-Verzeichnisstruktur und Schutz der Originale

Verbindliches RAW/CLEAN-Prinzip: `SOURCE_HOST` ist das ausschließlich lesbare RAW-Archiv, `CURATED_HOST` das separate CLEAN-Archiv mit realen PDF-Kopien in Unterordnern pro Stück/Arrangement. Die Anwendung kopiert auch bereits korrekt benannte PDFs; Exporte lesen nur bestätigte CLEAN-Dateien. RAW und CLEAN dürfen sich weder gleichen noch ineinander liegen. Auch Status-, Export- und Anwendungsdatenverzeichnisse dürfen nicht innerhalb von RAW liegen. Beim Start kanonische Pfade und Mount-/Berechtigungskonfiguration validieren, bei Überlappung abbrechen; keine Quelle als Ziel eines Datei-Schreibvorgangs verwenden. Symbolische Links und Dateipfad-Traversal verhindern. Keine Änderungen an RAW, auch nicht bei erneuter Indizierung, Korrektur oder Scanaufbereitung.

Beispielpfade; an die tatsächlich vorhandenen DSM-Freigaben anpassen, nicht ungeprüft neue Ordner in einem bestehenden Archiv anlegen.

```text
/volume1/Notenarchiv/                   # bestehende Quelle, nicht umbenennen
  Böhmischer Traum/
    doc001.pdf
    Trombone II-III.pdf
  ABBA Medley/
    scan001.pdf
/volume1/Notenarchiv_Sortiert/          # neu, App verwaltet Inhalt
  Böhmischer Traum [arr-a1b2c3d4]/
    Klarinette_B_02.pdf
    Posaune_C_Bassschluessel_02-03.pdf
    _Ungeprueft/
      scan004__d7e8f901.pdf
  ABBA Medley [arr-f5e6d7c8]/
    Floete_01.pdf
/volume1/Notenarchiv_Status/            # sichtbare Statusmarkierung parallel zur Quelle
  Böhmischer Traum/
    INDEXSTATUS.json
    _INDIZIERT_BITTE_PRUEFEN.txt
/volume1/Notenmappen/                   # generierte Ausgaben
  Konzertmappe 2027 [Projekt-ID]/
    Personen/
    Stimmen/
    Druck/
/volume1/docker/notenarchiv/           # nur für Dienstkonto/Admin
  compose.yaml
  .env
  data/                                # SQLite, Einstellungen, Logs, Thumbnails
  secrets/
```

### Originalmarkierung: wichtige Unterscheidung

Ein read-only gemounteter Originalordner kann nicht automatisch mit einer Datei beschrieben werden. Deshalb im sicheren Standardmodus einen parallel gespiegelten Statusordner und sichtbare Statusanzeige im Webarchiv verwenden. Wenn die Markierung zwingend **direkt im Originalordner** erscheinen soll, optional eine ausdrücklich freigegebene Marker-Funktion (separater Dienst/Prozess oder manuelles Kopieren) mit eng begrenzten DSM-ACLs implementieren. Die Schreibberechtigung auf einem Elternordner kann sonst Umbenennen/Löschen von PDFs erlauben. Vor Aktivierung müssen negative Tests bestätigen, dass das Marker-Konto Originale weder verändern, löschen noch umbenennen kann; wenn das auf DSM nicht zuverlässig möglich ist, beim sicheren parallelen Status bleiben. Die Hauptanwendung behält immer den read-only Mount. Keine Umbenennung des Quellordners und keine Umbenennung der PDFs im Original.

Mögliche Marker: `_INDIZIERT_BITTE_PRUEFEN.txt`, `_GEPRUEFT.txt`, `_NEUE_DATEIEN_PRUEFEN.txt`. Nicht mehrere widersprüchliche Statusmarker stehen lassen. Der Marker ist nur eine lesbare Projektion des DB-Status; die DB ist führend. Marker enthält Datum, Quellordner-ID, Fingerprint und Anzahl geprüfter/offener Dateien, keine personenbezogenen Daten.

### Zielnamen

- Standard: `Instrument_Stimmung_Notation_Stimmnummer.pdf`, nur relevante Felder verwenden. Optional Titelpräfix, wenn die Datei außerhalb des Stückordners identifizierbar sein soll; empfohlen als konfigurierbarer, später stabiler Standard.
- Ein PDF mit mehreren Stimmen bleibt eine Datei, z. B. `Posaune_C_Bassschluessel_02-03.pdf`; die DB verknüpft es mit beiden Stimmen.
- Nicht eindeutige Dateien liegen in `_Ungeprueft/`; keine falsche Instrumentenbezeichnung als endgültiger Name.
- Bei Konflikten oder alternativen Notenausgaben nicht überschreiben: stabile ID-Kurzform oder Versionssuffix ergänzen und Konflikt zur Prüfung anzeigen.
- Titel/Arrangeur sind Anzeige-/Suchfelder; stabile UUID bleibt auch bei Korrektur von Namen unverändert. Namen Windows/SMB-kompatibel machen, Unicode normalisieren, Pfadtraversal verhindern.
- Initiale Zielkopie ist byteidentisch mit der Quelle (SHA-256 prüfen). Optimierte Scans nur als getrennte abgeleitete Datei mit Verarbeitungsversion ablegen; keine Originalkopie still überschreiben.

## 4. Indizierungsworkflow

1. Die Indizierung als separate Archivfunktion starten, Quellordner auswählen oder Archiv auf neue/geänderte Dateien scannen. Nur PDFs im freigegebenen Root, keine Symlinks nach außen. Laufende Scans erst nach stabilem Dateizustand lesen.
2. Dateigröße, Änderungszeit, Pfad und bei neuen/geänderten Dateien SHA-256 erfassen. PDF auf Lesbarkeit und Seitenzahl prüfen. Exakter Hash-Duplikat-Hinweis; nicht automatisch verschiedene Stücke zusammenlegen.
3. Stücktitel zunächst aus Ordnername und Instrument/Stimme aus Dateiname vorschlagen. Für jede neue oder inhaltlich geänderte PDF verpflichtend den tatsächlichen Inhalt prüfen: vorhandene PDF-Textschicht auswerten und relevante gescannte Kopfbereiche per OCR lesen (z. B. erste 20–30 % der ersten Seite, bei Bedarf weitere Seiten/Regionen). Ein eindeutig wirkender Dateiname ist niemals ein Grund, die Inhaltsprüfung zu überspringen. Bei zuverlässig auslesbarem digitalem Text ist zusätzliche Raster-OCR nicht zwingend, bei Scan-PDFs hingegen erforderlich.
4. OCR-Kandidaten, erkannte Textausschnitte, Regel-ID und Scores speichern. Aliase (Trombone, Posaune, Trb., römische Zahlen usw.), Stimmung, Notation und Mehrfachstimmen normalisieren. Keine Zuordnung nur aufgrund ähnlich klingender Namen oder Zahl. Dateinamen- und Inhaltskandidaten getrennt speichern und vergleichen: Übereinstimmung = plausibler Vorschlag; Widerspruch = KONFLIKT; fehlender oder unklarer Inhaltsnachweis = UNKLAR/ZU_PRUEFEN. Kein automatisches BESTAETIGT, auch bei hoher Sicherheit.
5. PDFs in Staging-Dateien im Ziel-Dateisystem kopieren, SHA-256 prüfen, atomar in neue Zielpfade veröffentlichen. Unklare Zuordnungen in `_Ungeprueft/`. Persistenter Job und Reconciliation bei Abbruch zwischen DB und Dateioperationen.
6. Status des Quellordners auf `INDIZIERT_PRUEFUNG_OFFEN` setzen, sobald alle PDF-Dateien erfasst/kopiert sind oder dokumentierte Fehler vorliegen (bei Fehlern Status `TEILWEISE_FEHLER`, nicht erfolgreich indiziert). Statusmarker schreiben/aktualisieren. Die UI zeigt deutlich „Stimmen kontrollieren“ und die Anzahl ungeprüfter Dokumente.
7. Archivar öffnet Prüfansicht: PDF/Zoom neben Originalname, OCR-Text, Titel, Arrangement, Stimmen-Dropdowns, Status und ggf. Konflikte. Mehrere Stimmen auswählbar. Korrektur benennt/verschiebt ausschließlich die Zielkopie und aktualisiert die DB; Quelle bleibt unverändert.
8. Manuelle Bestätigung pro Datei; optional Batch-Bestätigung nach bewusster Sichtprüfung. Projektgenerierung benutzt standardmäßig nur bestätigte Zuordnungen. Ungeprüfte Stimmen werden nicht still verwendet.
9. Wenn alle Dateien fachlich geprüft sind, Ordnerstatus `GEPRUEFT`. Fehlende Stimmen sind ein separater Zustand: „geprüft“ bedeutet nicht automatisch „vollständig“.
10. Bei neuen/geänderten Dateien bestehende bestätigte Zuordnungen unveränderter Hashes erhalten. Nur betroffene Versionen erneut prüfen. Neue Version wird separat gespeichert; alte, bereits verwendete Version bleibt referenzierbar. Gelöschte Quelle markieren, Zielkopie nicht automatisch löschen. Abgleich als manueller Start und optional zeitgesteuert.

### Beispiel

`Böhmischer Traum/Trombone II-III.pdf` → Dateinamen-Kandidaten Posaune 2 und 3 → PDF-Inhaltsprüfung (Text/OCR) und Abgleich → byteidentische Kopie `Posaune_02-03.pdf` → Status „zu prüfen“ → Archivar bestätigt beide Stimmen → dieselbe PDF wird beiden zugeordnet. Kein doppeltes Ablegen notwendig.

Beispiele für den Abgleich:

| Dateiname | PDF-Inhalt | Ergebnis |
|---|---|---|
| `Posaune1.pdf` | 1. Posaune | Plausibler Vorschlag, manuell bestätigen |
| `Trombone II-III.pdf` | Trombone II/III | Beide Stimmen vorschlagen, manuell bestätigen |
| `Posaune1.pdf` | 2. Posaune | Konflikt, Zuordnung manuell klären |
| `Posaune1.pdf` | Keine lesbare Stimmenbezeichnung | Unklar, manuell prüfen |

Nur bei unverändertem SHA-256 und bereits bestätigter Zuordnung darf bei späteren Archivläufen die erneute OCR und manuelle Prüfung entfallen. Bei Änderungen ist die neue Dateiversion erneut zu prüfen.

### Statusmodell

| Ebene | Status |
|---|---|
| Quellordner | NEU / INDIZIERUNG_LAEUFT / TEILWEISE_FEHLER / INDIZIERT_PRUEFUNG_OFFEN / GEPRUEFT / AENDERUNG_ERKANNT |
| PDF/Version | ERKANNT / UNKLAR / ZU_PRUEFEN / BESTAETIGT / KONFLIKT / FEHLER / QUELLE_FEHLT |
| Vollständigkeit | unabhängig anhand erwarteter Stimmen (vollständig / fehlend / nicht erforderlich / ungeklärt) |
| Job | QUEUED / RUNNING / SUCCEEDED / FAILED / CANCELLED |

Wichtig: OCR-Confidence ist kein Beweis der musikalischen Richtigkeit. Ein erkanntes Instrument kann ohne korrekte Transposition oder Schlüssel unbrauchbar sein. Keine automatische musikalische Transposition im MVP.

## 5. Datenmodell und GUIDs

Zwei verschiedene Begriffe: `GID` bezeichnet die Linux-Gruppen-ID für Dateirechte, `GUID/UUID` bezeichnet eine stabile Objekt-ID der Anwendung. Beide sind erforderlich, aber unabhängig.

Python `uuid.uuid4()` bzw. Django `UUIDField(default=uuid.uuid4, ...)` für Stücke, Arrangements, Dateien, Personen, Projekte, Projektpositionen und Exporte. SHA-256 für Inhaltsidentität, nicht als Ersatz für die Objekt-ID. Identitäten und relative Pfade persistieren in SQLite.

| Tabelle/Entität | Wesentliche Daten |
|---|---|
| Instrument | ID, Name, Aliase, Stimmung/Notation |
| Stimme | ID, Instrument-ID, Nummer/Bezeichnung, Schlüssel, Transposition/Variante |
| Mitglied | ID, Name, reguläre Stimme, aktiv/inaktiv |
| Werk | ID, Titel, alternative Titel |
| Arrangement | ID, Werk-ID, Arrangeur, ggf. Besetzungs-/Ausgabenbezeichnung |
| Quellordner | ID, relativer Pfad, Fingerprint, Status |
| Quelldatei / Version | ID, Quellordner, Pfad, SHA-256, Größe, Seitenzahl, Erkennungsstatus |
| Archivdatei | ID, Quellversion, relativer Zielpfad, Hash, Verarbeitungsversion |
| Datei_Stimme | Archivdatei-ID, Stimme-ID, Bestätigung, Mehrfachzuordnungen |
| OCR_Kandidat | Datei-ID, Text/Region, erkannte Werte, Score, Regelversion |
| Erwartete_Stimme | Arrangement/Ensemble-Besetzung, Stimme, erforderlich/optional |
| Projekt | ID, Name, Format, Druckoptionen, Version, Status |
| Projektposition | ID, Projekt-ID, Nummer, Arrangement-ID oder Reserve, Reihenfolge |
| Projektteilnehmer | Projekt-ID, Mitglied-ID, Standard-/Projektstimme, ggf. Ensemble-Stimme |
| Projekt_Ensemble_Mapping | Projekt/Arrangement, Ensemble-Stimme, Instrument, konkrete Notenstimme |
| Persönliche_Ausnahme | Teilnehmer-ID, Projektposition-ID, abweichende Instrumenten-/Notenstimme |
| Ersatzregel | Geltungsbereich, gewünschte Stimme, erlaubte Ersatzstimme, Priorität |
| Export | Projektversion, Teilnehmer/Stimme, Manifest, Ausgabe-/Druckdateipfade |
| Job | Typ, Status, Fortschritt, Fehler, Zeitpunkte, Lease/Heartbeat |
| Prüfprotokoll | Bearbeiter, Zeit, Aktion, vorher/nachher |

Projektposition besitzt eigene ID, damit dasselbe Arrangement zweimal enthalten sein darf und Reserven erhalten bleiben. Alle Teilnehmer und stimmbezogenen Exporte verwenden dieselben Projektpositionen und Nummern; es gibt keine persönlichen Zusatz- oder Auslassungspositionen. Die Personalisierung betrifft ausschließlich Stimmenzuordnungen und optionale Deckblätter. Für wiederholbare Drucke speichert der Export die genauen verwendeten Datei-Versionen und Regeln. Ein Projekt kann später neu erzeugt werden mit expliziter Auswahl aktueller bestätigter Notenversionen.

### 5.1 Bedienung und Persistenz schneller Stimmenwechsel

Die Projekt-Hauptansicht enthält eine editierbare Stimmenmatrix (Projektposition × Teilnehmer), mit HTMX-Teilaustausch einzelner Zellen, fixierten Zeilen-/Spaltenköpfen soweit sinnvoll und Instrument-/Teilnehmerfilter. Bei großen Projekten nur sichtbare bzw. paginierte Zeilen laden. Jede Zelle zeigt effektive Notenstimme und Herkunft (Standard, Projekt, Ausnahme, Ersatz, fehlend), nicht nur eine abstrakte Nummer. Ein direktes Dropdown bietet kompatible, bestätigte Notenfassungen des jeweiligen Arrangements; eine Ausnahme ist auch bei vorhandener Standardstimme zulässig. Bei mehreren PDFs derselben Stimme muss die konkrete Fassung eindeutig ausgewählt werden können. Keine automatische Transposition.

- `Projektteilnehmer` speichert die projektspezifische Standardzuweisung; `Persönliche_Ausnahme` wird eindeutig durch Teilnehmer-ID und Projektposition-ID identifiziert (Unique Constraint). Optional konkrete bestätigte Archivdatei/Fassung referenzieren, wenn die Stimm-ID allein nicht eindeutig ist.
- Auflösung serverseitig zentral implementieren: persönliche Stückausnahme vor Projektstandard vor Vereinsstandard; musikalische Ensemble-Mappings bei Bedarf auflösen, anschließend nur bei fehlender spielbarer Fassung erlaubte Ersatzregeln auswerten. Ein manuell gewähltes vorhandenes Part wird nicht durch eine Ersatzregel ersetzt.
- Speichern einzelner Zellen ohne Seitenwechsel per validiertem HTMX-Request; Rückmeldung bei Fehlern, CSRF-Schutz und Prüfung der Projektzugehörigkeit. Mehrfachauswahl mit Batch-Update in einer kurzen DB-Transaktion. Reset löscht die betreffende Ausnahme und berechnet die effektive Stimme neu. Änderungen am Projektstandard lassen bestehende Ausnahmen bestehen, außer bei ausdrücklich gewähltem Reset.
- Projektänderungen versionieren, bei konkurrierenden Bearbeitungen Konflikte statt stiller Überschreibung anzeigen, vorher/nachher protokollieren. Exportmanifest hält die konkrete verwendete Stimme und Dateiversion fest. Betroffene personalisierte Exporte als veraltet kennzeichnen; gezielte Neugenerierung des betroffenen Teilnehmers anbieten, ohne andere Zuordnungen oder Stücklisten zu ändern.
- Akzeptanztest: Mathias Posaune 1, Sebi Posaune 2, Riccardo Posaune 3 als Projektstandard; Riccardo erhält für mehrere ausgewählte Stücke Posaune 2, obwohl Posaune 3 vorhanden ist. Nach Neuladen sind alle Änderungen erhalten; Reset einer Zelle stellt Projektstandard wieder her. Mathias, Sebi, Vereinsstammdaten, RAW/CLEAN-Dateizuordnung und Nummerierung bleiben unverändert.

SQLite auf einem lokalen Bind-Mount der NAS, nicht über SMB/NFS. Kurze Transaktionen, WAL nach Kompatibilitätsprüfung, Busy Timeout, Fremdschlüssel, genau ein Worker; DB nicht während OCR sperren. Bei späterer hoher Mehrbenutzerlast kann PostgreSQL nachgerüstet werden. DB-Backup über SQLite Backup API oder bei gestoppten Containern, nicht einfach eine laufende DB-Datei ohne WAL kopieren.

## 6. Servicekonto, UID/GID und Berechtigungen

In DSM unter Systemsteuerung > Benutzer und Gruppe ein dediziertes Konto `svc_notenarchiv` und optional eine Gruppe `notenarchiv_service` erstellen. Nicht Mitglied der Administratorengruppe; unnötige DSM-Anwendungsberechtigungen deaktivieren; kein täglicher Login als Dienstkonto. Die tatsächlichen UID/GID per SSH auf der Vereins-NAS bestimmen:

```sh
id svc_notenarchiv
id -u svc_notenarchiv
id -g svc_notenarchiv
```

Die ausgegebenen Werte in die lokale `.env` eintragen, keine Werte raten. Falls spezielle Gruppen-ACLs benötigt werden, die richtige numerische Gruppe ermitteln und ggf. `group_add` explizit konfigurieren. Der Compose-Schlüssel `user: "${APP_UID}:${APP_GID}"` setzt die Laufzeitidentität. `PUID/PGID` sind keine universellen Docker-Variablen und wirken nur, wenn ein Image sie selbst auswertet.

| NAS-Freigabe | Dienstkonto | Archivare |
|---|---|---|
| Originalarchiv | Lesen, zusätzlich Docker `:ro` | gemäß Berechtigungen für Digitalisierung und Ablage |
| Sortiertes Archiv | Lesen/Schreiben | empfohlen lesen; Korrekturen in der Web-App |
| Statusarchiv | Lesen/Schreiben | Lesen |
| Notenmappen | Lesen/Schreiben | Lesen/Download, weitere Rechte nach Bedarf |
| docker/notenarchiv/data | Lesen/Schreiben | kein direkter Zugriff nötig |
| Secrets/Compose | Admin verwaltet, Dienst nur erforderliche Leserechte | kein Zugriff |
| Andere Vereins-/private Shares | kein Zugriff | unverändert |

DSM-ACLs und numerische Identitäten vor Inbetriebnahme mit Lese-/Schreib-/Verweigerungstests überprüfen. Kein `chmod 777`, keine pauschale Freigabe an Everyone, keine privilegierten Container. Das Dienstkonto ist nicht dasselbe wie die Benutzer der Webanwendung: Archivare erhalten individuelle Web-Logins mit identischen Funktionsrechten (kein Rollenmodell nötig, aber Authentifizierung und nachvollziehbare Änderungen sinnvoll). Kein öffentliches Portforwarding.

## 7. Konfiguration

In `.env` nur Deployment-Konfiguration und Pfade. Fachliche Einstellungen wie Drucker, Aliasregeln, Stimmen, Projektformat und OCR-Profile gehören in die Datenbank und in die Weboberfläche. Secrets separat in Dateien mit restriktiven Rechten, nie in Git oder im Image. Beispiel `.env.example` ohne reale Geheimnisse:

```dotenv
APP_IMAGE=ghcr.io/OWNER/notenarchiv:0.1.0
APP_UID=REPLACE_WITH_DSM_UID
APP_GID=REPLACE_WITH_DSM_GID
APP_PORT=8085
APP_BIND=127.0.0.1
TZ=Europe/Vienna
APP_ALLOWED_HOSTS=notenarchiv.example.invalid,localhost
APP_CSRF_TRUSTED_ORIGINS=https://notenarchiv.example.invalid
SOURCE_HOST=/volume1/Notenarchiv
CURATED_HOST=/volume1/Notenarchiv_Sortiert
STATUS_HOST=/volume1/Notenarchiv_Status
EXPORT_HOST=/volume1/Notenmappen
DATA_HOST=/volume1/docker/notenarchiv/data
SECRET_HOST=/volume1/docker/notenarchiv/secrets/django_secret_key
```

`APP_BIND=127.0.0.1` setzt einen DSM-Reverse-Proxy oder anderen lokalen Zugang voraus. Für einen reinen LAN-Test kann die NAS-LAN-IP verwendet werden, dann Firewall entsprechend einschränken; keine öffentliche Freigabe. `OWNER`, Hostnamen und IDs sind Platzhalter. Weitere interne Defaults:

| Variable | Beispiel / Zweck |
|---|---|
| SOURCE_DIR | /archive/source |
| CURATED_DIR | /archive/curated |
| STATUS_DIR | /archive/status |
| EXPORT_DIR | /archive/export |
| DATABASE_PATH | /data/notenarchiv.sqlite3 |
| DJANGO_SECRET_KEY_FILE | /run/secrets/django_secret_key |
| DEBUG_MODE | FALSE (Default; TRUE aktiviert Anwendungsdiagnose, nicht Django DEBUG) |
| OCR_LANGUAGES | deu+eng (weitere Sprachen optional) |
| OCR_DPI | 300 (Startwert, messen) |
| OCR_TIMEOUT_SECONDS | 60 (je Seite/Region, konfigurierbar) |
| OCR_WORKERS | 1 |
| OMP_THREAD_LIMIT | 2 |
| PDF_MAX_BYTES | 104857600 (Startwert; große Partituren berücksichtigen) |
| PDF_MAX_RENDER_PIXELS | 30000000 (Startwert) |
| INDEX_INTERVAL_MINUTES | 0 = nur manuell; später optional |
| PRINT_ENABLED | 0 bis Drucker getestet |
| CUPS_SERVER | optionaler interner Druckserver |
| LOG_LEVEL | Abgeleitet: INFO bei Deploy, DEBUG bei Debug; keine unabhängige Umschaltung erforderlich |

Keine DSM-Admin-Zugangsdaten, SMB-Passwörter oder GitHub-Token in der App notwendig, da lokale Bind-Mounts verwendet werden. Werte validieren und bei fehlenden Zugriffsrechten klar abbrechen.

### 7.1 Betriebsmodus und Logging

`DEBUG_MODE` ist die einzige Umschaltvariable für die Anwendungsdiagnose. Fehlt sie in der Prozessumgebung, gilt immer Deploy. `TRUE` und `FALSE` werden unabhängig von Groß-/Kleinschreibung nach Entfernen umgebender Leerzeichen akzeptiert; andere Werte (einschließlich leerer expliziter Werte) führen beim Start zu einer verständlichen Konfigurationsfehlermeldung. Die Standard-Compose-Datei enthält keinen aktiven Eintrag für `DEBUG_MODE`; die Anwendung bestimmt den Standard selbst. Python-Beispiel:

```python
import os

raw = os.environ.get("DEBUG_MODE", "FALSE").strip().upper()
if raw not in {"TRUE", "FALSE"}:
    raise ValueError("DEBUG_MODE must be TRUE or FALSE")
DEBUG_MODE = raw == "TRUE"
DEBUG = False  # Django DEBUG bleibt in beiden Modi deaktiviert.
```

In der Standard-Compose-Konfiguration ist `DEBUG_MODE` nicht gesetzt. In der gemeinsamen `x-app`-Umgebung kann für Diagnosezwecke direkt gesetzt werden:

```yaml
environment:
  DEBUG_MODE: "TRUE"
```

Web und Worker müssen denselben Modus erhalten. Bei Änderung beide Dienste neu erstellen (z. B. `docker compose up -d --force-recreate web worker`); kein neues Image notwendig. Die tatsächlich effektive Einstellung beim Start protokollieren. Keine Umschaltung durch GUI oder HTTP-Parameter. Django `DEBUG` bleibt fest auf `False`; kein Entwicklungsserver, kein Django-Traceback im Browser, keine Abschaltung von CSRF, Anmeldung oder Berechtigungen.

| Funktion | Deploy (Default) | Debug |
|---|---|---|
| Python-Anwendungslogs auf stdout/stderr | INFO und höher | DEBUG und höher |
| Persistente detaillierte Anwendungs-Logdateien | aus | an |
| Live-Diagnoseansicht im GUI | aus | an |
| Fachliche Job-Zustände, OCR-Vorschläge und Prüfhinweise | an | an |
| Authentifizierung und Sicherheitsprüfungen | an | an |

Vorgeschlagene Implementierung mit Python `logging`, Django-Logging-Konfiguration und `RotatingFileHandler` (ein schreibender Prozess je Datei). Docker-Logrotation bleibt in beiden Modi aktiv. Für Web und Worker getrennte Dateien, damit keine konkurrierende Dateirotation entsteht:

```
/data/logs/
  web.debug.log
  web.debug.log.1
  worker.debug.log
  worker.debug.log.1
```

Pro Datei als Startwert 10 MiB, fünf Backups zusätzlich zur aktiven Datei; insgesamt maximal ca. 120 MiB für beide Logger unter diesen Annahmen. Bei später mehreren Web-/Worker-Prozessen pro Dienst separate Prozessdateien oder einen zentralen Log-Listener einsetzen; `RotatingFileHandler` ist nicht prozessübergreifend sicher. UID/GID müssen Schreibrechte auf `/data/logs` besitzen. Kann der Debug-Dateilog nicht geöffnet werden, Start mit klarer Diagnose abbrechen, statt Debug-Logging stillschweigend zu deaktivieren. Bereits bestehende Debug-Dateien werden beim Rückwechsel zu Deploy nicht automatisch gelöscht; Zugriff über die Debug-GUI wird deaktiviert, und alte Dateien können administrativ entfernt werden.

Logfelder: ISO-8601-Zeitstempel mit Zeitzone, Level, Dienst, Komponente, Ereignis, Job-/Korrelations-ID, Dauer, gegebenenfalls interne Datei-ID, Fehlerklasse und bereinigte technische Details. Keine Passwörter, Tokens, HTTP-Cookies, vollständigen OCR-Rohtexte, PDF-Inhalte oder unnötigen personenbezogenen Daten; auch Fehlerdetails und Subprozessausgaben bereinigen. OCR-Zwischenergebnisse in der fachlichen Prüfoberfläche bleiben unabhängig vom Debug-Modus verfügbar; zusätzliche Diagnoseinformationen können z. B. ausgewählte Regel-ID, Erkennungssicherheit und Konfliktgrund enthalten.

GUI: zusätzlicher Menüpunkt „Debug / Logs“, Modusanzeige, abrufbare Live-Logansicht (HTMX-Polling mit Cursor und begrenzter Antwortgröße ausreichend), Filter nach Komponente/Job/Level/Zeit, kopierbare bzw. herunterladbare bereinigte Logauszüge. Nur authentifizierte Archivare; keine direkte Veröffentlichung des Logverzeichnisses als Staticfiles, kein beliebiger Dateipfad als Request-Parameter, HTML-Escaping. In Deploy werden Debug-Routen serverseitig deaktiviert, nicht nur ausgeblendet. Produktive Job- und Prüfstatus bleiben erhalten. Debug-Dateien sind Diagnoseartefakte, nicht die maßgebliche Datenquelle für fachliche Zustände.

## 8. Beispiel Compose-Deployment

Illustrativ, **nicht unmittelbar lauffähig**, bevor Dockerfile, Django-Settings, Health-Endpunkt und Management-Kommandos implementiert sind. Beide Services nutzen dasselbe getestete Image. Django-Migrationen nur einmal vor dem Start bzw. Upgrade ausführen (`docker compose run --rm web python manage.py migrate`), niemals unkoordiniert in beiden Diensten. Erst initialen Admin anlegen und danach starten.

```yaml
x-app: &app
  image: ${APP_IMAGE}
  user: "${APP_UID}:${APP_GID}"
  restart: unless-stopped
  init: true
  read_only: true
  cap_drop: [ALL]
  security_opt: [no-new-privileges:true]
  tmpfs:
    - /tmp:size=256m,mode=1777
  environment:
    TZ: ${TZ}
    # Optional: entfernen oder FALSE für Deploy; TRUE für Debug.
    # DEBUG_MODE: "TRUE"
    APP_ALLOWED_HOSTS: ${APP_ALLOWED_HOSTS}
    APP_CSRF_TRUSTED_ORIGINS: ${APP_CSRF_TRUSTED_ORIGINS}
    DJANGO_SECRET_KEY_FILE: /run/secrets/django_secret_key
    DATABASE_PATH: /data/notenarchiv.sqlite3
    SOURCE_DIR: /archive/source
    CURATED_DIR: /archive/curated
    STATUS_DIR: /archive/status
    EXPORT_DIR: /archive/export
    OCR_LANGUAGES: deu+eng
    OCR_DPI: "300"
    OCR_WORKERS: "1"
    OMP_THREAD_LIMIT: "2"
    PRINT_ENABLED: "0"
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
services:
  web:
    <<: *app
    command: [gunicorn, config.wsgi:application, --bind, "0.0.0.0:8000", --workers, "1", --threads, "4"]
    ports:
      - "${APP_BIND}:${APP_PORT}:8000"
    volumes:
      - ${DATA_HOST}:/data:rw
      - ${SOURCE_HOST}:/archive/source:ro
      - ${CURATED_HOST}:/archive/curated:ro
      - ${STATUS_HOST}:/archive/status:ro
      - ${EXPORT_HOST}:/archive/export:ro
      - ${SECRET_HOST}:/run/secrets/django_secret_key:ro
    healthcheck:
      test: [CMD, python, -c, "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
      interval: 30s
      timeout: 5s
      retries: 3
  worker:
    <<: *app
    command: [python, manage.py, run_worker]
    volumes:
      - ${DATA_HOST}:/data:rw
      - ${SOURCE_HOST}:/archive/source:ro
      - ${CURATED_HOST}:/archive/curated:rw
      - ${STATUS_HOST}:/archive/status:rw
      - ${EXPORT_HOST}:/archive/export:rw
      - ${SECRET_HOST}:/run/secrets/django_secret_key:ro
```

Worker verarbeitet auch Zielkopie-Umbenennungen, damit der Webcontainer dort read-only bleiben kann. Django-Healthcheck muss lokalen Host akzeptieren und keine Authentifizierung erfordern; keine sensiblen Details ausgeben. Gunicorn- und Django-Staticfiles-Serving explizit einrichten (z. B. WhiteNoise oder Reverse-Proxy). Umfangreiche OCR-Zwischendateien bei Bedarf in ein persistentes, begrenztes Scratch-Verzeichnis unter `/data` statt RAM-tmpfs. Ressourcenlimits nach Messung und verfügbarer DSM-Version einstellen. Die Worker-Queue muss beim Neustart verwaiste Jobs anhand Lease/Heartbeat erkennen; keine doppelten Druckaufträge automatisch neu starten.

## 9. GitHub und Container-Erstellung

Private GitHub-Repository-Option `notenarchiv` (oder öffentlich/open source bei bewusst gewählter Lizenz). Nur Code, synthetische Testdaten, Konfigurationstemplates und Dokumentation. Niemals echte Noten-PDFs, Namen der Vereinsmitglieder, NAS-Pfade mit Geheimnissen, Datenbank, OCR-Texte oder Tokens committen. Auch keine echten Scans in CI-Artefakten oder Issues.

```text
notenarchiv/
  README.md
  REQUIREMENTS.md
  ARCHITECTURE.md
  LICENSE
  pyproject.toml
  uv.lock
  Dockerfile
  .dockerignore
  .gitignore
  .env.example
  compose.yaml
  manage.py
  config/
  core/               # eigenständige PDF-/Bildverarbeitung
  apps/
    archive/          # OCR, Import, Review, Dateiversionen
    catalog/          # Werke, Arrangements, Instrumente, Stimmen
    members/
    projects/
    exports/
    printing/
    jobs/
  templates/
  static/
  tests/              # synthetische PDF- und OCR-Fixtures
  .github/workflows/
    ci.yml
    release.yml
```

Dockerfile: Python-slim-Basis, Debian-Pakete für Tesseract/Sprachdaten, ggf. CUPS-Client und notwendige PDF-Abhängigkeiten. Keine GUI. Lockfile-installierter Python-Code, Build-time Staticfiles, nicht-root Standardbenutzer und Runtime-Override durch Compose. Keine echten Daten während `docker build`. Build-Abhängigkeiten nach Möglichkeit aus Runtime-Image entfernen. Basisimage und Dependencies für Release pinnen.

### Pipeline

- Pull Request: Ruff, pytest/pytest-django, PDF-/OCR-Tests, Browser-Smoke-Test, Build-Test, Dependency-/Image-Sicherheitsprüfung.
- Merge auf main: optional internes Development-Image mit Commit-SHA.
- Versions-Tag `v0.1.0`: erneut testen, Image `ghcr.io/<owner>/notenarchiv:0.1.0` für `linux/amd64` bauen und veröffentlichen, Release-Notizen. Optional ARM64 erst bei Bedarf.
- GitHub Actions nutzt `GITHUB_TOKEN`, `contents: read`, `packages: write` nur für Publish-Job. Drittanbieter-Actions bei Umsetzung auf überprüfte Commit-SHAs pinnen. SBOM/Provenance erstellen. Keine Deploy-Schlüssel für die NAS im GitHub-Runner.
- NAS zieht das fertige Image; Produktion verwendet konkreten Release-Tag oder Digest, kein automatisches Watchtower-Update. Für private GHCR-Images einen dedizierten GitHub-Account/Token mit `read:packages` und Zugriff auf das Paket konfigurieren; Token nicht in Compose speichern.

Beispiel für den reinen Publish-Schritt eines späteren Release-Workflows (Testjob und Pinning noch ergänzen):

```yaml
name: Release image
on:
  push:
    tags: ['v*']
permissions:
  contents: read
  packages: write
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Login, build and push
        env:
          GHCR_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -eu
          image="ghcr.io/${GITHUB_REPOSITORY,,}"
          version="${GITHUB_REF_NAME#v}"
          printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin
          docker build --platform linux/amd64 -t "$image:$version" .
          docker push "$image:$version"
```

Dieser Ausschnitt ist kein vollständiger produktionsreifer CI-Workflow. Veröffentlichung erst nach erfolgreichem verpflichtendem Testjob und Prüfung des Tag-Inhalts. GitHub muss das Paket dem Repository korrekt zuordnen und die Berechtigung für private Pulls erhalten.

### DSM-Installation / Updates

1. Container Manager installieren; Shares und Dienstkonto anlegen, echte UID/GID ermitteln, Berechtigungen testen.
2. Compose-Datei und `.env` in Projektverzeichnis ablegen; Secret-Datei sicher erzeugen, Berechtigungen setzen.
3. Bei privatem Image in der tatsächlichen Docker-Client-Umgebung authentifizieren (`docker login ghcr.io`), nicht im App-Container.
4. Initial `docker compose pull`, Migrationen einmalig ausführen, Admin-Konto erstellen, `docker compose up -d`. Alternativ Projekt im DSM Container Manager aus Compose-Datei anlegen; Migrationen/Init weiterhin kontrolliert ausführen. Je nach DSM-Version CLI `docker compose` oder `docker-compose` prüfen.
5. Reverse-Proxy mit HTTPS und LAN-/Tailnet-Zugriff konfigurieren; keine öffentliche Freigabe. Quell-, Ziel- und Ausgabepfade im App-Diagnosemenü prüfen.
6. Update: DB und persistente Daten sichern, Worker stoppen, neuen Tag setzen, Image ziehen, Migration einmalig ausführen, neu starten und Smoke-Test durchführen. Bei DB-Migrationsproblemen alten Image-Tag allein nicht als ausreichenden Rollback betrachten; ggf. kompatiblen DB-Backupstand wiederherstellen. Projekt-Delete/Clean-Aktionen in DSM nicht unüberlegt verwenden.

## 10. PDF-Generierung und intelligenter Druck

Zwei getrennte Ausgaben: Lese-PDF mit Original-Seitenformaten und Druck-PDF mit Manifest. Optionales Deckblatt und Inhaltsverzeichnis voranstellen, gemeinsame Projektstücknummern beibehalten, Platzhalter erzeugen. Die Stückliste ist für alle Teilnehmer und Stimmen identisch; ausschließlich die konkret verwendeten Notenstimmen und das optionale Deckblatt unterscheiden sich.

Bei A4-Noten A3-Spreads stückweise erzeugen: A3 quer 420×297 mm, je zwei A4 hoch 210×297 mm nebeneinander; verbleibende Seite A4. Nicht über Stückgrenzen paaren. Originale A3-Seiten erkennen, im Lese-PDF als ganze A3-Seiten belassen und für den A3-Druck nicht aufteilen; A4 quer und Sonderformate benötigen eigene Regeln bzw. manuelle Entscheidung. Tatsächlicher Druckrand/Druckertreiber kann eine leichte Skalierung erzwingen; keine abgeschnittenen Noten. A3 nicht aus beliebigen PDF-Seiten ungeprüft erzwingen.

Druckadapter: Druckerfähigkeiten per IPP/CUPS abfragen, z. B. `lpstat -p`, `lpoptions -p DRUCKER -l`; Ausgabe bereits korrekt layouten, kein zusätzliches `number-up`. Möglichst gemischter Medienauftrag, sofern Drucker/IPP-Server dies zuverlässig unterstützt. Sonst aufeinanderfolgende Teilaufträge in der richtigen Reihenfolge (nur zusammenhängende Medienblöcke gruppieren, nicht sämtliche A4 und A3 separat nach Format sortieren). Andere Druckjobs können sich dazwischenschieben; Anwender darauf hinweisen und bei Bedarf manuell sortierbare Ausgabe anbieten. Keine pauschale Garantie für automatisches A3/A4 oder Sortierung. Job-ID, Status und Teilauftrag protokollieren, keine automatische Wiederholung unklarer Druckaufträge.

Fallback: Bei einem Drucker ohne A3-Unterstützung eine explizite Bestätigung für eine geeignete A4-Ersatzausgabe anfordern (gegebenenfalls verkleinert; Lesbarkeit in der Vorschau prüfen). Druckfertige PDFs und Manifest können zusätzlich heruntergeladen und manuell gedruckt werden. Druckerspezifische IPP-/Treiberfähigkeit, Papierfächer, benutzerdefiniertes 170×120-mm-Format und druckbare Ränder vor Implementierung testen. Kein Zugriff auf DSM-Admin oder Drucker-Passwörter im Quellcode. Druckerverbindungen auf bekannte interne Ziele beschränken.

## 11. Backup, Sicherheit und Tests

- Originale über den NAS-Backupplan sichern; kuratiertes Archiv, Status, Exporte und DB zusätzlich sichern. Originale und Zielkopien sind kein unabhängiges Backup, wenn sie auf derselben NAS liegen.
- DB konsistent sichern (Backup API oder Wartungsfenster) und Dateimanifeste/Versionen passend dazu. Wiederherstellung regelmäßig testen; Exporte sind teilweise regenerierbar, bestätigte Zuordnungen nicht.
- Alle Zugriffe nur über authentifizierte Websessions; gleiche Funktionen für alle Archivare, keine öffentlichen Links, CSRF-/Host-Prüfung, sichere Cookies bei HTTPS. Passwörter mit Django-Hashing. Protokolle ohne Secrets und unnötige OCR-/Personendaten.
- Originale und PDFs als nicht vertrauenswürdige Eingaben behandeln: Pfadgrenzen, PDF-Größen-/Pixel-/Zeitlimits, kein Shell-Aufruf mit interpolierten Dateinamen, keine PDF-JavaScript-Ausführung, Vorschau isolieren, Parser regelmäßig patchen. OCR ohne externen Netzwerkdienst. Runtime-Netzwerkzugang soweit möglich auf Browser/benötigte Drucker beschränken.
- Tests für gemischte Schreibweisen (II/III, 2. Trombone, B/Es, Schlüssel), Mehrfachzuordnung, falsche OCR, verpflichtende Inhaltsprüfung trotz eindeutigem Dateinamen, Dateiname/Inhalt-Widerspruch, fehlende Inhaltsbeschriftung, Wiederverwendung bestätigter unveränderter Hashes, fehlende/defekte PDFs, Duplikate, Unicode, Namenskollision, Änderungen/Löschungen, Wiederanlauf nach Kopierabbruch, read-only Originale (Schreib-/Lösch-/Umbenennungsversuche scheitern, auch bei erneuter Indizierung), getrennte RAW/CLEAN-Roots, byteidentische Kopien auch bei standardisiertem Quelldateinamen, Matrix-Einzel-/Mehrfachänderung, Reset, Persistenz, unveränderte Stammdaten und andere Teilnehmer, Nummernlücken, identische Stücklisten aller Exporte, Ersatzregeln, Ensemble-Transposition, PDF-Medienmaße, 1–6 Seiten A4/A3, Erhalt nativer A3-Seiten, Scanaufbereitung ohne Verlust musikalischer Zeichen, Druckfehler, DB-Restore.

Zusätzliche Tests für Betriebsmodi: Variable fehlt, TRUE/FALSE in gemischter Schreibweise, ungültiger Wert, gemeinsamer Modus Web/Worker, Django DEBUG stets False, persistente Logs nur im Debug-Modus, Logrotation, Wiederanlauf und Erhalt der Dateien, Schreibrechte, GUI/API-Zugriff nur authentifiziert und im Debug-Modus, keine Secrets in Logs, Normalbetrieb mit deaktivierter Diagnose.

## 12. Implementierungsreihenfolge

1. Repository für die eigenständige Anwendung anlegen, Lizenzstrategie für Abhängigkeiten festlegen, CI, Django-Weblogin, Deploy-/Debug-Konfiguration und Container-Smoke-Test auf der DS224+ aufsetzen.
2. Datenmodell, Instrumente/Stimmen, read-only Quellarchiv, separater Zielordner, Import/Kopie/Hash, Status, manuelle Zuordnung, Suche, Vorschau. Dies liefert bereits einen nutzbaren Archiv-Workflow ohne OCR.
3. OCR, Aliasregeln, Confidence, Prüfwarteschlange, Vollständigkeitsmatrix, inkrementeller Reindex. Mit repräsentativen Scans lokal benchmarken und Regeln verbessern.
4. Mitglieder, Projekte, Ensemble-/Stimmenzuordnung, direkt editierbare Stimmenmatrix mit Einzel-/Mehrfachänderungen und Reset, Ersatzregeln, Ausnahmen, PDF-Export und Prüfbericht.
5. Scanaufbereitung und Marschbuch-Pipeline entwickeln: Sonderformat, Deskew, Qualitätskontrolle und optionaler Import nummerierter Stimmenordner als separater Importadapter.
6. A3/A4-Layout und Druckvorschau; erst danach echten Netzwerkdrucker anbinden und Fallback testen.
7. Backup/Restore, Release-/Updateprozess und kurze Archivar-Schulung.

## 13. Noch zu entscheiden / prüfen

- Tatsächliche DSM-Version, RAM, Volume-/Share-Pfade, Druckermodelle, IPP-Fähigkeiten und Papierfächer.
- Originalordner-Markierung zwingend physisch im Quellordner oder sichtbarer paralleler Status ausreichend? Wenn direkt: ACL-/Marker-Proof-of-Concept ohne Originalschreibrechte.
- Namensstandard: optional Titel im PDF-Dateinamen, kurze ID im Ordnername oder nur bei gleichnamigen Arrangements. Vorgehen bei Alternativversionen und bereits vorhandenen Zielkopien.
- Definition der erwarteten Stimmen je Arrangement/Besetzung; eine fehlende Stimme ist nicht immer ein Archivfehler.
- Deckblattgestaltung, Details der Druckanordnung für querformatige A4-Noten und weitere Sonderformate.
- Kein OCR-Modell und keine Druckerautomatik wurden bislang an den realen PDFs bzw. Druckern getestet. Keine GitHub-Repositories, Container oder DSM-Benutzer wurden tatsächlich erstellt.

## 14. Referenzen

- Synology Container Manager Projects: https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_project
- DS224+ Spezifikationen: https://www.synology.com/en-us/products/DS224%2B
- Synology Volume-Berechtigungen: https://kb.synology.com/en-global/DSM/tutorial/Docker_container_cant_access_the_folder_or_file
- GitHub Container-Build: https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- GitHub Packages Berechtigungen: https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages
- Tesseract CLI und OCR-Confidence: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- CUPS Druckoptionen: https://www.cups.org/doc/options.html
- Django: https://docs.djangoproject.com/
- SQLite WAL: https://sqlite.org/wal.html
- pypdf: https://pypdf.readthedocs.io/
- pypdfium2: https://pypdfium2.readthedocs.io/
