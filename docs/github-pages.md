# Veröffentlichung auf GitHub Pages

Die Website ist unter https://alexwiel.github.io/Blutspenden-overview/ erreichbar.
Die erste Bereitstellung vom 17.11.2026 lief erfolgreich:
[GitHub-Actions-Lauf 44063278468](https://github.com/AlexWiel/Blutspenden-overview/actions/runs/44063278468),
Commit `c20c184` auf `main`.

## Ablauf

`.github/workflows/pages.yml` wird bei relevanten Änderungen auf `main` sowie
manuell über GitHub Actions ausgelöst. Die GitHub-Pages-Einstellung ist
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
`pages: write` und `id-token: write`; der Build hat ausschließlich `contents: read`.
Die für die Erstaktivierung benötigte Pages-Einstellung wurde vom Repository-Inhaber
in GitHub gesetzt; dafür wurde kein zusätzliches Secret hinterlegt.

## Daten aktualisieren

**Der Workflow aktualisiert noch keine Termine beim Roten Kreuz.** Er veröffentlicht
den im Repository gespeicherten Datenstand. Ein täglicher Datenabruf und die
automatische Archivpersistierung sind weiterhin die offenen Teile von Phase 4.

Bis dahin: Import lokal ausführen, die JSON-Änderungen prüfen und nach `main`
übernehmen. Der Push der Daten löst die erneute Veröffentlichung aus:

```sh
python3 -m blutspenden --output-dir data
```

Ein manueller Deployment-Lauf über **Actions → Website auf GitHub Pages
veröffentlichen → Run workflow → main** veröffentlicht ebenfalls nur den schon
gespeicherten Stand. README- und reine Dokumentationsänderungen allein lösen keine
Bereitstellung aus. Ein fehlgeschlagener Test- oder Deployment-Lauf ersetzt keine
bereits erfolgreiche Website-Bereitstellung.

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
