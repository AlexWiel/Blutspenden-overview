# Phase 1: Prüfung der Datenquelle

Stand: 17. November 2026. **Recherche durchgeführt; technischer Abruf für beide Städte nachgewiesen.** Die Nutzungsgrundlage für eine öffentliche Weiterveröffentlichung bleibt vor dem Betrieb zu klären.

## Durchführung und Netzwerk

Quellenrecherche, Abrufregeln und historische Verfügbarkeit wurden parallel untersucht. Zunächst waren nur die bisherigen Einstiegsdomains erreichbar; die tatsächliche Terminsuche war noch gesperrt. Während der Prüfung wurde auch `termine.blut.at` erreichbar. Der abschließende Umgebungsstatus bestätigt diesen Host in der aktuell durchgesetzten Freigabeliste. Bei dieser Recherche wurde keine Umgebungskonfiguration verändert und keine Umgebung veröffentlicht.

Die früheren Proxyfehler sind damit kein aktueller Blocker mehr. Die im ersten Zwischenprotokoll als ungeprüft bezeichneten Punkte wurden wie unten beschrieben untersucht.

## Offizielle Quelle und Abrufmethode

Die offizielle Seite https://www.roteskreuz.at/blut/home verlinkt https://termine.blut.at als „Jetzt Termin finden“ und bindet die Suche über `https://termine.blut.at/integrations/iframe.js` ein. Der Skriptinhalt erzeugt ein Iframe auf `/iframe/appointments?lvScope=...`. Sowohl https://www.blut.at/ als auch https://www.roteskreuz.at/blutspende leiten zur offiziellen Blutspendeseite weiter. https://www.blutspenden.at/ führt hingegen zur allgemeinen RK-Startseite.

Regionale Einstiege, jeweils erfolgreich mit HTTP 200 geprüft:

- https://www.roteskreuz.at/kaernten/blut/home verweist auf https://termine.blut.at/bl/kaernten.
- https://www.roteskreuz.at/salzburg/blut/home verweist auf https://termine.blut.at/bl/salzburg.

Die regionalen Links führen auf öffentliche HTML-Suchergebnisse unter `/termine` mit `search_form[state_id]`. Für beide Städte funktioniert ein direkter GET ohne Anmeldung oder Reservierung:

```text
https://termine.blut.at/termine?search_form[term]=Klagenfurt&search_form[radius]=0&search_form[state_id]=AT-2
https://termine.blut.at/termine?search_form[term]=Tamsweg&search_form[radius]=0&search_form[state_id]=AT-5
```

`AT-2` steht für Kärnten, `AT-5` für Salzburg. Die Parameternamen stammen aus der tatsächlich verwendeten Suche. Browser beziehungsweise `urllib.parse.urlencode` kodieren die eckigen Klammern. Nicht `location_search_form[...]` als GET-Parameter verwenden: Diese Namen gehören zum POST-Formular, und ein ungeprüfter Redirect kann zur ungefilterten Startseite führen.

**Ausgewählte technische Richtung für Phase 2:** Öffentliche HTML-Suche zur Entdeckung der Detail-URLs, anschließend die dort offiziell verlinkten Einzeltermin-Kalender unter `/termine/<slug>/ics`. Kein nachgewiesener Gesamtfeed und keine dokumentierte API. Die untersuchten Einstiegsseiten enthalten keinen Link auf eine öffentliche API-Dokumentation; das beweist deren allgemeine Nichtexistenz nicht.

Die Liste zeigt einen Link „mehr anzeigen“ auf `/weitere-termine?page=2` mit Suchparametern. Phase 2 muss Pagination prüfen und vollständig berücksichtigen; der Phase-1-Nachweis ist ausdrücklich eine kleine Stichprobe, kein vollständiger Import aller zukünftigen Termine. Die Suche liefert sowohl „Klagenfurt“ als auch „Klagenfurt am Wörthersee“ als Ortsbezeichnung. Diese Varianten müssen später normalisiert werden; PLZ, Bundesland und tatsächlicher Veranstaltungsort sind zusätzlich zu prüfen, statt eine Umkreissuche als Stadtgrenze zu behandeln.

## Verifizierte Stichproben

Abruf am 17.11.2026 gegen 10:26 Uhr Europe/Vienna. Beide Suchen, beide Detailseiten und beide Kalenderexporte lieferten HTTP 200. Kalender hatten den Content-Type `text/calendar`.

| Feld | Klagenfurt | Tamsweg |
| --- | --- | --- |
| Karten auf erster Suchseite | 5 | 1 |
| Geprüftes Datum | 18.11.2026 | 20.11.2026 |
| Beginn–Ende | 09:00–13:00 | 15:00–20:00 |
| Veranstaltungsort | PÄDAG Klagenfurt | Mittelschule |
| Adresse | Hubertusstraße 1, 9020 Klagenfurt | Lasabergweg 2, 5580 Tamsweg |
| Kalender-UID | `11841-1` | `11762-1` |
| Status | `CONFIRMED` | `CONFIRMED` |
| Detailseite | [Klagenfurt](https://termine.blut.at/termine/u8t_pprtuzhnfoaul2nvww) | [Tamsweg](https://termine.blut.at/termine/v8okx0una5rz_1579-vtjw) |
| Offiziell verlinkter Export | [ICS Klagenfurt](https://termine.blut.at/termine/u8t_pprtuzhnfoaul2nvww/ics) | [ICS Tamsweg](https://termine.blut.at/termine/v8okx0una5rz_1579-vtjw/ics) |

Datum, Uhrzeit und Ort wurden zwischen Suchkarte, offizieller Detailseite und Kalender verglichen; die Straßenadresse ist auf Detailseite und im Kalender vorhanden. Die Zahlen beschreiben den Abrufzeitpunkt und sind keine Aussage über spätere Verfügbarkeit.

## Datenfelder und Grenzen

- `DTSTART` und `DTEND` liefern Datum, Beginn und Ende. `LOCATION` enthält Veranstaltungsort, Straße, PLZ und Ort als gemeinsamen Text, nicht als separate Adressfelder. Escaping und Zeilenfaltung müssen berücksichtigt werden.
- `UID` und der Detailseiten-Slug sind vorhandene Identifikatoren. Die UID blieb bei wiederholten Abrufen derselben Beispiele gleich. Eine dokumentierte Garantie ihrer Stabilität bei Änderungen wurde nicht gefunden; UID und Quellen-URL gemeinsam aufbewahren.
- `X-WR-TIMEZONE:Europe/Vienna` und eine `VTIMEZONE`-Definition sind vorhanden. Die eigentlichen `DTSTART`/`DTEND`-Werte tragen jedoch weder `TZID` noch `Z`, sind formal also floating times. Für diese Quelle ist eine ausdrücklich getestete Normalisierung nach `Europe/Vienna` notwendig; nicht versehentlich als UTC interpretieren.
- `CREATED` und `DTSTAMP` sind vorhanden. `DTSTAMP` verändert sich bei erneuten Exportabrufen und ist kein verlässlicher Nachweis einer inhaltlichen Änderung. Die geprüften Exporte enthalten weder `LAST-MODIFIED` noch `SEQUENCE`. Änderungen später durch Vergleich normalisierter fachlicher Felder erkennen.
- `STATUS:CONFIRMED` ist nachgewiesen. Es wurde kein abgesagtes Beispiel gefunden; eine zuverlässige Lieferung von `CANCELLED` darf nicht angenommen werden. Verschwundene Einträge nicht automatisch als abgesagt markieren.
- Mehrere Zeitfenster kommen auf der Website vor; die beiden Zielstadt-Stichproben enthalten jeweils nur ein Fenster. Mehrere Ereignisse pro Termin, fehlende Endzeiten und andere Sonderfälle müssen in Phase 2 gezielt verarbeitet und getestet werden.

## Historischer Rückblick

Die Suchmaske setzt für Beginn und Ende `min=2026-11-17` am Untersuchungstag. Auch serverseitig wird ein Zeitraum vor heute abgewiesen:

```text
https://termine.blut.at/termine?search_form[state_id]=AT-5&search_form[start_on]=2026-10-17&search_form[end_on]=2026-11-16
```

Die GET-Antwort hat HTTP 200, enthält aber ungültig markierte Felder mit „frühester Termin muss um oder nach 17.11.2026 liegen“ beziehungsweise derselben Meldung für „spätester Termin“. Eine entsprechende Formularübermittlung mit gültiger Sitzung und Turbo-Accept-Header ergibt HTTP 422. Das sind Validierungsfehler, **kein erfolgreicher Abruf ohne historische Treffer**.

Damit ist der gewünschte erste Rückblickmonat über die geprüfte öffentliche Suche nicht abrufbar. Ob bereits bekannte alte Detail-URLs bestehen bleiben oder der Betreiber einen historischen Export bereitstellen kann, wurde nicht nachgewiesen. Für Phase 2 wird ein eigenes Archiv ab dem ersten erfolgreichen Import benötigt. Ein vollständiger Rückblick zu Beginn darf nicht versprochen werden.

## Abrufregeln und Nutzungsgrundlage

| Quelle | Verifiziertes Ergebnis |
| --- | --- |
| https://termine.blut.at/robots.txt | HTTP 200, nur Kommentar, keine Regeln oder Abruffrequenz angegeben |
| https://www.roteskreuz.at/robots.txt | HTTP 200, `User-Agent: *`, `Allow: /`, einzelne sachfremde gesperrte Pfade; kein `Crawl-delay` |
| https://www.blut.at/robots.txt | HTTP 200, `User-Agent: *`, `Disallow: /` |
| https://www.blutspenden.at/robots.txt | Weiterleitung auf allgemeine HTML-Startseite statt Robots-Datei |
| https://www.roteskreuz.at/impressum | HTTP 200; auch vom Footer der Terminsuche und Detailseiten verlinkt |
| https://termine.blut.at/datenschutz | HTTP 200; behandelt personenbezogene Daten für Reservierungen, keine offene Datenlizenz |

Regeln sind hostbezogen; die Recherche über `www.roteskreuz.at` ersetzt keine Prüfung der Terminsuche. Robots-Regeln sind außerdem keine Lizenz zur Wiederveröffentlichung.

Das verlinkte Impressum enthält unter „Urheberrecht und Copyrights“:

> „Alle Inhalte dienen der persönlichen Information. Eine Weiterverwendung und Reproduktion über den persönlichen Gebrauch hinaus ist nicht gestattet.“

Eine offene Datenlizenz wurde auf den untersuchten Seiten nicht gefunden. Der Kalenderexport belegt eine vorgesehene Nutzung zum Kalendereintrag, aber nicht automatisch eine Erlaubnis zur öffentlichen Wiederveröffentlichung. Die konkrete Nutzungsgrundlage für eine Übersicht sachlicher Terminfelder muss vor dem öffentlichen Betrieb geklärt werden; das ist keine abschließende rechtliche Bewertung einzelner Fakten. Texte, Bilder und Logos nicht pauschal übernehmen.

Im Impressum genannter Kontakt für Blutspende: `blut@roteskreuz.at`. **Es wurde keine Nachricht versendet.** Bei Bedarf kann der Betreiber nach Freigabe, einem unterstützten Datenfeed und historischen Terminen gefragt werden.

Vorgeschlagene Projektfrequenz: einmal täglich sequenziell abrufen, mit Timeouts, Backoff, begrenzten Wiederholungen und bedingten Requests, falls unterstützt. Dies ist eine vorsichtige Projektentscheidung, keine veröffentlichte Abrufgrenze oder Betreiberfreigabe. Requests je Lauf hängen von Pagination und Zahl der Termine ab; keine unnötigen wiederholten Detailabrufe.

## Reproduzierbarer Nachweis

Aus dem Repository-Verzeichnis mit Python 3 und ohne zusätzliche Pakete:

```sh
python3 scripts/probe_source.py
```

Das versionierte Prüfskript führt ausschließlich öffentliche Leseabrufe durch: zwei gefilterte Suchen, je eine Detailseite und den verlinkten Kalender, sowie einen historischen Validierungscheck. Es verwendet vorhandenen Proxy und TLS-Vertrauen, gibt keine Cookies oder CSRF-Tokens aus und sendet keine Reservierungen oder Erinnerungen ab.

Beim dokumentierten Lauf: fünf Karten für Klagenfurt und eine für Tamsweg auf der jeweiligen ersten Seite, beide Stichproben mit übereinstimmenden Angaben, vergangene Suche als ungültig erkannt. **Exit-Code 0.** Bei fehlender Stichprobe, Fehlerantwort oder verändertem erwarteten Verhalten schlägt das Skript fehl. Eine Stadt ohne künftigen Termin wäre für einen Produktionsimport ein gültiger Zustand, verhindert aber diesen konkreten Stichprobennachweis. Das Skript ist kein Produktionsimporter und prüft weder Vollständigkeit noch alle ICS-Sonderfälle.

## Entscheidungen für die nächsten Phasen

1. Technisch öffentliche Suche plus offiziell verlinkte ICS-Exporte verwenden; keine interne oder erfundene API voraussetzen.
2. Pagination, Stadtvarianten, Kalenderparsing, Zeitzonen und mehrere Zeitfenster in Phase 2 umsetzen und testen.
3. Archiv ab erstem Abruf aufbauen. Fehlende Historie klar kennzeichnen; für den ersten Rückblick gegebenenfalls Betreiberexport anfragen.
4. Änderungen anhand normalisierter Daten erkennen; fehlende Einträge und bestätigte Absagen unterscheiden.
5. Nutzungsgrundlage vor Veröffentlichung und regelmäßigem öffentlichem Betrieb klären.

Die Phase-1-Recherche ist durchgeführt und die technische Abnahme mit beiden Stadtstichproben erbracht. Die genannten Quellenlimits und die offene Nutzungsgrundlage bleiben verbindliche Voraussetzungen beziehungsweise Einschränkungen für die weiteren Phasen.
