# Phase 3: Statische Terminübersicht

## Aufbau und Start

`index.html`, `assets/styles.css`, `assets/app.js` und `assets/model.mjs` bilden die
Website. Sie benötigt weder Framework, npm-Pakete, externe Schriftarten noch einen
Build. `model.mjs` enthält die separat testbare Datenlogik; `app.js` übernimmt das
DOM-Rendering. Text aus dem Datenbestand wird mit `textContent` eingesetzt;
Quelllinks werden vor der Darstellung validiert.

Im Repository-Hauptverzeichnis starten:

```sh
python3 -m http.server 8000 --bind 0.0.0.0
```

Die Seite über einen HTTP-Server öffnen, nicht direkt mit `file://`: JavaScript-
Module und JSON-Abrufe benötigen einen geeigneten Ursprung. CSS, Module und
`data/appointments.json` sowie `data/status.json` werden relativ zum Dokument
aufgelöst. Der GitHub-Pages-Unterpfad `/Blutspenden-overview/` wurde lokal geprüft.
Es wurde keine Website veröffentlicht und kein Workflow eingerichtet.

## Anzeige und Filter

- Native, beschriftete Radio-Buttons filtern „Beide Städte“, „Klagenfurt“ und
  „Tamsweg“. Eine Ergebniszusammenfassung wird als höfliche Live-Region aktualisiert.
- Kommende und laufende Termine erscheinen chronologisch. Der nächste gelistete,
  bestätigte Termin wird hervorgehoben; vorläufige, unklare und abgesagte Einträge
  werden nicht als nächster Termin empfohlen.
- Beendete Termine werden getrennt und mit dem jüngsten zuerst angezeigt. Die
  Monatsgrenze wird mit dem aktuellen Wiener Kalendertag berechnet, nicht aus einem
  möglicherweise alten JSON-Datenstand übernommen. Monatsenden und Sommerzeit
  sind berücksichtigt. Mit unbekanntem Ende bleibt ein Termin am gleichen lokalen
  Kalendertag noch im kommenden Bereich; das unbekannte Ende wird ausdrücklich genannt.
- Jede Karte zeigt Datum, Uhrzeit, Veranstaltungsort, Adresse und offizielle
  Prüflinks. „Unklar“ zeigt zusätzlich die letzte Sichtung und den Hinweis zur
  manuellen Prüfung. Explizite Absagen und vorläufige Termine bleiben erkennbar.
- Alle Angaben verwenden `Europe/Vienna`, auch wenn Browser oder Rechner eine
  andere Zeitzone verwenden. Zeitabhängige Labels werden minütlich neu berechnet;
  ein fokussierter Kartenlink wird dabei nicht durch DOM-Austausch entfernt.
- Der Rückblick zeigt den Zeitraum und den Archivbeginn. Der fehlende erste volle
  Rückblickmonat wird erklärt. Keine Termine werden zur Demonstration erfunden.

Die Seite kennzeichnet sich als unabhängige Übersicht und verweist auf das Rote
Kreuz als maßgebliche Quelle. Sie verwendet dessen Logo nicht und verspricht keine
bereits eingerichtete automatische Aktualisierung.

## Datenzustände

`appointments.json` wird vor der Darstellung auf Format, Zeiten, IDs, Stadtangaben,
Quellstatus und sichere offizielle Prüflinks geprüft. Unlesbare beziehungsweise
widersprüchliche Daten erzeugen einen Ladefehler, keine angebliche Nulltrefferliste.
Die Fehleransicht bietet einen erneuten Versuch und die offizielle Terminsuche.

Ein fehlender, unlesbarer oder widersprüchlicher Aktualisierungsstatus verhindert
nicht die Anzeige eines gültigen Terminbestands; stattdessen erscheint ein Hinweis.
Ein gescheiterter Quellabruf, ein zeitlich abweichender Status und Daten älter als
36 Stunden werden ebenfalls verständlich angezeigt. Rohtexte aus Fehlermeldungen
werden nicht übernommen. Ein erfolgreicher Abruf ohne Treffer wird ausdrücklich
von einem Fehler unterschieden; alte Archivdaten können dabei weiter sichtbar sein.

Beim Laden gibt es einen eigenen Status. Ohne JavaScript wird statt einer endlosen
Ladeanzeige ein Hinweis mit offiziellem Quellenlink angeboten. Die Website selbst
fragt niemals die Blutspendequelle ab, sondern nur die lokalen JSON-Dateien; für
neue Termine ist weiterhin der manuelle Import aus Phase 2 erforderlich.

## Bedienbarkeit und Gestaltung

Das Layout verwendet Systemschriften, eine ruhige burgunderfarbene Hervorhebung,
Textlabels zusätzlich zu Statusfarben, sichtbare Fokusmarkierungen und mindestens
44 Pixel hohe Filter-/Linkziele in den Karten. Ein Sprunglink führt zum Hauptinhalt.
Die Abschnitte haben klare Überschriften und die Termine sind semantische Listen.
Mobile Ansichten wechseln auf eine Spalte; lange Orte und Adressen können umbrechen.
Statusfarben sind nicht die einzige Information. Die Darstellung nutzt keine
Animationen und respektiert reduzierte Bewegung.

Dies ist keine vollständige Barrierefreiheitszertifizierung oder Prüfung mit
allen Browsern und Screenreadern. Tastaturbedienung, Kontraste der wesentlichen
Text-/Statusfarben und die unten genannten Ansichten wurden gezielt überprüft.

## Wiederholbare Prüfungen

Ohne zusätzliche JavaScript-Pakete, mit Node.js 18 oder neuer:

```sh
node --test tests/test_web_model.mjs
```

Die 19 Fälle prüfen Stadtfilter, Zeitgrenzen, laufende Termine, Monatsenden,
Sommerzeit, fehlende Endzeiten, Reihenfolge, sichere Links und Aktualisierungshinweise.

Für echte Browserprüfungen sind das optionale Python-Paket `playwright` und ein
im PATH verfügbarer Systembrowser `chromium` beziehungsweise `chromium-browser`
erforderlich:

```sh
python3 -m unittest discover -s tests -p 'test_web_browser.py' -v
```

Die Suite startet selbst einen temporären lokalen Server. Sie prüft den tatsächlichen
Projekt-Unterpfad und verwendet abgefangene JSON-Antworten für Fehler- und
Archivfälle. Synthetische Zustände bleiben ausschließlich im Test; die gespeicherten
Produktdaten werden nicht geändert. Ohne Browserabhängigkeiten werden diese Fälle
als übersprungen ausgewiesen, nicht als erfolgreich geprüft.

Gesamte Python-Suite einschließlich Import-/Archivtests und optionaler Browserfälle:

```sh
python3 -m unittest discover -s tests -v
```

## Abnahme am 17.11.2026

- 19 JavaScript-Tests bestanden, keine übersprungenen Tests.
- 11 Chromium-Browserprüfungen bestanden, keine übersprungenen Tests.
- Vorhandene 70 Python-Import-/Archivtests bleiben erfolgreich.
- Bestehender echter Datenstand: sechs kommende Zeitfenster, davon fünf in
  Klagenfurt und eines in Tamsweg. Filterwechsel zeigt entsprechend 6/5/1.
- Mobile Breiten 320, 390 und 768 Pixel ohne horizontalen Überlauf; Bedienung
  des Sprunglinks und der Radio-Buttons per Tastatur geprüft.
- Unklar-/Absagestatus mit beiden Prüflinks, getrennte vergangene Termine,
  leere Listen, Quellfehler, fehlender Status, veraltete Daten, kaputtes JSON
  und Wiederholung nach Netzwerkfehler im Browser geprüft.
- Tatsächliche Auslieferung mit realen JSON-Dateien am Projektpfad sowie die
  Desktopansicht mit 1365 Pixeln und mobile Ansicht mit 390 Pixeln geprüft.

Offen bleiben automatische Aktualisierung und Deployment (Phase 4) sowie die
Nutzungsgrundlage vor öffentlicher Weiterveröffentlichung aus dem Quellenbericht.

## Ergänzung: Spendevoraussetzungen

Der obere Seitenbereich enthält jetzt einen gut sichtbaren externen Link
„Voraussetzungen für eine Blutspende“ auf https://www.roteskreuz.at/blut/faq.
Diese offizielle Seite wurde mit HTTP 200 und den tatsächlichen Informationen zu
„Wer darf Blut spenden?“ geprüft. Es werden keine medizinischen Kriterien als
lokale Liste kopiert. Die ergänzte Browserprüfung deckt Linkziel, Tastaturfokus,
44-Pixel-Zielgröße und mobile Ansichten ab; insgesamt bestehen jetzt zwölf
Browserprüfungen.
