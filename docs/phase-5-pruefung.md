# Phase 5: Funktion und Datenqualität

Prüfung am 17. November 2026 auf Commit `6ec0ba0`.

## Automatisierte Prüfungen

- `python3 -m unittest discover -s tests -v`: **89 Tests bestanden**, keine
  übersprungenen Fälle. Darin enthalten sind **12 echte Chromium-Browserprüfungen**
  und 77 Tests für Import, Kalender, Archiv, Paketierung und Workflow-Persistierung.
- `node --test tests/test_web_model.mjs`: **19 Tests bestanden**, keine Skips.

Die Suite prüft Stadtvarianten und Nachbargemeinden, Dubletten, inhaltliche
Aktualisierungen, verschwundene und abgesagte Termine sowie Archivaufbewahrung.
Datumsfälle umfassen Monatsenden, Schaltjahre, Jahreswechsel, Wiener Sommerzeit,
mehrdeutige beziehungsweise nicht vorhandene Ortszeiten, laufende Termine und
unbekannte Endzeiten. Ungültige HTML-/Kalenderantworten, HTTP-Fehler, Timeouts,
begrenzte Wiederholungen und erfolgreiche leere Ergebnisse werden offline geprüft.
Abruffehler erhalten den letzten gültigen Terminbestand bytegenau.

Im Browser geprüft: Projekt-Unterpfad, Stadtfilter, Rückblick, Quellfehler und
veraltete Daten, fehlender Status, kaputtes JSON, erneuter Versuch nach Netzfehler,
Sprunglink und Radio-Buttons per Tastatur, Voraussetzungen-Link und mobile Breiten
320/390/768 Pixel. Diese Prüfungen verwenden feste Fixtures für reproduzierbare
Sonderfälle; sie ersetzen keine Live-Quellenprüfung.

## Live-Quellenvergleich

`python3 scripts/probe_source.py` endete mit Exit-Code 0. Beide Suchseiten,
je eine offizielle Detailseite und deren ICS wurden erfolgreich verglichen:

| Stadt | Datum und Ortszeit | Ort und Adresse | UID |
| --- | --- | --- | --- |
| Klagenfurt | 18.11.2026, 09:00–13:00 | PÄDAG Klagenfurt, Hubertusstraße 1, 9020 Klagenfurt | `11841-1` |
| Tamsweg | 20.11.2026, 15:00–20:00 | Mittelschule, Lasabergweg 2, 5580 Tamsweg | `11762-1` |

Suchkarte, Detail und Kalender stimmen bei Stadt, Datum und Uhrzeit überein.
Die erste Suchseite enthielt fünf Klagenfurter und einen Tamsweger Eintrag.
Historische Suchanfragen werden weiterhin als ungültig abgewiesen.

Zusätzlich wurde der bestehende Archivbestand in ein separates Arbeitsverzeichnis
kopiert und dort mit `python3 -m blutspenden --output-dir work/phase-5/live-data`
vollständig aktualisiert: sechs abgerufene Zeitfenster, sechs gespeicherte Einträge,
Exit-Code 0. Alle fachlichen Datensatzfelder stimmen mit dem gespeicherten
Produktbestand überein; Sichtungszeitpunkte wurden beim Vergleich ausgenommen.
Die produktiven JSON-Dateien wurden für diese Prüfung nicht verändert.

## Tatsächlich paketierte Website unter dem Projektpfad

Ein mit `blutspenden.build_site.build_site` erzeugtes, unverändertes Pages-Paket
wurde temporär per HTTP unter `/Blutspenden-overview/` ausgeliefert und in Chromium
ohne abgefangene JSON-Antworten geöffnet. Ergebnis:

- HTML, `data/appointments.json` und `data/status.json` liefern HTTP 200.
- Die echten Daten werden gerendert; die Filter zeigen 6/5/1 kommende Termine.
- Termin- und Stadtsuchlinks führen auf den offiziellen Host `termine.blut.at`.
- Bei 320/390/768 Pixeln entsteht kein horizontaler Überlauf.
- Keine JavaScript-Seitenfehler.

Der aktuelle Direktaufruf der veröffentlichten Adresse
<https://alexwiel.github.io/Blutspenden-overview/> war aus dieser Umgebung blockiert:
Chromium meldet `net::ERR_TUNNEL_CONNECTION_FAILED`; der unabhängige HTTP-Versuch
meldet Proxy CONNECT 403. Deshalb ist die lokale Paketprüfung **kein neuer Nachweis
der aktuell öffentlich ausgelieferten Seite**. Frühere erfolgreiche Live-Prüfung
und Deployment-Nachweise sind in [GitHub Pages](github-pages.md) dokumentiert;
die aktuelle Einordnung steht im [Phase-6-Bericht](phase-6-abschluss.md).

## Grenzen

Keine vollständige Barrierefreiheitszertifizierung oder Prüfung aller Browser.
Eine echte Absage-Stichprobe ist nicht nachgewiesen; die Behandlung ist mit
synthetischen Offline-/Browserfällen geprüft. Das Archiv wächst seit dem ersten
Import und enthält keinen vollständigen anfänglichen Rückblickmonat. Die offene
Nutzungsgrundlage und Grenzen zur ID-Stabilität bleiben wie in der
[Quellenprüfung](phase-1-datenquelle.md) beschrieben bestehen.
