# Lokal entwickeln (Windows)

1. Im Projektordner `uv sync --locked` ausführen.
2. `./dev.ps1 start` starten. Der Browser öffnet die lokale Anwendung automatisch.
3. Synthetische Entwicklungsdaten verwenden; keine echten Noten oder Mitglieder.
4. Zum Beenden `kill` eingeben und die Frage mit `yes` bestätigen. `no` läuft weiter.
   Alternativ Strg+C. In einem zweiten Terminal: `./dev.ps1 stop`.
5. Status: `./dev.ps1 status`. Nach Codeänderungen: `./dev.ps1 restart`.

Ohne automatische Anmeldung: `./dev.ps1 start -ManualAuth`. Ohne Browseröffnung:
`./dev.ps1 start -NoBrowser`. Anderer freier Port: `-Port 8086`.
Python-Alternative: `uv run python scripts/dev.py start --manual-auth`.

Die Anmeldung verwendet ausschließlich ein synthetisches Entwicklerkonto ohne
Passwort im isolierten lokalen Datenbestand. Produktions-/NAS-Anmeldung bleibt
unverändert. Bei manuellen Loginproblemen Datenbank, Browseradresse/Cookies und
Anmeldesperre prüfen. Ein belegter Port wird nicht automatisch freigeschossen.
Bei fehlenden Ressourcen zeigt die Diagnose die sichere Endpunktkategorie;
statische Dateien werden beim Start gesammelt. Kein automatisches Code-Neuladen:
nach Änderungen bewusst neu starten.
