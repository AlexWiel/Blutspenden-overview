# Hinweise für Arbeiten in diesem Repository

## Zweck und aktueller Stand

Das Projekt soll eine statische GitHub-Pages-Website für Blutspendetermine des
Österreichischen Roten Kreuzes in Klagenfurt am Wörthersee und Tamsweg bereitstellen.
Angezeigt werden sollen kommende Termine und beendete Termine aus einem rollierenden
Kalendermonat. Die Monatsgrenze ist der gleiche Kalendertag des Vormonats ab lokaler Mitternacht,
bei kürzerem Vormonat auf dessen letzten Tag gekürzt.

Quellenrecherche, manueller Datenimport, validierter JSON-Bestand und lokales
Archiv sind implementiert. Website und Deployment sind noch nicht implementiert.
`PLAN.md` beschreibt die Phasen und ihren Fortschritt;
`docs/phase-1-datenquelle.md` enthält die belegten Erkenntnisse zur Quelle.
Geplante Komponenten nicht als bereits vorhanden beschreiben.

## Repository-Struktur

| Pfad | Inhalt |
| --- | --- |
| `README.md` | Kurze Projektbeschreibung |
| `PLAN.md` | Aufgaben, Abnahmekriterien, Entscheidungen und offene Punkte |
| `docs/phase-1-datenquelle.md` | Quellenprüfung, Beispieltermine und bekannte Grenzen |
| `scripts/probe_source.py` | Manueller Phase-1-Live-Check der öffentlichen Quelle |
| `blutspenden/` | Quellabruf, ICS-Normalisierung, Archiv und CLI |
| `tests/` | Offline-Tests mit `unittest` |
| `data/appointments.json`, `data/status.json` | Erzeugter Terminbestand und separater Abrufstatus |
| `docs/phase-2-import.md` | Datenformat, Bedienung und Fehler-/Archivregeln |
| `.gitignore` | Vorlage mit Jekyll-/GitHub-Pages-Einträgen |

Die `.gitignore` allein belegt keinen Jekyll- oder Ruby-Stack. Es gibt derzeit
keinen `Gemfile`, kein `package.json`, keine Python-Abhängigkeitsdatei, keinen
Lockfile und keine CI-Konfiguration unter `.github/workflows/`.

## Tech-Stack

- Vorhanden: Python 3 mit ausschließlich Standardbibliothek, insbesondere
  `urllib.request`, `HTMLParser`, `json`, `zoneinfo` und `unittest`.
- Die CLI verwendet `fcntl` für die Schreibsperre und setzt Linux/Unix voraus.
- `zoneinfo` setzt Python 3.9 oder neuer sowie verfügbare IANA-Zeitzonendaten
  für `Europe/Vienna` voraus. Eine Python-Version ist im Repository nicht gepinnt.
- Geplant: HTML, CSS und JavaScript ohne Framework; der vorhandene Python-Importer liefert
  JSON. Automatische Aktualisierung und Veröffentlichung über GitHub Actions
  sind noch geplant.
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
Es gibt derzeit keinen Website-Build, Entwicklungsserver, Linter oder Deployment-
Befehl. Der vorhandene Test-Runner ist `unittest`; kein `pytest`, `npm` oder Bundler
ist eingerichtet. Reine Dokumentationsänderungen erfordern keinen Live-Abruf.
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
