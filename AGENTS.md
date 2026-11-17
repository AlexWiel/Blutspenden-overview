# Hinweise für Arbeiten in diesem Repository

## Zweck und aktueller Stand

Das Projekt soll eine statische GitHub-Pages-Website für Blutspendetermine des
Österreichischen Roten Kreuzes in Klagenfurt am Wörthersee und Tamsweg bereitstellen.
Angezeigt werden sollen kommende Termine und beendete Termine aus einem rollierenden
Kalendermonat. Die Monatsgrenze ist der gleiche Kalendertag des Vormonats ab lokaler Mitternacht,
bei kürzerem Vormonat auf dessen letzten Tag gekürzt.

Quellenrecherche, manueller Datenimport, validierter JSON-Bestand und lokales
Archiv und statische Website sind implementiert. GitHub-Pages-Deployment von
`main` ist eingerichtet, einschließlich täglichem und manuellem Datenabruf.
`PLAN.md` beschreibt die Phasen und ihren Fortschritt;
`docs/phase-1-datenquelle.md` enthält die belegten Erkenntnisse zur Quelle.
Geplante Komponenten nicht als bereits vorhanden beschreiben.

## Repository-Struktur

| Pfad | Inhalt |
| --- | --- |
| `README.md` | Projektbeschreibung, Start- und Testbefehle |
| `index.html`, `assets/` | Statische Website, Gestaltung, DOM-Rendering und Datums-/Filterlogik |
| `PLAN.md` | Aufgaben, Abnahmekriterien, Entscheidungen und offene Punkte |
| `docs/phase-1-datenquelle.md` | Quellenprüfung, Beispieltermine und bekannte Grenzen |
| `scripts/probe_source.py` | Manueller Phase-1-Live-Check der öffentlichen Quelle |
| `blutspenden/` | Quellabruf, ICS-Normalisierung, Archiv und CLI |
| `tests/` | Offline-Tests mit `unittest` |
| `data/appointments.json`, `data/status.json` | Erzeugter Terminbestand und separater Abrufstatus |
| `docs/phase-2-import.md` | Datenformat, Bedienung und Fehler-/Archivregeln |
| `docs/phase-3-website.md` | Website-Verhalten und Browserprüfung |
| `.github/workflows/pages.yml` | Test, Paketierung und Pages-Deployment von `main` |
| `blutspenden/build_site.py` | Paketiert ausschließlich öffentliche Website-Dateien |
| `docs/github-pages.md` | Veröffentlichungsablauf und aktueller Datenstand |
| `docs/phase-5-pruefung.md`, `docs/phase-6-abschluss.md` | Gesamtprüfung, Abschluss und verbleibende Grenzen |
| `.gitignore` | Vorlage mit Jekyll-/GitHub-Pages-Einträgen |

Die `.gitignore` allein belegt keinen Jekyll- oder Ruby-Stack. Es gibt derzeit
keinen `Gemfile`, kein `package.json`, keine Python-Abhängigkeitsdatei, keinen
Lockfile. Die Pages-CI liegt unter `.github/workflows/pages.yml`.

## Tech-Stack

- Vorhanden: Python 3 mit ausschließlich Standardbibliothek, insbesondere
  `urllib.request`, `HTMLParser`, `json`, `zoneinfo` und `unittest`.
- Die CLI verwendet `fcntl` für die Schreibsperre und setzt Linux/Unix voraus.
- `zoneinfo` setzt Python 3.9 oder neuer sowie verfügbare IANA-Zeitzonendaten
  für `Europe/Vienna` voraus. Eine Python-Version ist im Repository nicht gepinnt.
- Website: HTML, CSS und JavaScript-Module ohne Framework oder Build-Schritt;
  `assets/model.mjs` enthält reine Datenlogik, `assets/app.js` das DOM-Rendering.
  Node.js 18+ führt die JavaScript-Tests ohne npm-Abhängigkeiten aus.
- Optional für Browserprüfungen: Python Playwright und System-Chromium.
- Der Python-Importer liefert JSON. GitHub Actions veröffentlicht den gespeicherten
  Stand von `main`; Zeitplan- und manuelle Läufe aktualisieren vorher die Quelle
  und speichern das Archiv per Bot-Commit. Push-Läufe veröffentlichen ohne Abruf.
- Zusätzliche Frameworks oder Paketmanager nur einführen, wenn die konkrete
  Aufgabe sie benötigt. Bei neuen Abhängigkeiten Installation dokumentieren.

## Befehle und Validierung

Alle folgenden Befehle im Repository-Hauptverzeichnis ausführen.

```sh
python3 -m blutspenden --output-dir data
python3 -m unittest discover -s tests -v
```

Der erste Befehl ruft beide Städte vollständig ab und schreibt erst nach erfolgreicher
Validierung den Terminbestand. Er benötigt HTTPS-Zugriff auf `termine.blut.at`.
`--output-dir` erlaubt ein separates Verzeichnis für manuelle Prüfungen.
Der zweite Befehl führt die Offline-Suite ohne Netzwerkanfragen aus. Sie prüft
Parser, Pagination und HTTP-Fehler, Archivierung, Monats-/Sommerzeitgrenzen,
Dubletten und den Schutz gültiger Daten bei Abruf- oder Schreibfehlern.

```sh
python3 scripts/probe_source.py
```

Das ist der ursprüngliche manuelle Phase-1-Nachweis, kein vollständiger Importer.
Er benötigt Live-Zugriff und kann bei fehlenden zukünftigen Stichproben oder
verändertem Quellenverhalten fehlschlagen. Ein solcher Fehler ist nicht automatisch
ein Anwendungsfehler. Details zu den Prüfgrenzen stehen im Quellenbericht.

```sh
git diff --check
```

Diesen lokalen Check für Whitespace-Fehler vor Abschluss von Änderungen verwenden.
Die statische Website benötigt keinen Build-Schritt. Entwicklungsserver:

```sh
python3 -m http.server 8000 --bind 0.0.0.0
node --test tests/test_web_model.mjs
python3 -m unittest discover -s tests -p 'test_web_browser.py' -v
```

Der zweite Befehl prüft die JavaScript-Datenlogik, der dritte optional die Website
mit Python Playwright und einem `chromium`/`chromium-browser` im PATH. Fehlende
Browser-Voraussetzungen führen zu expliziten Skips; diese nicht als bestanden
melden. Python-Test-Discovery führt die Browserfälle ebenfalls aus, wenn verfügbar.
Kein `pytest`, npm oder Bundler ist eingerichtet. Pages wird über den Workflow auf
`main` veröffentlicht; Details in `docs/github-pages.md`. Paketierung separat prüfen:

```sh
python3 -m blutspenden.build_site --output-dir /tmp/blutspenden-pages-site
```

Das Ziel muss leer oder neu und außerhalb des Repositorys sein. Der Workflow
veröffentlicht nur das Paket, niemals das gesamte Repository. Build-Job nur mit
Leserechten; Pages-/OIDC-Schreibrechte auf den Deployment-Job und
`contents: write` auf den Archiv-Refresh-Job begrenzen. Bestehende
Branch-Beschränkungen der Pages-Umgebung erhalten. Reine Dokumentationsänderungen
lösen keine Bereitstellung aus. `scripts/persist_refresh.sh` darf ausschließlich
die beiden JSON-Dateien committen; niemals Force-Push oder blindes Rebase eines
Archivkonflikts einführen. Der gleiche Workflow muss den vom Refresh-Job
ausgegebenen SHA veröffentlichen, weil Bot-Pushes keinen weiteren Workflow starten.
Quellfehlerstatus mit erhaltenen Terminen veröffentlichen und den Lauf danach als
fehlgeschlagen kennzeichnen.
Bei Website-Änderungen JavaScript- und Browserprüfungen ausführen, insbesondere
Datenfehler, mobile Ansichten, Tastatur und den Projekt-Unterpfad prüfen.
Öffentliche Termindaten als untrusted behandeln: DOM über `textContent` erstellen,
Quelllinks validieren, keine ungeprüften HTML-Fragmente einfügen. Alle Asset- und
JSON-Pfade relativ halten; Browserdatenzustände dürfen keine echten Nulltreffer
vortäuschen. Unklare und abgesagte Termine nicht als nächsten Termin hervorheben.
Reine Dokumentationsänderungen erfordern keinen Live-Abruf.
Bei Änderungen am Importer die relevanten Offline-Tests ausführen und bei Änderungen
an Quellabruf oder Kalendernormalisierung zusätzlich einen Live-Import, sofern der
Netzwerkzugriff besteht. Ergebnis oder konkreten Blocker berichten. Für Fehlerfälle
Mock-Antworten verwenden; die öffentliche Quelle nicht absichtlich überlasten.

## Regeln für Termindaten und weitere Implementierung

- Vor Änderungen am Datenabruf den Quellenbericht lesen. Technische Richtung:
  öffentliche HTML-Suche zur Entdeckung von Detail-URLs und die dort verlinkten
  Kalender unter `/termine/<slug>/ics`. Eine dokumentierte API oder ein Gesamtfeed
  ist nicht nachgewiesen.
- Keine Termindaten erfinden. Abruffehler, ungültige Suchanfragen und echte leere
  Ergebnisse getrennt behandeln. Letzten gültigen Datenstand bei Fehlern erhalten.
- Klagenfurt und Klagenfurt am Wörthersee normalisieren; Veranstaltungsort und
  Bundesland prüfen. Pagination und mehrere Zeitfenster müssen beim produktiven
  Import berücksichtigt werden; der Phase-1-Probecheck deckt sie nicht vollständig ab.
- `Europe/Vienna` einschließlich Sommerzeit verwenden. Beobachtete ICS-Zeiten
  haben weder `TZID` noch `Z` am Ereignisfeld; nicht pauschal als UTC interpretieren.
- `UID` und Quellen-URL bewahren; dauerhafte ID-Stabilität ist nicht garantiert.
  `DTSTAMP` nicht als zuverlässigen inhaltlichen Änderungszeitpunkt verwenden.
- Historische Suche wird laut Quellenprüfung serverseitig abgelehnt. Ein Archiv
  wächst ab dem ersten Import; vollständige anfängliche Historie ist nicht
  nachgewiesen. Verschwundene Einträge erhalten `verification_status=unklar`;
  explizite Absagen haben Vorrang (`abgesagt`). Die offiziellen Prüflinks
  `verification_url` und `verification_search_url` für die manuelle Prüfung
  beibehalten. Der Quellstatus wird dadurch nicht überschrieben.
- Die Nutzungsgrundlage für öffentliche Weiterverwendung ist vor öffentlichem
  Betrieb zu klären; das verlinkte Impressum enthält eine Beschränkung. Details
  stehen im Quellenbericht. Keine Kontaktaufnahme ohne entsprechenden Auftrag.
- Requests begrenzen, Timeouts und Backoff vorsehen; TLS-Prüfung und Cloud-Proxy
  beibehalten. Einmal täglicher Abruf ist eine Planung, keine bestätigte Quellvorgabe.

## Arbeitsweise

Änderungen auf die beauftragte Aufgabe begrenzen und vorhandene lokale Änderungen
erhalten. Dokumentation und Benutzertexte auf Deutsch halten; vorhandene englische
Python-Bezeichner konsistent fortführen. Aufgaben in `PLAN.md` erst nach belegter
Prüfung abhaken und relevante neue Erkenntnisse dort beziehungsweise im Quellenbericht
festhalten. Bei neuen Build-, Test- oder Startbefehlen diese Datei und die README
aktualisieren. Bei späterem Pages-Deployment den Projektpfad
`/Blutspenden-overview/` berücksichtigen.

## Automatische Aktualisierung

Der Workflow läuft täglich ab 05:17 UTC (06:17 Wien im Winter, 07:17 im Sommer).
Manuelle Läufe aktualisieren standardmäßig ebenfalls Daten (`refresh_data=true`);
mit `false` sowie bei normalen Code-Pushes wird nur der gespeicherte Stand deployt.
`scripts/persist_refresh.sh` speichert ausschließlich die zwei JSON-Dateien auf
`main`, ohne Force-Push und ohne fremde vorgemerkte Dateien zu committen. Bei einem
konkurrierenden Remote-Commit schlägt das Speichern fehl; nicht blind überschreiben.
GitHub-Token-Commits starten keinen Folgeworkflow, deshalb muss derselbe Lauf den
exportierten Daten-Commit bauen und deployen. Bei Quellfehlern werden gültige alte
Daten mit neuem Fehlerstatus veröffentlicht; ein separater Abschlussjob macht den
Workflow rot. Fehlerfälle offline testen, nicht absichtlich auf der Live-Seite erzeugen.
Browserfixtures unter `tests/fixtures/` sind feste Teststände und dürfen nicht
unbesehen durch tägliche Produktdaten ersetzt werden. Beim Voraussetzungen-Link
nur die offizielle Zielseite verlinken, keine eigene medizinische Liste pflegen.
