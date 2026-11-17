# Projektplan: Blutspendetermine für Klagenfurt und Tamsweg

## Ziel

Eine statische Website auf GitHub Pages zeigt aktuelle und kommende Blutspendetermine des Österreichischen Roten Kreuzes für Klagenfurt am Wörthersee und Tamsweg sowie die im vergangenen Monat beendeten Termine.

## Annahmen und technische Richtung

- „Im letzten Monat“ bezeichnet einen rollierenden Kalendermonat bis heute, nicht den vorherigen Kalendermonat. Die genaue Monatsgrenze wird bei der Umsetzung festgelegt und getestet.
- Gefiltert wird anhand des Veranstaltungsorts innerhalb der beiden Städte; Termine in Nachbargemeinden gehören zunächst nicht zum Umfang.
- Für Anzeige und Datumsberechnung gilt `Europe/Vienna`, einschließlich Sommerzeit.
- Die Website verwendet HTML, CSS und JavaScript ohne Framework. Ein Python-Skript erzeugt die Termindaten als JSON.
- GitHub Actions aktualisiert die Daten täglich und auf manuellen Wunsch und veröffentlicht die Seite auf GitHub Pages.
- Die konkrete Abrufmethode wird erst nach Prüfung der offiziellen Datenquelle gewählt.

## Vorgehen

Die Phasen in dieser Reihenfolge bearbeiten. Aufgaben erst nach erfolgreicher Prüfung abhaken. Erkenntnisse, Entscheidungen und konkrete Blocker unten dokumentieren. Bei einem Blocker unabhängige Aufgaben fortsetzen; fehlende oder fehlerhafte Quelldaten niemals durch erfundene Termine ersetzen.

### 1. Offizielle Datenquelle prüfen

- [ ] Offizielle Terminsuche des Österreichischen Roten Kreuzes für beide Städte ermitteln.
- [ ] Dokumentierte Schnittstelle, Kalenderexport oder geeignete öffentliche Terminseiten untersuchen.
- [ ] Nutzungsbedingungen, Abrufregeln und angemessene Abruffrequenz prüfen.
- [ ] Verfügbarkeit von Datum, Beginn, Ende, Veranstaltungsort, Adresse, Quellenlink und stabiler Termin-ID prüfen.
- [ ] Klären, wie Änderungen, Absagen und historische Termine erkennbar sind.
- [ ] Einen kleinen, reproduzierbaren Abruf für beide Städte durchführen und Ergebnisse mit den offiziellen Einträgen vergleichen.
- [ ] Datenquelle, Abrufmethode und Grenzen dokumentieren.

**Abnahme:** Eine geeignete Quelle und der Abruf für beide Städte sind nachgewiesen. Fehlende historische Daten sind ausdrücklich dokumentiert.

**Stand 17.11.2026:** Technische Quellenrecherche und Prüfung der Abrufregeln parallel begonnen. Der Cloud-Proxy blockiert die Recherche-Domains beim HTTPS-Tunnelaufbau (`CONNECT 403 Forbidden`). Es wurden keine Quelldaten empfangen; die Aufgaben bleiben offen und die Abnahme ist nicht erreicht. Abrufnachweis, Aufgabenstatus und Fortsetzung: [Phase-1-Recherche](docs/phase-1-datenquelle.md).

### 2. Termine abrufen und speichern

- [ ] Datenformat für Termine und Aktualisierungsstatus definieren.
- [ ] Python-Abrufskript mit Zeitlimits, verständlichen Fehlern und schonender Abruffrequenz erstellen.
- [ ] Stadtfilter, Zeitzone und Datumsnormalisierung implementieren.
- [ ] Doppelte Einträge erkennen und Änderungen vorhandenen Terminen zuordnen.
- [ ] Vergangene Termine mindestens für den Rückblickzeitraum aufbewahren, auch wenn sie aus der offiziellen Suche verschwinden.
- [ ] Absagen und verschwundene Einträge gemäß den tatsächlich verfügbaren Quellinformationen behandeln; Verschwinden allein nicht als bestätigte Absage werten.
- [ ] Neue Daten vor dem Ersetzen des letzten gültigen Datenstands validieren.
- [ ] Fehlgeschlagene Abrufe von erfolgreichen Abrufen ohne Termine unterscheiden.

**Abnahme:** Gültige JSON-Daten für beide Städte liegen vor. Wiederholte Abrufe erzeugen keine Dubletten und zerstören bei Fehlern keine gültigen Daten.

**Grenze:** Ein vollständiger Rückblick beim ersten Start ist nur möglich, wenn die Quelle historische Termine bereitstellt. Andernfalls wächst das Archiv ab dem ersten erfolgreichen Abruf.

### 3. Übersichtliche Website erstellen

- [ ] Responsive Grundstruktur mit HTML, CSS und JavaScript erstellen.
- [ ] Filter für „Beide Städte“, „Klagenfurt“ und „Tamsweg“ ergänzen.
- [ ] Kommende und laufende Termine chronologisch darstellen und den nächsten Termin hervorheben.
- [ ] Beendete Termine im Rückblickzeitraum getrennt anzeigen.
- [ ] Datum, Uhrzeit, Veranstaltungsort, Adresse und offiziellen Quellenlink lesbar darstellen.
- [ ] Letzte erfolgreiche Aktualisierung sowie Hinweise auf veraltete Daten, Ladefehler und leere Trefferlisten anzeigen.
- [ ] Unabhängige Übersicht klar kennzeichnen und auf das Rote Kreuz als maßgebliche Quelle verweisen.
- [ ] Tastaturbedienung, verständliche Beschriftungen und ausreichende Kontraste berücksichtigen.

**Abnahme:** Beide Städte und Terminbereiche sind auf Smartphone und Desktop verständlich nutzbar; alle relevanten Datenzustände werden korrekt angezeigt.

### 4. Aktualisierung und GitHub Pages automatisieren

- [ ] GitHub Actions für täglichen sowie manuellen Datenabruf einrichten.
- [ ] Persistierung des Archivs über Workflow-Läufe hinweg festlegen und umsetzen.
- [ ] Validierung und Veröffentlichung über GitHub Pages einrichten.
- [ ] Bei Abruffehlern den letzten gültigen Terminbestand erhalten und den Fehler sichtbar machen.
- [ ] Erforderliche Workflow-Berechtigungen auf das notwendige Maß begrenzen.
- [ ] Pfade unter dem GitHub-Pages-Projektpfad `/Blutspenden-overview/` prüfen.

**Abnahme:** Manueller Workflow und Veröffentlichung funktionieren; Aktualisierungsfehler werden nicht als „keine Termine“ ausgegeben. Die tägliche Ausführung ist konfiguriert.

### 5. Funktion und Datenqualität prüfen

- [ ] Tests für Stadtfilter, Dubletten, Aktualisierungen und Archivaufbewahrung ausführen.
- [ ] Datumsgrenzen einschließlich Monatsende, Sommerzeit, laufender Termine und fehlender Endzeit prüfen.
- [ ] Fehlerhafte Antworten, Netzwerkausfälle und erfolgreiche Antworten ohne Termine prüfen.
- [ ] Angezeigte Termine für beide Städte mit der offiziellen Quelle vergleichen.
- [ ] Mobile Darstellung und Tastaturbedienung prüfen.
- [ ] Ausgelieferte Website einschließlich JSON-Datei und Quellenlinks unter dem Pages-Projektpfad prüfen.

**Abnahme:** Relevante Tests bestehen. Einschränkungen der Quelle und gegebenenfalls nicht prüfbare Fälle sind dokumentiert.

### 6. Dokumentieren und erste Version veröffentlichen

- [ ] README um lokalen Start, Datenabruf, Tests und Deployment ergänzen.
- [ ] Datenquelle, Aktualisierungsrhythmus, Archivgrenze und Fehlerverhalten dokumentieren.
- [ ] Erforderliche GitHub-Pages-Einstellungen und gegebenenfalls externe Voraussetzungen beschreiben.
- [ ] Erste Version veröffentlichen und die tatsächlich veröffentlichte Seite prüfen.
- [ ] Verifizierte Ergebnisse und verbleibende Einschränkungen festhalten.

**Fertig, wenn:** Beide Städte korrekt dargestellt werden, die automatische Aktualisierung und Veröffentlichung funktionieren, der Datenstatus erkennbar ist und der Entwicklungsablauf dokumentiert ist.

## Fortschritt, Entscheidungen und Blocker

- Ausgangslage: Das Repository enthält bisher nur README und `.gitignore`; Anwendung, Datenabruf und Workflows müssen erstellt werden.
- Phase 1: parallel untersucht, aber durch fehlende Netzwerkfreigabe blockiert; offizielle Datenquelle, historische Termine, Nutzungsbedingungen und Abrufmöglichkeiten noch nicht verifiziert. Siehe [Rechercheprotokoll](docs/phase-1-datenquelle.md).
- Netzwerkentwurf für die drei Recherche-Domains mit und ohne `www` gespeichert. Erst nach Übernahme in den Umgebungseinstellungen und wirksamer Freigabe können die Abrufe erneut geprüft werden.
- Anwendung und Datenabruf (Phase 2–6): noch nicht begonnen.
