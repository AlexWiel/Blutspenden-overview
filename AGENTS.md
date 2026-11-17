# Hinweise für Arbeiten in diesem Repository

## Zweck und aktueller Stand

Das Projekt soll eine statische GitHub-Pages-Website für Blutspendetermine des
Österreichischen Roten Kreuzes in Klagenfurt am Wörthersee und Tamsweg bereitstellen.
Angezeigt werden sollen kommende Termine und beendete Termine aus einem rollierenden
Kalendermonat. Die genaue Monatsgrenze ist noch festzulegen und zu testen.

Aktuell sind die Quellenrecherche und ein ausführbares Prüfskript vorhanden.
Website, produktiver Import, JSON-Datenbestand, Archiv und Deployment sind noch
nicht implementiert. `PLAN.md` beschreibt die Phasen und ihren Fortschritt;
`docs/phase-1-datenquelle.md` enthält die belegten Erkenntnisse zur Quelle.
Geplante Komponenten nicht als bereits vorhanden beschreiben.

## Repository-Struktur

| Pfad | Inhalt |
| --- | --- |
| `README.md` | Kurze Projektbeschreibung |
| `PLAN.md` | Aufgaben, Abnahmekriterien, Entscheidungen und offene Punkte |
| `docs/phase-1-datenquelle.md` | Quellenprüfung, Beispieltermine und bekannte Grenzen |
| `scripts/probe_source.py` | Manueller, lesender Live-Check der öffentlichen Quelle |
| `.gitignore` | Vorlage mit Jekyll-/GitHub-Pages-Einträgen |

Die `.gitignore` allein belegt keinen Jekyll- oder Ruby-Stack. Es gibt derzeit
keinen `Gemfile`, kein `package.json`, keine Python-Abhängigkeitsdatei, keinen
Lockfile und keine CI-Konfiguration unter `.github/workflows/`.

## Tech-Stack

- Vorhanden: Python 3 mit ausschließlich Standardbibliothek, insbesondere
  `urllib.request`, `HTMLParser`, `json` und `zoneinfo`.
- `zoneinfo` setzt Python 3.9 oder neuer sowie verfügbare IANA-Zeitzonendaten
  für `Europe/Vienna` voraus. Eine Python-Version ist im Repository nicht gepinnt.
- Geplant: HTML, CSS und JavaScript ohne Framework; ein Python-Importer erzeugt
  JSON, GitHub Actions aktualisiert und veröffentlicht auf GitHub Pages.
- Zusätzliche Frameworks oder Paketmanager nur einführen, wenn die konkrete
  Aufgabe sie benötigt. Bei neuen Abhängigkeiten Installation dokumentieren.

## Befehle und Validierung

Alle folgenden Befehle im Repository-Hauptverzeichnis ausführen.

```sh
python3 scripts/probe_source.py
```

Das ist der einzige vorhandene funktionale Prüfaufruf. Er benötigt HTTPS-Zugriff
auf `termine.blut.at`, verwendet vorhandene Proxy- und TLS-Einstellungen und gibt
einen JSON-Bericht auf stdout aus. Er vergleicht für jede Stadt eine Suchkarte mit
Detailseite und Einzeltermin-ICS und prüft die Ablehnung einer historischen Suche.
Er reserviert keine Termine und schreibt keinen Datenbestand.

Exit-Code 0 bedeutet, dass diese Stichproben und das erwartete Quellenverhalten
geprüft wurden. Netzwerkfehler, geändertes HTML, fehlende zukünftige Stichproben
oder veränderte Validierung können den Check fehlschlagen lassen. Eine Stadt ohne
zukünftigen Termin ist nicht automatisch ein Anwendungsfehler. Der Check ist weder
ein vollständiger Import noch ein Ersatz für eine lokale automatisierte Testsuite.

```sh
git diff --check
```

Diesen lokalen Check für Whitespace-Fehler vor Abschluss von Änderungen verwenden.
Es gibt derzeit **keinen Build-, Entwicklungsserver-, Lint- oder Unit-Test-Befehl**
und keinen konfigurierten Test-Runner. Keine erfundenen `npm`, `pytest`, Bundler-
oder Deployment-Befehle ausführen oder als bestehende Projektbefehle dokumentieren.
Reine Dokumentationsänderungen erfordern keinen erneuten Live-Abruf. Bei Änderungen
am Prüfskript den relevanten Live-Check ausführen, sofern der Netzwerkzugriff besteht,
und Ergebnis oder konkreten Blocker berichten.

## Regeln für Termindaten und weitere Implementierung

- Vor Änderungen am Datenabruf den Quellenbericht lesen. Technische Richtung:
  öffentliche HTML-Suche zur Entdeckung von Detail-URLs und die dort verlinkten
  Kalender unter `/termine/<slug>/ics`. Eine dokumentierte API oder ein Gesamtfeed
  ist nicht nachgewiesen.
- Keine Termindaten erfinden. Abruffehler, ungültige Suchanfragen und echte leere
  Ergebnisse getrennt behandeln. Letzten gültigen Datenstand bei Fehlern erhalten.
- Klagenfurt und Klagenfurt am Wörthersee normalisieren; Veranstaltungsort und
  Bundesland prüfen. Pagination und mehrere Zeitfenster müssen beim produktiven
  Import berücksichtigt werden; das Prüfskript deckt diese nicht vollständig ab.
- `Europe/Vienna` einschließlich Sommerzeit verwenden. Beobachtete ICS-Zeiten
  haben weder `TZID` noch `Z` am Ereignisfeld; nicht pauschal als UTC interpretieren.
- `UID` und Quellen-URL bewahren; dauerhafte ID-Stabilität ist nicht garantiert.
  `DTSTAMP` nicht als zuverlässigen inhaltlichen Änderungszeitpunkt verwenden.
- Historische Suche wird laut Quellenprüfung serverseitig abgelehnt. Ein Archiv
  muss ab dem ersten Import entstehen; vollständige anfängliche Historie ist nicht
  nachgewiesen. Verschwundene Einträge sind keine bestätigten Absagen.
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
