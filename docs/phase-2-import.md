# Phase 2: Abruf, Datenformat und Archiv

## Bedienung

Voraussetzungen: Python 3.9 oder neuer mit IANA-Zeitzonendaten für
`Europe/Vienna`, Linux beziehungsweise ein Unix-System mit `fcntl`, sowie
HTTPS-Zugriff auf `termine.blut.at`. Es werden ausschließlich Python-Standardmodule
verwendet; keine Paketinstallation, Zugangsdaten oder externen Dienste nötig.

Aus dem Repository-Hauptverzeichnis:

```sh
python3 -m blutspenden --output-dir data
python3 -m unittest discover -s tests -v
```

Der Import ist manuell. Er startet keine Website, richtet keinen Zeitplan ein und
veröffentlicht keine Daten. Die Konfiguration von GitHub Actions gehört zu Phase 4.
Der vorhandene Phase-1-Nachweis bleibt separat verfügbar:

```sh
python3 scripts/probe_source.py
```

`--output-dir` kann auf ein anderes lokales Verzeichnis zeigen. Der Import schreibt
`appointments.json` sowie `status.json`. Eine ignorierte `.update.lock` verhindert
überlappende Schreibläufe; das Betriebssystem gibt die Sperre auch nach einem
Prozessabbruch frei. Die Lock-Datei selbst kann im Verzeichnis bestehen bleiben.

## Abruf und Fehlerbehandlung

Der Client durchsucht beide Städte mit den nachgewiesenen `search_form`-Parametern,
folgt den tatsächlich verlinkten Ergebnisseiten und liest ausschließlich die auf
den Detailseiten verlinkten ICS-Exporte. Stadtfilter müssen bei jeder Folgeseite
erhalten bleiben. Seitenlimit und Schleifenerkennung verhindern unbegrenzte Abrufe;
das Erreichen eines Limits gilt als Fehler, nicht als vollständiges Ergebnis.

Requests erfolgen sequenziell, mit mindestens einer Sekunde Abstand zwischen ihren
Startzeitpunkten. Standard: 25 Sekunden Timeout pro Request, höchstens zwei
Wiederholungen bei temporären Netzwerkfehlern beziehungsweise HTTP 429, 500, 502,
503 oder 504. `Retry-After` wird berücksichtigt; bei mehr als 60 Sekunden verlangter
Pause wird der Lauf abgebrochen, statt vorzeitig weiterzumachen. Antworten sind auf
2 MiB begrenzt. Proxy und TLS-Prüfung bleiben aktiv. Nur bekannte HTTPS-Quellenpfade
auf `termine.blut.at` sind zulässig, auch bei Weiterleitungen.

Ein erfolgreicher Import setzt erfolgreiche Abrufe beider Städte voraus. Eine
abgeschnittene oder unverständliche HTML-/Kalenderantwort ist kein Nulltreffer.
Leere Suchergebnisse werden nur mit den erwarteten Ergebniscontainern und der
expliziten offiziellen Nulltreffer-Meldung angenommen. Nachbarorte werden anhand
der Kartenangaben ausgefiltert; für importierte Kalender werden Ortsname und PLZ
nochmals geprüft. Die erlaubten Klagenfurt-PLZ sind 9020, 9061 und 9073, jeweils nur
mit der Ortsbezeichnung Klagenfurt oder Klagenfurt am Wörthersee; Tamsweg hat 5580.
Weitere Ortsvarianten werden nicht stillschweigend zugeordnet.

Bei Abruf-, Parsing- oder Validierungsfehlern bleibt ein bestehendes
`appointments.json` bytegenau unverändert. Der Fehler wird in `status.json`
vermerkt; der Prozess endet mit Exit-Code 1. Ohne vorherigen Bestand wird bei einem
Fehler keine leere Termindatei erzeugt. Beschädigte vorhandene Dateien werden nicht
stillschweigend zurückgesetzt.

Termindatei und Statusdatei werden jeweils über eine temporäre Datei im selben
Verzeichnis mit anschließendem `os.replace` atomar ersetzt. Sie bilden keine
gemeinsame Dateisystemtransaktion: Bei einem Abbruch zwischen beiden Schreibvorgängen
kann der Status älter sein als der gültige Terminbestand. Verbraucher müssen die
Zeitstempel beider Dateien berücksichtigen. Ein Schreibfehler beim Status nach
bereits erfolgreichem Ersetzen der Termine wird nicht als erfolgreicher Lauf gemeldet.

## Datenformat Version 1

`appointments.json` enthält folgende Felder:

| Feld | Bedeutung |
| --- | --- |
| `schema_version` | Ganzzahl `1` |
| `source` | `https://termine.blut.at` |
| `last_successful_fetch` | Zeitpunkt des letzten vollständig erfolgreichen Laufs als ISO-Zeitstempel mit Offset |
| `archive_started_at` | Zeitpunkt des ersten erfolgreichen Imports; bleibt erhalten |
| `history_start` | Untere Grenze des gewünschten Rückblicks, nicht eine Zusicherung vollständiger Historie |
| `appointments` | Nach Zeitpunkt und ID sortierte Liste der gespeicherten Zeitfenster |

Jedes Zeitfenster hat diese Felder:

| Feld | Typ und Bedeutung |
| --- | --- |
| `id`, `uid` | Zeichenketten; ID ist `rotes-kreuz:` plus Kalender-UID |
| `source_url`, `calendar_url` | Offizielle Detail- beziehungsweise ICS-URL |
| `source_event_id` | Slug der Detail-URL |
| `city` | `Klagenfurt am Wörthersee` oder `Tamsweg` |
| `venue` | Veranstaltungsort |
| `address` | Straßen-/Adressanteil aus `LOCATION` |
| `postal_code`, `locality` | Vierstellige PLZ und ursprüngliche Ortsbezeichnung |
| `starts_at`, `ends_at` | ISO-Zeitstempel in Europe/Vienna; unbekanntes Ende ist `null` |
| `status` | Expliziter Quellstatus: `confirmed`, `cancelled` oder `tentative` |
| `first_seen_at` | Erster erfolgreicher Abruf dieses Eintrags |
| `last_seen_at` | Letzter erfolgreicher Abruf, in dem er enthalten war |
| `last_changed_at` | Letzte Änderung der gespeicherten fachlichen Quellfelder |
| `availability` | `listed` beim letzten Abruf enthalten, sonst `not_listed` |
| `verification_status` | `unklar` bei verschwundenen Terminen, `gelistet` bei aktuellen Einträgen, `abgesagt` bei expliziter Absage |
| `verification_url` | Offizielle Detailseite zur manuellen Prüfung (identisch mit `source_url`) |
| `verification_search_url` | Offizielle, auf Stadt und Bundesland gefilterte Terminsuche als Alternative |

Adressen werden aus dem beobachteten `LOCATION`-Format extrahiert; unvollständige
Adressen, unzulässige URLs, nicht unterstützte Städte und widersprüchliche Daten
führen zum Abbruch. Zeilenfaltung und iCalendar-Textescaping werden verarbeitet.
Mehrere `VEVENT`s mit verschiedenen UIDs bleiben getrennte Zeitfenster.
Wiederholungsregeln, Ganztagstermine und `DURATION` sind derzeit nicht unterstützt
und werden ausdrücklich abgewiesen. Der manuelle Phase-1-Probeparser ist kein
Ersatz für diesen produktiven Parser.

Quellzeiten ohne `TZID` oder `Z` werden gemäß der belegten Quellenkonvention als
`Europe/Vienna` interpretiert. UTC und explizite Zeitzonen werden umgerechnet.
Nicht existierende oder mehrdeutige lokale Uhrzeiten beim Sommerzeitwechsel werden
nicht geraten. Ein fehlendes Ende bleibt unbekannt; ein fehlender Quellstatus wird
nicht als Bestätigung erfunden.

## Dubletten, Änderungen und Archiv

Identische Kalender-UIDs werden dedupliziert. Widersprüchliche Einträge mit derselben
UID oder konkurrierende UIDs für dieselbe Quellen-URL und Startzeit brechen den
Import ab. Falls eine UID wechselt, wird eine bestehende eindeutige Kombination
von Quellen-URL und Startzeit als Zuordnung verwendet. Unterschiedliche Zeitfenster
derselben Detailseite werden nicht pauschal zusammengelegt. Eine gleichzeitige
Änderung von UID, URL und Startzeit lässt sich ohne Quellgarantie nicht sicher
zuordnen; alte Einträge bleiben dann gegebenenfalls als nicht mehr gelistet erhalten.

Bei unveränderten fachlichen Feldern ändern sich nur Abruf-/Sichtungszeitpunkte.
Der transportabhängige `DTSTAMP` fließt weder in die Daten noch in die
Änderungserkennung ein. Nur ein ausdrücklich gelieferter Absagestatus wird
übernommen. Ein verschwundener Termin bleibt mit `availability=not_listed` und
seinem letzten Quellstatus gespeichert und erhält `verification_status=unklar`.
Eine ausdrückliche Quellabsage behält Vorrang: Sie erhält auch nach Verschwinden
`verification_status=abgesagt`. Taucht ein Termin wieder auf, wird der Prüfstatus
neu aus Quelle und Verfügbarkeit bestimmt. Der Wechsel allein verändert nicht
`last_changed_at`, da keine Änderung der fachlichen Quellfelder nachgewiesen ist.

`verification_url` führt direkt zur offiziellen Detailseite. Falls diese nicht
mehr verfügbar ist, führt `verification_search_url` zur Suche für Klagenfurt oder
Tamsweg einschließlich Bundesland. Diese Suche bietet laut Quellenprüfung keinen
historischen Rückblick; sie kann daher nicht jeden verschwundenen vergangenen
Termin klären. Der Prüfstatus bleibt eine Kennzeichnung der Unsicherheit, keine
Behauptung, dass ein Termin stattgefunden hat oder abgesagt wurde. Beim Aufbau der
Website in Phase 3 sollen beide Links mit verständlichen Beschriftungen erscheinen.

Das erste lokale Format Version 1 ohne diese drei abgeleiteten Prüffelder wird beim
Laden nach vollständiger Validierung im Speicher ergänzt. Archiv- und Abrufzeiten
bleiben erhalten. Unvollständige oder widersprüchliche Prüffelder werden als Fehler
behandelt. Die Datei wird erst beim nächsten erfolgreichen Speichern ersetzt.

Der Rückblick beginnt am gleichen Kalendertag des Vormonats um 00:00 Uhr in
`Europe/Vienna`, bei kürzerem Vormonat am letzten Monatstag. Beispiel: am 31.03.2027
beginnt er am 28.02.2027, am 31.03.2028 am 29.02.2028. Termine mit Ende genau auf
der Grenze bleiben erhalten. Bei unbekanntem Ende wird ausschließlich zur
Aufbewahrung konservativ die nächste lokale Mitternacht verwendet; `ends_at`
bleibt trotzdem `null`. Zukünftige Termine bleiben erhalten, auch wenn sie nicht
mehr gelistet sind. Ältere beendete Termine werden aus dem Bestand entfernt.

Die öffentliche Quelle liefert über die geprüfte Suche keinen vergangenen Monat.
Das Archiv wächst ab `archive_started_at`; `history_start` allein bedeutet keine
lückenlose Abdeckung des ersten Monats. Erfundenes Auffüllen ist ausgeschlossen.

## Aktualisierungsstatus

`status.json` enthält `schema_version`, `last_attempt`, `last_successful_fetch`,
`state`, `fetched_counts` und `error`:

- `state=ok`: vollständiger gültiger Abruf mit mindestens einem Zeitfenster.
- `state=empty`: vollständiger gültiger Abruf beider Städte ohne aktuelle Treffer.
  Archivierte Einträge können trotzdem in `appointments.json` vorhanden sein.
- `state=error`: keine gültige neue Gesamtantwort; `fetched_counts=null` und eine
  allgemeine Fehlermeldung plus `error_type`. Keine Antworttexte, Cookies oder
  Zugangsdaten werden in den Status übernommen.

Bei erfolgreichem Lauf enthält `fetched_counts` die Anzahl abgerufener Zeitfenster
je kanonischer Stadt und `error=null`. Beim ersten fehlgeschlagenen Lauf oder
beschädigtem Altbestand ist kein vertrauenswürdiger erfolgreicher Datenzeitpunkt
verfügbar; `last_successful_fetch` ist dann `null`.

Die zwei Dateien werden jeweils atomar ersetzt, bilden aber keine gemeinsame
Dateisystemtransaktion. Falls nach erfolgreichem Schreiben des Datenbestands das
Schreiben des Status scheitert, beendet sich die CLI mit einem Fehler; die neue
Datendatei bleibt gültig. Verbraucher sollten ihren `last_successful_fetch` mit
dem Status vergleichen und einen zeitlich abweichenden Status als veraltet behandeln.

## Validierung und offene Grenzen

Die Offline-Suite prüft unter anderem Stadt-/PLZ-Filter, Pagination, echte Leere
gegen Fehler, Retries, unvollständige Antworten, ICS-Sonderfälle, Sommerzeit,
UID-Konflikte, Updates, Absagen, Verschwinden, Monatsgrenzen, atomare Schreibfehler,
beschädigte Bestände und konkurrierende Importläufe. Sie benötigt kein Netzwerk.

Die Live-Abnahme wird mit dem manuellen Import gegen beide Städte und einer
Wiederholung ohne Dubletten durchgeführt. Es gibt noch keine Website und keinen
Deploy-Workflow. Die im [Quellenbericht](phase-1-datenquelle.md) dokumentierte
Nutzungsgrundlage ist vor öffentlichem Betrieb weiterhin zu klären.

## Abnahme am 17.11.2026

- `python3 -m unittest discover -s tests -v`: **65 Tests bestanden**, keine
  übersprungenen Tests, ohne Netzwerk.
- Zwei vollständige manuelle Live-Importe nach `data/`: beide erfolgreich mit je
  fünf Zeitfenstern für Klagenfurt und einem für Tamsweg, insgesamt sechs
  eindeutigen IDs. Die Wiederholung erhielt `first_seen_at` und `last_changed_at`
  und aktualisierte `last_seen_at` ohne Dubletten.
- `appointments.json` erneut mit `load_dataset` validiert; Status `ok`.
- Archivbeginn 17.11.2026 gegen 10:45 Uhr Europe/Vienna, letzter geprüfter
  erfolgreicher Lauf gegen 10:47 Uhr. Ein vergangener voller Monat ist damit
  ausdrücklich noch nicht abgedeckt.

Es wurde keine Website bereitgestellt, keine Umgebung geändert und nichts
veröffentlicht. Die Dateien sind für die weitere Umsetzung lokal vorhanden.

## Ergänzung: unklare Termine und manuelle Prüfung

70 Offline-Tests bestanden nach Ergänzung der Prüffelder, einschließlich
Verschwinden, Wiederauftauchen, Vorrang bestätigter Absagen, Stadtfilter in den
Prüflinks und Übernahme des ursprünglichen lokalen Archivs. Die vorhandenen sechs
Live-Einträge wurden ohne neuen Quellabruf um die abgeleiteten Prüffelder ergänzt;
die bestehenden Sichtungs- und Archivzeitpunkte blieben unverändert.
