# Veröffentlichung auf GitHub Pages

Die Website ist unter https://alexwiel.github.io/Blutspenden-overview/ erreichbar.
Die erste Bereitstellung vom 17.11.2026 lief erfolgreich:
[GitHub-Actions-Lauf 44063278468](https://github.com/AlexWiel/Blutspenden-overview/actions/runs/44063278468),
Commit `c20c184` auf `main`.

## Ablauf

`.github/workflows/pages.yml` wird bei relevanten Änderungen auf `main` sowie
täglich per Zeitplan sowie manuell über GitHub Actions ausgelöst. Die GitHub-Pages-Einstellung ist
**Source: GitHub Actions**. Die Deployment-Umgebung `github-pages` erlaubt `main`;
diese Branch-Beschränkung wurde beibehalten. Der Feature-Branch muss für weitere
Veröffentlichungen zunächst nach `main` übernommen werden.

Der Workflow führt die Python-Import-/Archiv-/Pakettests und die Node-Tests aus.
Danach erstellt `python3 -m blutspenden.build_site --output-dir DIR` ein geprüftes
Website-Paket und veröffentlicht es mit den offiziellen GitHub-Pages-Actions.
Das Ausgabeverzeichnis muss leer und außerhalb des Repositorys sein.

Das Paket enthält ausschließlich `index.html`, die drei Dateien unter `assets/`,
die beiden JSON-Dateien unter `data/` und `.nojekyll`. Python-Quellcode, Tests,
Git-Metadaten und lokale Sperrdateien werden nicht mit ausgeliefert.

Die Actions sind auf konkrete Commit-SHAs festgelegt. Nur der Deployment-Job erhält
`pages: write` und `id-token: write`; nur der Datenabruf-Job hat `contents: write`.
Der Build hat ausschließlich `contents: read`.
Die für die Erstaktivierung benötigte Pages-Einstellung wurde vom Repository-Inhaber
in GitHub gesetzt; dafür wurde kein zusätzliches Secret hinterlegt.

## Tägliche und manuelle Aktualisierung

Der Zeitplan `17 5 * * *` startet täglich ab **05:17 UTC**: in Wien um 06:17 Uhr
im Winter und 07:17 Uhr im Sommer. GitHub kann geplante Läufe verzögert starten.
Zeitpläne laufen ausschließlich auf dem Default-Branch `main`.

Manuell: **Actions → Website auf GitHub Pages veröffentlichen → Run workflow →
main**. Die Option **refresh_data** ist standardmäßig aktiviert und ruft neue
Termine ab. Mit deaktivierter Option wird nur der gespeicherte Stand veröffentlicht.
Ein normaler Push von Website-/Datenänderungen veröffentlicht ebenfalls ohne
zusätzlichen Quellabruf. Reine Dokumentationsänderungen lösen keinen Lauf aus.

Der Datenabruf-Job checkt den neuesten `main`-Stand aus und lädt so das Archiv des
vorherigen Laufs. Nach dem vollständigen Import speichert
`scripts/persist_refresh.sh` ausschließlich `data/appointments.json` und
`data/status.json` als Commit auf `main`. Ein unveränderter Bestand erzeugt keinen
leeren Commit. Der Push ist ein normaler Fast-Forward-Push: Bei einer konkurrierenden
Änderung wird abgebrochen, niemals der andere Stand überschrieben oder ein
JSON-Konflikt blind aufgelöst. Der nächste Lauf beginnt wieder mit dem neuesten
Archiv. Branch-Schutzregeln müssen den dafür vorgesehenen Bot-Push zulassen; die
vorhandene `main`-Konfiguration wurde bei der Einrichtung verwendet.

Ein Commit mit dem eingebauten `GITHUB_TOKEN` startet keinen neuen Push-Workflow.
Deshalb nutzt der Build **im selben Lauf** den vom Datenjob ausgegebenen Commit-SHA
und veröffentlicht anschließend genau diesen Bestand. Es gibt keine zusätzlichen
persönlichen Token oder Secrets. Gemeinsame Workflow-Concurrency verhindert
parallele Import-/Deploy-Läufe; der Import ist auf 20 Minuten begrenzt, Build und
Deployment jeweils auf zehn Minuten.

Bei Quellfehlern erhält der Importer den letzten gültigen Terminbestand unverändert
und schreibt einen neuen Fehlerstatus. Auch dieser Status wird committet und mit
den alten gültigen Daten veröffentlicht. Die Seite weist darauf hin; ein letzter
separater Job markiert den Workflow anschließend als fehlgeschlagen. Ein echtes
leeres Ergebnis bleibt davon unterscheidbar. Fehler bei Checkout, Schreibrechten,
Git-Push oder Infrastruktur verhindern eine neue Bereitstellung; sie können keinen
Quellstatus veröffentlichen. Die bisherige Website bleibt dann erhalten und der
Lauf ist in Actions fehlgeschlagen. Beschädigte Archive oder fehlgeschlagene Tests
werden nicht veröffentlicht.

Der manuelle lokale Import bleibt möglich:

```sh
python3 -m blutspenden --output-dir data
```

Bei einem lokalen Daten-Commit muss dieser nach `main` übernommen werden, damit
die Veröffentlichung startet. Das Archiv wächst ab dem ersten echten Import;
fehlende historische Daten werden weiterhin nicht nachträglich erfunden.

## Verifikation

- `actionlint` hat den Workflow ohne Befund geprüft.
- 73 Python-Tests und 19 JavaScript-Tests bestanden im Deployment-Workflow.
- Das erzeugte Paket wurde lokal unter `/Blutspenden-overview/` im Browser geprüft.
- Die öffentliche Seite, CSS, beide JavaScript-Module und beide JSON-Dateien
  lieferten HTTP 200 mit passenden Content-Types.
- Der bestehende Datenstand umfasst fünf Klagenfurter und einen Tamsweger Termin.

Die offene Nutzungsgrundlage der Quelle ist im
[Quellenbericht](phase-1-datenquelle.md) dokumentiert. Die Veröffentlichung ist kein
Nachweis einer Freigabe durch das Rote Kreuz.

## Ergänzung Phase 3 und 4

Der obere Seitenbereich verlinkt die verifizierte offizielle Seite
https://www.roteskreuz.at/blut/faq
mit den Voraussetzungen für eine Blutspende (die tatsächlich verwendete Ziel-URL
steht zusätzlich im HTML). Externe Inhalte bleiben beim Roten Kreuz.

108 lokale Prüfungen bestanden: 77 Python-Import-/Archiv-/Paket-/CI-Tests,
12 Browserprüfungen und 19 JavaScript-Tests. CI-Persistenz wurde gegen lokale
Git-Remotes geprüft, einschließlich unveränderter Archive, fremder vorgemerkter
Dateien, abgelehnter konkurrierender Pushes und veröffentlichbarer Fehlerstände.
Browserfixtures liegen getrennt unter `tests/fixtures/`, damit tägliche echte
Datenänderungen die fest datierten UI-Prüfungen nicht verändern.

### Live-Nachweis der Automatisierung am 17.11.2026

- [Push-Lauf 44111309979](https://github.com/AlexWiel/Blutspenden-overview/actions/runs/44111309979): erfolgreich; veröffentlicht ohne zusätzlichen Quellabruf.
- [Manueller Aktualisierungslauf 44111310168](https://github.com/AlexWiel/Blutspenden-overview/actions/runs/44111310168): erfolgreich; Quellabruf, automatischer Daten-Commit `ceb3178`, Validierung und Deployment desselben Stands.
- Der neue Stand mit sechs Terminen und `last_successful_fetch=2026-11-17T16:11:36.886392+01:00` ist öffentlich abrufbar und stimmt mit dem persistierten Repository-Datenstand überein. Archivbeginn blieb am 17.11.2026 um 10:45 Uhr erhalten.
- Der Voraussetzungen-Link ist auf der öffentlichen Seite vorhanden. Fehlerveröffentlichung wurde mit simuliertem Quellfehler und lokalem Git-Remote getestet; die Live-Seite wurde dafür nicht absichtlich in einen Fehlerzustand versetzt.
- Der tägliche Zeitplan ist konfiguriert; seine nächste automatische Auslösung liegt nach dieser manuellen Prüfung und wurde noch nicht beobachtet.
