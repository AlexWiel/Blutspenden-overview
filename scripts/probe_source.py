"""Read-only Phase-1 probe; not a production importer or a complete schedule.

Run manually: python3 scripts/probe_source.py
Uses public search pages and their linked per-event calendars. No reservations.
"""

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from zoneinfo import ZoneInfo


BASE = "https://termine.blut.at"


def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Blutspenden-overview/phase-1-source-probe",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8"), response.headers.get_content_type()


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(html):
    parser = Text()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def search_url(**fields):
    return BASE + "/termine?" + urllib.parse.urlencode({
        f"search_form[{name}]": value for name, value in fields.items()
    })


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def city_sample(city, state):
    url = search_url(term=city, radius=0, state_id=state)
    html, _ = fetch(url)
    require('class="invalid-feedback"' not in html, "Invalid city search")
    # Deliberately specific to the inspected public HTML. Fail on markup changes.
    cards = []
    pattern = r'<div class="card-body">(.*?)<a class="stretched-link"([^>]+)>'
    for body, attributes in re.findall(pattern, html, re.S):
        link = re.search(r'href="([^"]+)"', attributes)
        date = re.search(r'data-date="([^"]+)"', attributes)
        if link and date:
            cards.append((body, link[1], date[1]))
    require(cards, f"No sample found for {city}; inspect source manually")
    body, path, date = cards[0]
    require(city in plain(body), "Search did not return the requested city")
    detail_url = urllib.parse.urljoin(BASE, unescape(path))
    detail, _ = fetch(detail_url)
    require(f"{path}/ics" in detail, "Official calendar link missing")
    calendar, content_type = fetch(detail_url + "/ics")
    require(content_type == "text/calendar", "Unexpected calendar content type")
    # Unfold iCalendar lines. Full parsing of multiple VEVENTs is Phase 2 work.
    calendar = calendar.replace("\r\n", "\n")
    calendar = re.sub(r"\n[ \t]", "", calendar)
    values = {}
    for line in calendar.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key] = value
    for key in ["UID", "DTSTART", "DTEND", "LOCATION", "STATUS"]:
        require(key in values, f"Missing calendar field: {key}")
    require(values["DTSTART"][:8] == date.replace("-", ""), "Date mismatch")
    detail_text = plain(detail)
    event_date = datetime.strptime(values["DTSTART"][:8], "%Y%m%d")
    months = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli",
              "August", "September", "Oktober", "November", "Dezember"]
    displayed_date = (f"{event_date.day}. {months[event_date.month - 1]} "
                      f"{event_date.year}")
    require(displayed_date in detail_text, "Detail date mismatch")
    for key in ["DTSTART", "DTEND"]:
        value = values[key]
        clock = value[9:11] + ":" + value[11:13]
        require(clock in plain(body) and clock in detail_text, "Time mismatch")
    require(city in values["LOCATION"] and city in detail_text, "City mismatch")
    return {
        "city": city,
        "search_url": url,
        "cards_on_first_page": len(cards),
        "sample_card_text": plain(body),
        "source_url": detail_url,
        "calendar_url": detail_url + "/ics",
        "calendar": {key: values[key] for key in [
            "UID", "DTSTART", "DTEND", "LOCATION", "STATUS",
            "X-WR-TIMEZONE", "CREATED", "DTSTAMP",
        ] if key in values},
        "comparison": "city, date and times agree across card, detail and calendar",
    }


def main():
    now = datetime.now(ZoneInfo("Europe/Vienna"))
    report = {"retrieved_at": now.isoformat(), "samples": [
        city_sample("Klagenfurt", "AT-2"),
        city_sample("Tamsweg", "AT-5"),
    ]}
    # A small, explicitly invalid past query tests the source's validation.
    today = now.date()
    url = search_url(state_id="AT-5", start_on=str(today - timedelta(days=31)),
                     end_on=str(today - timedelta(days=1)))
    html, _ = fetch(url)
    text = plain(html)
    rejected = "muss um oder nach" in text and "is-invalid" in html
    require(rejected, "Historical-query behavior changed; inspect source manually")
    report["history"] = {"url": url, "past_range_rejected": rejected}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
