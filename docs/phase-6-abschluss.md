# Phase 6: Dokumentation und Veröffentlichungsstand

Stand: 17.11.2026, Europe/Vienna. Phase 5 und Phase 6 wurden parallel bearbeitet.
Der zunächst ältere lokale Stand wurde per Fast-Forward auf `origin/main`
(`6ec0ba0`) aktualisiert; vorhandene Arbeit blieb erhalten.

## Ergebnis

Die erste Version ist bereits veröffentlicht:
https://alexwiel.github.io/Blutspenden-overview/.
Eine erneute Veröffentlichung ist für die abschließenden Dokumentationsänderungen
nicht erforderlich; reine Dokumentationsänderungen starten keinen Deployment-Lauf.

Der GitHub-Connector bestätigte in dieser Abschlussprüfung den manuellen
[Workflow-Lauf 44111310168](https://github.com/AlexWiel/Blutspenden-overview/actions/runs/44111310168)
als erfolgreich: Quellabruf und Archivpersistierung (`refresh`), Tests und
Paketierung (`build`) sowie Veröffentlichung (`deploy`). Der Fehlerabschlussjob
wurde erwartungsgemäß übersprungen. Daten-Commit: `ceb3178`.
Die erste Veröffentlichung und der damalige direkte HTTP-/Browsernachweis sind in
[GitHub Pages](github-pages.md) dokumentiert.

## Reproduzierbarer Betrieb

Die [README](../README.md) enthält Voraussetzungen, lokalen Start, Import,
Python-/JavaScript-/Browsertests, öffentliche Adresse, Aktualisierungszeiten und
die notwendigen Pages-Einstellungen. [GitHub Pages](github-pages.md) erklärt
Paketierung, manuelle Ausführung mit und ohne Quellabruf, Archivpersistierung,
minimale Job-Berechtigungen und Fehlerbehandlung. Die Quellen- und Archivregeln
stehen in [Phase 1](phase-1-datenquelle.md) und [Phase 2](phase-2-import.md).
Die aktuelle Gesamtprüfung steht im [Phase-5-Bericht](phase-5-pruefung.md).

## Verbleibende Einschränkungen

- Ein erneuter direkter Abruf der öffentlichen Pages-Adresse scheiterte in dieser
  Umgebung am Proxy: `Tunnel connection failed: 403 Forbidden`. Dies ist kein
  HTTP-Fehlernachweis der Website. Die aktuelle Prüfung des erfolgreichen
  Deployments über GitHub ist vom früher dokumentierten direkten Live-Test zu
  unterscheiden. Es wurden keine Netzwerk- oder Pages-Einstellungen geändert.
- Der tägliche Lauf ab 05:17 UTC ist konfiguriert; ein zeitgesteuerter Lauf wurde
  noch nicht beobachtet. Der vollständige manuelle Aktualisierungslauf ist belegt.
- Das Archiv wächst seit 17.11.2026. Die Quelle liefert keinen vollständigen
  anfänglichen historischen Monat. Verschwundene Termine bleiben unklar;
  eine echte abgesagte Live-Stichprobe ist weiterhin nicht nachgewiesen.
- Das verlinkte Impressum beschränkt Weiterverwendung. Die Veröffentlichung
  belegt keine Freigabe durch das Rote Kreuz; die Nutzungsgrundlage bleibt offen.
  Es wurde keine Kontaktaufnahme durchgeführt.

Die technischen Aufgaben der Phase 6 sind erfüllt. Die genannten Grenzen bleiben
als Betriebs- und Quellenbeschränkungen sichtbar und werden nicht als geprüft ausgegeben.
