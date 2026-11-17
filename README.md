# Blutspenden-overview

Geplante GitHub-Pages-Übersicht über Blutspendetermine des Österreichischen Roten
Kreuzes in Klagenfurt am Wörthersee und Tamsweg, einschließlich eines monatlichen
Rückblicks. Der Datenimport mit lokalem Archiv ist implementiert; die Website und
automatische Veröffentlichung folgen in den nächsten Phasen.

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

## Prüfen

```sh
python3 -m unittest discover -s tests -v
```

Die automatisierten Tests laufen ohne Netzwerk. Der ursprüngliche manuelle
Quellennachweis benötigt dagegen Live-Zugriff:

```sh
python3 scripts/probe_source.py
```

Ein Build-System oder Entwicklungsserver für die Website ist noch nicht vorhanden.

## Dokumentation

- [Projektplan](PLAN.md): Phasen, Aufgaben und Fortschritt.
- [Quellenprüfung](docs/phase-1-datenquelle.md): offizielle Suche, Kalenderexport und Einschränkungen.
- [Import und Datenformat](docs/phase-2-import.md): Speicherung, Fehlerstatus, Zeitzonen und Archivgrenze.
- [Hinweise für Coding-Agenten](AGENTS.md).

Die Nutzungsgrundlage für eine öffentliche Weiterveröffentlichung der Quelldaten
ist vor öffentlichem Betrieb zu klären; Details stehen im Quellenbericht.
