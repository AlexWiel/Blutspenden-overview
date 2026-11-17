# Blutspenden-overview

GitHub-Pages-Übersicht über Blutspendetermine des Österreichischen Roten
Kreuzes in Klagenfurt am Wörthersee und Tamsweg, einschließlich eines monatlichen
Rückblicks. Datenimport, lokales Archiv und responsive Website sind implementiert.
Die Website ist veröffentlicht: https://alexwiel.github.io/Blutspenden-overview/
Neue Termine werden täglich über GitHub Actions abgerufen, archiviert und
anschließend veröffentlicht. Ein manueller Start ist ebenfalls möglich.

## Voraussetzungen und Datenimport

Python 3.9 oder neuer, Zeitzonendaten für `Europe/Vienna`, Linux/Unix mit `fcntl`
und HTTPS-Zugriff auf `termine.blut.at`. Keine zusätzlichen Python-Pakete nötig.
Alle Befehle im Repository-Hauptverzeichnis ausführen:

```sh
python3 -m blutspenden --output-dir data
```

Das schreibt `data/appointments.json` und `data/status.json`. Ein fehlgeschlagener
Abruf ersetzt den letzten gültigen Terminbestand nicht. Historische Daten wachsen
ab dem ersten Import; die Quelle liefert keinen vollständigen ersten Rückblickmonat.
Verschwundene Termine bleiben als „unklar“ gekennzeichnet und enthalten Links zur
offiziellen Detailseite und zur Stadtsuche für eine manuelle Prüfung. Explizite
Absagen bleiben als solche erhalten. Der Import startet keine Website und
veröffentlicht nichts.

## Website lokal starten

Die Website benötigt keinen Build-Schritt. Im Repository-Hauptverzeichnis:

```sh
python3 -m http.server 8000 --bind 0.0.0.0
```

Im Browser die Adresse des lokalen Servers öffnen. Die Website lädt die beiden
JSON-Dateien aus `data/`. Sie bietet Stadtfilter, kommende und laufende Termine,
einen getrennten Monatsrückblick und Prüflinks für unklare Termine. Ladefehler,
fehlender Aktualisierungsstatus und Daten älter als 36 Stunden werden angezeigt.
Alle Datumsangaben verwenden `Europe/Vienna`, unabhängig von der Browserzeitzone.
Die Anwendung verwendet relative Pfade und funktioniert auch unter dem
GitHub-Pages-Projektpfad `/Blutspenden-overview/`.

Die Anzeige eines gespeicherten Datenstands führt selbst keinen neuen Quellabruf
aus. Der tägliche Workflow läuft ab 05:17 UTC (Wien: 06:17 im Winter, 07:17 im
Sommer). Für einen zusätzlichen Abruf in GitHub Actions den Workflow manuell mit
aktivierter Option `refresh_data` starten; lokal ist der Import ebenfalls möglich. Die Seite ist als unabhängige
Übersicht gekennzeichnet; die offiziellen Angaben sind maßgeblich.

## Prüfen

```sh
python3 -m unittest discover -s tests -v
```

Die Python-Tests prüfen Import und Archiv. Falls das Python-Paket `playwright`
und ein Systembrowser `chromium` oder `chromium-browser` im PATH vorhanden sind,
werden außerdem Browserprüfungen auf einem temporären lokalen HTTP-Server
ausgeführt. Ohne diese optionalen Voraussetzungen sind die Browserfälle ausdrücklich
übersprungen, nicht bestanden. Sie fragen die öffentliche Quelle nicht ab.

Die JavaScript-Logik lässt sich mit Node.js (18 oder neuer) ohne npm-Pakete prüfen:

```sh
node --test tests/test_web_model.mjs
```

Die optionale Browser-Suite kann separat gestartet werden:

```sh
python3 -m unittest discover -s tests -p 'test_web_browser.py' -v
```

Mehr zur Website und ihren Prüfungen: [Phase 3](docs/phase-3-website.md).
Der ursprüngliche manuelle
Quellennachweis benötigt dagegen Live-Zugriff:

```sh
python3 scripts/probe_source.py
```

Ein zusätzlicher Build-Schritt ist für die statische Website nicht nötig.

## Veröffentlichung

Änderungen an Website oder Daten auf `main` werden nach erfolgreichen Tests über
GitHub Actions veröffentlicht. Ein manueller Lauf ist ebenfalls möglich. Bei Zeitplan- und manuellen Aktualisierungsläufen werden neue Termine vor der
Veröffentlichung abgerufen. Normale Code-Pushes veröffentlichen nur den gespeicherten
Stand. Bei Quellfehlern bleiben gültige Termine erhalten; die Website zeigt den
neuen Fehlerstatus an. Details: [GitHub Pages](docs/github-pages.md).

## Dokumentation

- [Projektplan](PLAN.md): Phasen, Aufgaben und Fortschritt.
- [Quellenprüfung](docs/phase-1-datenquelle.md): offizielle Suche, Kalenderexport und Einschränkungen.
- [Import und Datenformat](docs/phase-2-import.md): Speicherung, Fehlerstatus, Zeitzonen und Archivgrenze.
- [Website](docs/phase-3-website.md): Darstellung, Datenzustände und Browserprüfungen.
- [Hinweise für Coding-Agenten](AGENTS.md).

Die Nutzungsgrundlage für eine öffentliche Weiterveröffentlichung der Quelldaten
ist vor öffentlichem Betrieb zu klären; Details stehen im Quellenbericht.
