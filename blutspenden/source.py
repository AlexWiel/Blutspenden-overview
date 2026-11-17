"""Read-only, all-or-nothing discovery of official donation calendars."""

import http.client
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

from .calendar import parse_calendar

BASE = "https://termine.blut.at"
EMPTY_TEXT = "Leider liegen zu Ihrer Suche aktuell keine Termine vor."
CITIES = (
    ("Klagenfurt am Wörthersee", "Klagenfurt", "AT-2", "Kärnten"),
    ("Tamsweg", "Tamsweg", "AT-5", "Salzburg"),
)
EVENT_PATH = re.compile(r"/termine/[A-Za-z0-9_-]+\Z")
CALENDAR_PATH = re.compile(r"/termine/[A-Za-z0-9_-]+/ics\Z")
MAX_BYTES = 2 * 1024 * 1024


class SourceError(RuntimeError):
    """A complete, valid source response could not be established."""


def _safe_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "termine.blut.at"
            or parsed.fragment or not (
                parsed.path in ("/termine", "/weitere-termine")
                or EVENT_PATH.fullmatch(parsed.path)
                or CALENDAR_PATH.fullmatch(parsed.path))):
        raise SourceError("Nicht unterstützte Quellen-URL")
    return url


class _Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _Node:
    def __init__(self, tag="document", attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.walk()

    def text(self):
        return " ".join(" ".join(
            child.text() if isinstance(child, _Node) else child
            for child in self.children).split())

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class _Document(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]
        self.feed(html)
        self.close()
        # Unclosed structures could otherwise masquerade as a successful empty page.
        if len(self.stack) != 1:
            raise SourceError("Unvollständige HTML-Antwort der Quelle")

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise SourceError("Unerwartete HTML-Struktur der Quelle")
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _one(nodes, description):
    nodes = list(nodes)
    if len(nodes) != 1:
        raise SourceError("Quellenstruktur geändert: " + description)
    return nodes[0]


def _canonical_city(name):
    folded = " ".join(name.casefold().split())
    if folded in ("klagenfurt", "klagenfurt am wörthersee"):
        return "Klagenfurt am Wörthersee"
    if folded == "tamsweg":
        return "Tamsweg"
    return None


def _page(html, url, city, state_name):
    doc = _Document(html).root
    if any(node.has_class("is-invalid") or node.has_class("invalid-feedback")
           for node in doc.walk()):
        raise SourceError("Die Quelle hat die Suchparameter abgewiesen")
    appointments = _one((n for n in doc.walk()
                         if n.attrs.get("id") == "appointments"), "Terminliste fehlt")
    pagination = _one((n for n in doc.walk()
                      if n.attrs.get("id") == "pagination"), "Pagination fehlt")
    cards = [n for n in appointments.walk() if n.has_class("card-body")]
    # A link without a readable card indicates changed markup, not zero results.
    all_links = [n for n in appointments.walk() if n.has_class("stretched-link")]
    if len(all_links) != len(cards):
        raise SourceError("Unlesbare Terminkarten")
    events = []
    for card in cards:
        locality = _one((n for n in card.walk() if n.tag == "span"
                         and n.has_class("h3") and n.has_class("font-weight-medium")),
                        "Ortsangabe fehlt").text()
        postal = _one((n for n in card.walk() if n.tag == "span"
                       and n.has_class("h3") and n.has_class("font-weight-light")),
                      "Postleitzahl fehlt").text()
        if not re.fullmatch(r"\d{4}", postal):
            raise SourceError("Ungültige Postleitzahl in Suchkarte")
        anchor = _one((n for n in card.walk() if n.has_class("stretched-link")),
                      "Terminlink fehlt")
        detail = _safe_url(urllib.parse.urljoin(url, anchor.attrs.get("href", "")))
        if not EVENT_PATH.fullmatch(urllib.parse.urlsplit(detail).path):
            raise SourceError("Ungültiger Terminlink")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", anchor.attrs.get("data-date", "")):
            raise SourceError("Datum fehlt in Suchkarte")
        if _canonical_city(locality) != city:
            continue
        if state_name not in card.text():
            raise SourceError("Bundesland der Terminkarte stimmt nicht überein")
        events.append(detail)
    links = [n.attrs["href"] for n in pagination.walk()
             if n.tag == "a" and "href" in n.attrs]
    if len(links) > 1:
        raise SourceError("Mehrdeutige Pagination")
    next_url = _safe_url(urllib.parse.urljoin(url, links[0])) if links else None
    if next_url and urllib.parse.urlsplit(next_url).path != "/weitere-termine":
        raise SourceError("Ungültiger Link zur nächsten Ergebnisseite")
    if not cards and (EMPTY_TEXT not in doc.text() or next_url):
        raise SourceError("Leere Terminliste ohne bestätigte Nulltreffer-Meldung")
    return events, next_url


def _calendar_link(html, source_url):
    doc = _Document(html).root
    paths = set()
    for node in doc.walk():
        if node.tag == "a" and "href" in node.attrs:
            url = urllib.parse.urljoin(source_url, node.attrs["href"])
            if url == source_url + "/ics":
                paths.add(_safe_url(url))
    if not paths:
        raise SourceError("Offizieller Kalenderlink fehlt auf der Detailseite")
    return paths.pop()


class SourceClient:
    """Sequential GET client. Results are returned only after both cities succeed."""

    def __init__(self, timeout=25, delay=1.0, retries=2, max_pages=100):
        if timeout <= 0 or delay < 0 or retries < 0 or max_pages < 1:
            raise ValueError("Ungültige Abrufkonfiguration")
        self.timeout = timeout
        self.delay = delay
        self.retries = retries
        self.max_pages = max_pages
        self._last_request = None
        self._opener = urllib.request.build_opener(_Redirects())

    def _get(self, url, expected_type):
        _safe_url(url)
        path = urllib.parse.urlsplit(url).path
        for attempt in range(self.retries + 1):
            if self._last_request is not None:
                time.sleep(max(0, self.delay - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            request = urllib.request.Request(url, headers={
                "User-Agent": "Blutspenden-overview/1.0 (public schedule importer)",
                "Accept": expected_type,
            })
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    _safe_url(response.geturl())
                    if response.headers.get_content_type() != expected_type:
                        raise SourceError("Unerwartetes Antwortformat: " + path)
                    raw = response.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise SourceError("Quellenantwort überschreitet Größenlimit: " + path)
                    return raw.decode("utf-8-sig")
            except urllib.error.HTTPError as error:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                error.close()
                if error.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise SourceError(f"Quelle antwortet mit HTTP {error.code}: {path}") from None
                pause = self._backoff(attempt, retry_after)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError,
                    http.client.HTTPException):
                if attempt == self.retries:
                    raise SourceError("Quelle nicht erreichbar: " + path) from None
                pause = self._backoff(attempt, None)
            except UnicodeDecodeError:
                raise SourceError("Ungültiges UTF-8 in Quellenantwort: " + path) from None
            time.sleep(pause)
        raise SourceError("Abruf konnte nicht abgeschlossen werden")

    @staticmethod
    def _backoff(attempt, retry_after):
        pause = 2 ** attempt
        if retry_after:
            try:
                seconds = float(retry_after)
            except ValueError:
                try:
                    deadline = parsedate_to_datetime(retry_after)
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                    seconds = (deadline - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    seconds = 0
            # Do not ignore a long Retry-After by retrying too early.
            if seconds > 60:
                raise SourceError("Quelle verlangt längere Wartezeit; Abruf später wiederholen")
            pause = max(pause, seconds)
        return min(60, max(0, pause))

    def fetch_all(self):
        records = []
        for city, term, state, state_name in CITIES:
            filters = {"search_form[term]": term, "search_form[radius]": "0",
                       "search_form[state_id]": state}
            url = BASE + "/termine?" + urllib.parse.urlencode(filters)
            visited = set()
            detail_urls = []
            while url:
                if url in visited or len(visited) >= self.max_pages:
                    raise SourceError("Pagination unvollständig: Schleife oder Seitenlimit")
                visited.add(url)
                html = self._get(url, "text/html")
                events, next_url = _page(html, url, city, state_name)
                detail_urls.extend(events)
                if next_url:
                    query = urllib.parse.parse_qs(urllib.parse.urlsplit(next_url).query)
                    if any(query.get(key) != [value] for key, value in filters.items()):
                        raise SourceError("Pagination verliert die Stadtfilter")
                    if not query.get("page", [""])[0].isdigit():
                        raise SourceError("Pagination ohne gültige Seitenzahl")
                url = next_url
            for detail in dict.fromkeys(detail_urls):
                html = self._get(detail, "text/html")
                calendar_url = _calendar_link(html, detail)
                text = self._get(calendar_url, "text/calendar")
                try:
                    parsed = parse_calendar(text, detail, city)
                except ValueError as error:
                    raise SourceError("Ungültige Termindaten: " + str(error)) from None
                if not parsed:
                    raise SourceError("Kalender enthält keinen Termin")
                records.extend(parsed)
        return records
