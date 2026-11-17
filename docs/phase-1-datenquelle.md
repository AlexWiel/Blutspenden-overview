# Phase 1: Prüfung der Datenquelle

Stand: 17. November 2026. **Status: durch Netzwerkzugriff blockiert, nicht abgeschlossen.**

## Durchführung und Ergebnis

Die technische Quellenrecherche und die Prüfung von Abrufregeln wurden parallel durchgeführt. Die Abrufe aus der Cloud-Umgebung scheitern bereits beim Aufbau des HTTPS-Tunnels mit:

```text
<urlopen error Tunnel connection failed: 403 Forbidden>
```

Das ist eine Ablehnung durch den Cloud-Proxy, keine empfangene HTTP-Antwort des Roten Kreuzes. Es wurden keine Terminseiten, robots.txt-Dateien oder Nutzungsbedingungen empfangen. Insbesondere bedeutet der Fehler weder „keine Termine“ noch „automatischer Abruf durch den Anbieter verboten“.

Die zusätzlich geprüfte Umgebungskonfiguration bestätigt: eingeschränkter Netzwerkzugriff, aktiv durchgesetzt; die unten genannten Domains stehen nicht auf der wirksamen Freigabeliste.

## Geprüfte Recherchekandidaten

Diese URLs sind Einstiegspunkte für die weitere Recherche, **keine verifizierten Terminquellen oder Schnittstellen**:

| URL | Zweck | Beobachtung |
| --- | --- | --- |
| https://www.roteskreuz.at/blutspende | Einstieg über das Rote Kreuz | Proxy-CONNECT verweigert |
| https://www.blut.at/ | Möglicher Einstieg zur Blutspende | Proxy-CONNECT verweigert |
| https://www.blutspenden.at/ | Weiterer Recherchekandidat | Proxy-CONNECT verweigert |
| https://www.roteskreuz.at/robots.txt | Abrufregeln | Proxy-CONNECT verweigert |
| https://www.blut.at/robots.txt | Abrufregeln | Proxy-CONNECT verweigert |
| https://www.blutspenden.at/robots.txt | Abrufregeln | Proxy-CONNECT verweigert |

Auch die robots.txt-Abrufe der drei Domains ohne `www` waren auf Proxy-Ebene blockiert. Die Untersuchung weiterer Unterseiten ist bis zur Freigabe nicht sinnvoll.

## Stand der Phase-1-Aufgaben

| Aufgabe | Ergebnis / noch zu erbringen |
| --- | --- |
| Offizielle Suche für beide Städte ermitteln | Noch offen: die tatsächliche Suche muss über die offizielle Website gefunden und für Klagenfurt am Wörthersee und Tamsweg bestätigt werden. |
| API, Kalenderexport oder öffentliche Terminseiten untersuchen | Noch offen: kein Datenformat und kein Endpunkt verifiziert. Eine öffentlich verwendete interne Schnittstelle ist nicht automatisch eine dokumentierte API. |
| Nutzungsbedingungen, Abrufregeln und Frequenz prüfen | Noch offen: weder robots.txt noch verlinkte Bedingungen konnten gelesen werden. Eine Veröffentlichungserlaubnis ist nicht nachgewiesen. |
| Datenfelder und stabile Termin-ID prüfen | Noch offen: Datum, Beginn, Ende, Ort, Adresse, Quellenlink und ID müssen an echten Einträgen geprüft werden. |
| Änderungen, Absagen und Historie klären | Noch offen: weder historische Abrufbarkeit noch Absage- oder Änderungskennzeichen nachgewiesen. |
| Reproduzierbarer Abruf für beide Städte und Vergleich | Noch offen: nur der Verbindungsfehler wurde reproduziert, kein erfolgreicher Terminabruf. |
| Quelle, Methode und Grenzen dokumentieren | Dieser Zwischenstand dokumentiert die Recherche und den Blocker; die endgültige Quellenentscheidung steht aus. |

Keine Phase-1-Aufgabe wird aufgrund eines bloßen Abrufversuchs als abgeschlossen markiert. Die Abnahme ist noch nicht erreicht.

## Reproduzierbarer Verbindungscheck

Aus dem Repository-Verzeichnis, mit Python 3 und ohne zusätzliche Abhängigkeiten:

```sh
python3 - <<'PY'
import sys
import urllib.error
import urllib.request

urls = [
    'https://www.roteskreuz.at/blutspende',
    'https://www.blut.at/',
    'https://www.blutspenden.at/',
    'https://www.roteskreuz.at/robots.txt',
    'https://www.blut.at/robots.txt',
    'https://www.blutspenden.at/robots.txt',
]
failed = False
for url in urls:
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            print(url, response.status, response.url)
    except (urllib.error.URLError, TimeoutError) as error:
        failed = True
        print(url, type(error).__name__, str(error))
sys.exit(1 if failed else 0)
PY
```

Der Check liest nur öffentlich erreichbare Seiten und behält TLS-Prüfung und vorhandene Proxy-Konfiguration bei. Exit-Code 1 bedeutet mindestens einen fehlgeschlagenen Abruf; Exit-Code 0 belegt allein die Erreichbarkeit, noch keine geeignete Terminquelle. Der Abruf für beide Städte muss nach Identifikation der tatsächlichen Suche separat dokumentiert werden.

## Fortsetzung nach Netzwerkfreigabe

1. In den Umgebungseinstellungen den gespeicherten Netzwerkentwurf prüfen und speichern und anschließend die Umgebung veröffentlichen. Der Entwurf ergänzt `roteskreuz.at`, `www.roteskreuz.at`, `blut.at`, `www.blut.at`, `blutspenden.at` und `www.blutspenden.at`; die vorhandenen Paketmanager-Freigaben bleiben erhalten. Das Speichern des Entwurfs allein ändert die laufende Umgebung nicht.
2. Nach wirksamer Freigabe den Verbindungscheck wiederholen. Falls die offizielle Website auf weitere Hosts verweist, nur die tatsächlich benötigten Ziele ergänzen.
3. Offizielle Suche, verlinkte Bedingungen und robots.txt lesen; API oder Export gegenüber HTML-Auswertung bevorzugen, sofern verfügbar und geeignet.
4. Für jede Stadt einen kleinen Abruf mit exakter URL, Parametern, Abrufzeit, Ergebnisanzahl und ausgewählten nicht personenbezogenen Terminfeldern dokumentieren und mit den offiziellen Einträgen vergleichen. Ein echter Nulltreffer muss von einem Abruffehler unterschieden werden.
5. Mindestens einen historischen Zeitraum sowie Angaben zu Absagen und Änderungen untersuchen. Grenzen ausdrücklich dokumentieren; fehlende Endzeiten oder IDs nicht erfinden.
6. Erst dann Abrufmethode festlegen und die nachgewiesenen Aufgaben in `PLAN.md` abhaken.

Vorläufige technische Empfehlung: sequenziell einmal täglich abrufen, Zeitlimits und Fehler-Backoff verwenden und bedingte Requests nutzen, falls unterstützt. Das ist eine eigene Planungsempfehlung, **keine verifizierte Vorgabe oder Erlaubnis des Anbieters**. Auch eine erlaubende robots.txt ersetzt keine Prüfung der Nutzungsbedingungen für die Wiederveröffentlichung.

Ein eigenes Archiv bleibt die geplante Absicherung für vergangene Termine. Ob der erste Rückblickmonat aus der Quelle gefüllt werden kann, ist weiterhin ungeklärt. Das Verschwinden eines Termins darf ohne weiteres Signal nicht als bestätigte Absage behandelt werden.
