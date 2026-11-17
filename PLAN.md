# Projektplan: Blutspendetermine für Klagenfurt und Tamsweg

## Ziel

Eine statische Website auf GitHub Pages zeigt aktuelle und kommende Blutspendetermine des Österreichischen Roten Kreuzes für Klagenfurt am Wörthersee und Tamsweg sowie die im vergangenen Monat beendeten Termine.

## Annahmen und technische Richtung

- „Im letzten Monat“ bezeichnet einen rollierenden Kalendermonat bis heute, nicht den vorherigen Kalendermonat. Die Grenze ist der gleiche Kalendertag des Vormonats ab 00:00 Uhr in `Europe/Vienna`, bei kürzerem Vormonat auf dessen letzten Tag gekürzt (implementiert und getestet).
- Gefiltert wird anhand des Veranstaltungsorts innerhalb der beiden Städte; Termine in Nachbargemeinden gehören zunächst nicht zum Umfang.
- Für Anzeige und Datumsberechnung gilt `Europe/Vienna`, einschließlich Sommerzeit.
- Die Website verwendet HTML, CSS und JavaScript ohne Framework. Ein Python-Skript erzeugt die Termindaten als JSON.
- GitHub Actions aktualisiert die Daten täglich und auf manuellen Wunsch und veröffentlicht die Seite auf GitHub Pages.
- Die Abrufmethode ist öffentliche HTML-Suche mit Pagination und offiziell verlinkten Einzeltermin-ICS; siehe Quellenbericht.

## Vorgehen

Die Phasen in dieser Reihenfolge bearbeiten. Aufgaben erst nach erfolgreicher Prüfung abhaken. Erkenntnisse, Entscheidungen und konkrete Blocker unten dokumentieren. Bei einem Blocker unabhängige Aufgaben fortsetzen; fehlende oder fehlerhafte Quelldaten niemals durch erfundene Termine ersetzen.

### 1. Offizielle Datenquelle prüfen

- [x] Offizielle Terminsuche des Österreichischen Roten Kreuzes für beide Städte ermitteln.
- [x] Dokumentierte Schnittstelle, Kalenderexport oder geeignete öffentliche Terminseiten untersuchen.
- [x] Nutzungsbedingungen, Abrufregeln und angemessene Abruffrequenz prüfen (Weiterverwendungsbeschränkung gefunden; Nutzungsgrundlage vor Veröffentlichung klären).
- [x] Verfügbarkeit von Datum, Beginn, Ende, Veranstaltungsort, Adresse, Quellenlink und stabiler Termin-ID prüfen (UID und Slug vorhanden; langfristige Stabilität nicht garantiert).
- [x] Klären, wie Änderungen, Absagen und historische Termine erkennbar sind (Grenzen dokumentiert; keine bestätigte Absage-Stichprobe).
- [x] Einen kleinen, reproduzierbaren Abruf für beide Städte durchführen und Ergebnisse mit den offiziellen Einträgen vergleichen.
- [x] Datenquelle, Abrufmethode und Grenzen dokumentieren.

**Abnahme:** Eine technisch geeignete Quelle und der Abruf für beide Städte sind nachgewiesen. Fehlende historische Daten sind ausdrücklich dokumentiert. Die Erlaubnis zur öffentlichen Weiterverwendung ist damit noch nicht nachgewiesen.

**Stand 17.11.2026, nach Veröffentlichung:** Phase 1 parallel durchgeführt. Offizielle Suche unter `termine.blut.at` und Einzeltermin-ICS sind erreichbar. Je eine Stichprobe für Klagenfurt und Tamsweg erfolgreich mit Karte, Detailseite und Kalender verglichen; versionierter Nachweis: `python3 scripts/probe_source.py` (Exit-Code 0). Historische Suche wird serverseitig abgelehnt; Archiv ab erstem Import erforderlich. Das verlinkte Impressum schränkt die Weiterverwendung ein; vor öffentlichem Betrieb klären. Belege und technische Grenzen: [Phase-1-Recherche](docs/phase-1-datenquelle.md).

### 2. Termine abrufen und speichern

- [x] Datenformat für Termine und Aktualisierungsstatus definieren.
- [x] Python-Abrufskript mit Zeitlimits, verständlichen Fehlern und schonender Abruffrequenz erstellen.
- [x] Stadtfilter, Zeitzone und Datumsnormalisierung implementieren.
- [x] Doppelte Einträge erkennen und Änderungen vorhandenen Terminen zuordnen.
- [x] Vergangene Termine mindestens für den Rückblickzeitraum aufbewahren, auch wenn sie aus der offiziellen Suche verschwinden.
- [x] Absagen und verschwundene Einträge gemäß den tatsächlich verfügbaren Quellinformationen behandeln; Verschwinden allein nicht als bestätigte Absage werten.
- [x] Neue Daten vor dem Ersetzen des letzten gültigen Datenstands validieren.
- [x] Fehlgeschlagene Abrufe von erfolgreichen Abrufen ohne Termine unterscheiden.

**Abnahme:** Gültige JSON-Daten für beide Städte liegen vor. Wiederholte Abrufe erzeugen keine Dubletten und zerstören bei Fehlern keine gültigen Daten.

**Grenze:** Ein vollständiger Rückblick beim ersten Start ist nur möglich, wenn die Quelle historische Termine bereitstellt. Andernfalls wächst das Archiv ab dem ersten erfolgreichen Abruf.

**Stand 17.11.2026:** Phase 2 parallel implementiert. `python3 -m blutspenden --output-dir data` zweimal erfolgreich: jeweils fünf Klagenfurter und ein Tamsweger Zeitfenster, sechs eindeutige IDs, keine Dubletten oder vorgetäuschten fachlichen Änderungen. `python3 -m unittest discover -s tests -v`: 65 Tests bestanden. Datenformat, Fehlerstatus und Archivregeln: [Phase-2-Dokumentation](docs/phase-2-import.md). Website und automatische Veröffentlichung bleiben offen. Ergänzung: Prüfstatus und manuelle Prüflinks implementiert, 70 Offline-Tests bestanden.

### 3. Übersichtliche Website erstellen

- [x] Responsive Grundstruktur mit HTML, CSS und JavaScript erstellen.
- [x] Filter für „Beide Städte“, „Klagenfurt“ und „Tamsweg“ ergänzen.
- [x] Kommende und laufende Termine chronologisch darstellen und den nächsten Termin hervorheben.
- [x] Beendete Termine im Rückblickzeitraum getrennt anzeigen.
- [x] Datum, Uhrzeit, Veranstaltungsort, Adresse und offiziellen Quellenlink lesbar darstellen.
- [x] Letzte erfolgreiche Aktualisierung sowie Hinweise auf veraltete Daten, Ladefehler und leere Trefferlisten anzeigen.
- [x] Prüfstatus „unklar“ für verschwundene Termine samt Link zur offiziellen Detailseite und alternativer Stadtsuche anzeigen; explizite Absagen beibehalten.
- [x] Unabhängige Übersicht klar kennzeichnen und auf das Rote Kreuz als maßgebliche Quelle verweisen.
- [x] Tastaturbedienung, verständliche Beschriftungen und ausreichende Kontraste berücksichtigen.
- [x] Einen gut sichtbaren externen Link „Voraussetzungen für eine Blutspende“ im oberen Seitenbereich ergänzen. Auf die offizielle Seite des Österreichischen Roten Kreuzes mit den aktuellen Spendevoraussetzungen verweisen; Zielseite vor Einbau prüfen. Den Link als extern kennzeichnen und per Tastatur sowie mobil gut erreichbar gestalten. Medizinische Voraussetzungen nicht als eigene, möglicherweise veraltete Liste übernehmen.

**Abnahme:** Beide Städte und Terminbereiche sind auf Smartphone und Desktop verständlich nutzbar; alle relevanten Datenzustände werden korrekt angezeigt.

**Stand 17.11.2026:** Phase 3 parallel umgesetzt: statische Website ohne Build, Filter, laufende/kommende Termine, Monatsrückblick, sichere Prüflinks und Fehler-/Veraltungshinweise. 19 JavaScript-Tests und 11 Chromium-Browserprüfungen bestanden (keine übersprungen); mobile Breiten 320/390/768 px, Tastatur und Pages-Unterpfad geprüft. Anzeige des echten gespeicherten Bestands: 6 Termine (5 Klagenfurt, 1 Tamsweg). Weitere Details: [Phase-3-Dokumentation](docs/phase-3-website.md). Keine Veröffentlichung durchgeführt.

### 4. Aktualisierung und GitHub Pages automatisieren

- [x] GitHub Actions für täglichen sowie manuellen Datenabruf einrichten.
- [x] Persistierung des Archivs über Workflow-Läufe hinweg festlegen und umsetzen.
- [x] Validierung und Veröffentlichung über GitHub Pages einrichten (Workflow auf `main`, erste Bereitstellung erfolgreich).
- [x] Bei Abruffehlern den letzten gültigen Terminbestand erhalten und den Fehler sichtbar machen.
- [x] Erforderliche Workflow-Berechtigungen auf das notwendige Maß begrenzen.
- [x] Pfade unter dem GitHub-Pages-Projektpfad `/Blutspenden-overview/` prüfen (lokales Paket und öffentliche Seite).

**Abnahme:** Manueller Workflow und Veröffentlichung funktionieren; Aktualisierungsfehler werden nicht als „keine Termine“ ausgegeben. Die tägliche Ausführung ist konfiguriert.

**Stand 17.11.2026:** Erste Website auf [GitHub Pages](https://alexwiel.github.io/Blutspenden-overview/) veröffentlicht, Workflow-Lauf `44063278468` erfolgreich. Deployment erfolgt von `main` mit minimalen Rechten und einem Paket aus ausschließlich öffentlichen Dateien. Zum Zeitpunkt der Erstveröffentlichung fehlten täglicher Datenabruf und Archivpersistierung noch; diese sind mit der unten dokumentierten Ergänzung umgesetzt. Siehe [Deployment-Dokumentation](docs/github-pages.md).

**Ergänzung 17.11.2026:** Sichtbarer Voraussetzungen-Link zur offiziellen RK-FAQ geprüft und umgesetzt. Tageszeitplan `05:17 UTC`, manueller Abruf mit `refresh_data`, Archiv-Commit auf `main`, Fehlerstatus-Veröffentlichung und Rechteaufteilung implementiert. 108 lokale Prüfungen bestanden (77 Python, 12 Browser, 19 JavaScript); vollständiger manueller GitHub-Actions-Lauf `44111310168` erfolgreich (Abruf, Daten-Commit `ceb3178`, Build und Deployment). Auch der Push-Deployment-Lauf `44111309979` war erfolgreich. Voraussetzungen-Link und neuer Abrufzeitpunkt wurden auf der öffentlichen Seite geprüft.

### 5. Funktion und Datenqualität prüfen

- [x] Tests für Stadtfilter, Dubletten, Aktualisierungen und Archivaufbewahrung ausführen.
- [x] Datumsgrenzen einschließlich Monatsende, Sommerzeit, laufender Termine und fehlender Endzeit prüfen.
- [x] Fehlerhafte Antworten, Netzwerkausfälle und erfolgreiche Antworten ohne Termine prüfen.
- [x] Angezeigte Termine für beide Städte mit der offiziellen Quelle vergleichen.
- [x] Mobile Darstellung und Tastaturbedienung prüfen.
- [ ] Ausgelieferte Website einschließlich JSON-Datei und Quellenlinks unter dem Pages-Projektpfad prüfen (lokales unverändertes Pages-Paket bestanden; erneute öffentliche Prüfung aktuell durch Umgebungsproxy blockiert).

**Abnahme:** Relevante Tests bestehen. Einschränkungen der Quelle und gegebenenfalls nicht prüfbare Fälle sind dokumentiert.

**Stand 17.11.2026:** 89 Python-Tests einschließlich 12 Chromium-Browserprüfungen und 19 JavaScript-Tests bestanden, keine Skips. Live-Quellenprobe und isolierter Vollimport erfolgreich; alle sechs Datensätze fachlich identisch. Unverändertes Pages-Paket unter dem Projektpfad ohne JSON-Mocks geprüft: HTTP 200, Stadtfilter 6/5/1, offizielle Links, mobile Breiten ohne Überlauf, keine JavaScript-Fehler. Aktueller öffentlicher Direktabruf durch Proxy CONNECT 403 blockiert; diese erneute Live-Prüfung bleibt offen. [Prüfbericht](docs/phase-5-pruefung.md).

### 6. Dokumentieren und erste Version veröffentlichen

- [x] README um lokalen Start, Datenabruf, Tests und Deployment ergänzen.
- [x] Datenquelle, Aktualisierungsrhythmus, Archivgrenze und Fehlerverhalten dokumentieren.
- [x] Erforderliche GitHub-Pages-Einstellungen und gegebenenfalls externe Voraussetzungen beschreiben.
- [x] Erste Version veröffentlichen und die tatsächlich veröffentlichte Seite prüfen (GitHub Pages, 17.11.2026).
- [x] Verifizierte Ergebnisse und verbleibende Einschränkungen festhalten.

**Fertig, wenn:** Beide Städte korrekt dargestellt werden, die automatische Aktualisierung und Veröffentlichung funktionieren, der Datenstatus erkennbar ist und der Entwicklungsablauf dokumentiert ist.

**Abschluss 17.11.2026:** README und Betriebsdokumentation mit lokalen Befehlen, Tagesrhythmus, Pages-Einstellungen, Archiv- und Fehlerregeln geprüft und ergänzt. Erste Veröffentlichung bereits erfolgt; manueller Aktualisierungslauf `44111310168` einschließlich Archivpersistierung und Deployment in dieser Prüfung über GitHub erneut als erfolgreich bestätigt. Direkter Live-Abruf aktuell durch Umgebungsproxy blockiert; frühere Live-Verifikation bleibt separat dokumentiert. [Abschlussbericht und Grenzen](docs/phase-6-abschluss.md).

## Fortschritt, Entscheidungen und Blocker

- Ausgangslage: Das Repository enthält bisher nur README und `.gitignore`; Anwendung, Datenabruf und Workflows müssen erstellt werden.
- Phase 1: Recherche und technische Abnahme durchgeführt; beide Städte erfolgreich abgerufen. Offene Nutzungsgrundlage und Quellenlimits siehe [Rechercheprotokoll](docs/phase-1-datenquelle.md).
- `termine.blut.at` ist inzwischen erreichbar und laut aktuellem Umgebungsstatus freigegeben. Bei dieser Recherche wurde keine Umgebungskonfiguration geändert und keine Umgebung veröffentlicht.
- Phase 2: manueller Import, JSON-Validierung, Dublettenerkennung, Archiv und separater Abrufstatus implementiert und geprüft. Erster Archivaufbau ab 17.11.2026; kein vollständiger anfänglicher Rückblickmonat.
- Phase 3: Website implementiert und lokal geprüft.
- Phase 4: täglicher und manueller Datenabruf, automatische Archivpersistierung und Pages-Deployment von `main` eingerichtet; Ablauf und Nachweise siehe Deployment-Dokumentation.
- Phase 5–6: parallel bearbeitet; Gesamtprüfung und Betriebsdokumentation ergänzt. Erfolgreiches bestehendes Deployment über GitHub erneut bestätigt; direkter Pages-Abruf in der aktuellen Umgebung durch Proxy-403 blockiert. Die Nutzungsgrundlage bleibt offen. Siehe [Phase 5](docs/phase-5-pruefung.md) und [Phase 6](docs/phase-6-abschluss.md).
