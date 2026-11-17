import http.client
import io
import unittest
import urllib.error
import urllib.parse
from unittest.mock import Mock, patch

from blutspenden.source import (
    BASE, EMPTY_TEXT, SourceClient, SourceError, _calendar_link, _page, _safe_url,
)


def card(slug="example", city="Tamsweg", state="Salzburg", postal="5580"):
    return (f'<div class="card-body"><div>{state}</div>'
            f'<span class="h3 font-weight-light">{postal}</span>'
            f'<span class="h3 font-weight-medium">{city}</span>'
            f'<a class="stretched-link" data-date="2026-11-20" '
            f'href="/termine/{slug}"></a></div>')


def page(cards="", next_url=None, empty=False):
    text = f'<p>{EMPTY_TEXT}</p>' if empty else ""
    link = f'<a href="{next_url}">mehr anzeigen</a>' if next_url else ""
    return (text + f'<turbo-frame id="appointments">{cards}</turbo-frame>'
            f'<turbo-frame id="pagination">{link}</turbo-frame>')


class PageTests(unittest.TestCase):
    def test_target_and_neighbor_city_are_distinguished(self):
        html = page(card() + card("neighbor", "Mariapfarr"))
        urls, next_url = _page(html, BASE + "/termine", "Tamsweg", "Salzburg")
        self.assertEqual(urls, [BASE + "/termine/example"])
        self.assertIsNone(next_url)

    def test_klagenfurt_alias_matches(self):
        urls, _ = _page(page(card(city="Klagenfurt", state="Kärnten", postal="9020")),
                        BASE + "/termine", "Klagenfurt am Wörthersee", "Kärnten")
        self.assertEqual(len(urls), 1)

    def test_explicit_empty_state_is_valid(self):
        self.assertEqual(_page(page(empty=True), BASE + "/termine", "Tamsweg", "Salzburg"),
                         ([], None))

    def test_empty_or_invalid_html_is_not_a_successful_empty_result(self):
        invalid = ["<html><body>Maintenance</body></html>", page(),
                   '<div class="invalid-feedback">Invalid query</div>' + page(empty=True),
                   '<turbo-frame id="appointments">',
                   page('<a class="stretched-link" href="/termine/x"></a>'),
                   page(card().replace('data-date="2026-11-20"', ""))]
        for html in invalid:
            with self.subTest(html=html), self.assertRaises(SourceError):
                _page(html, BASE + "/termine", "Tamsweg", "Salzburg")

    def test_state_mismatch_is_an_error(self):
        with self.assertRaises(SourceError):
            _page(page(card(state="Kärnten")), BASE + "/termine", "Tamsweg", "Salzburg")

    def test_external_pagination_and_calendar_links_are_rejected(self):
        with self.assertRaises(SourceError):
            _page(page(card(), "https://other.example/weitere-termine?page=2"),
                  BASE + "/termine", "Tamsweg", "Salzburg")
        with self.assertRaises(SourceError):
            _calendar_link('<a href="https://other.example/ics">Export</a>', BASE + "/termine/a")

    def test_only_official_linked_calendar_is_used(self):
        self.assertEqual(_calendar_link('<a href="/termine/a/ics">Export</a>',
                                        BASE + "/termine/a"), BASE + "/termine/a/ics")

    def test_host_and_route_constraints(self):
        for url in ["http://termine.blut.at/termine", "https://user@termine.blut.at/termine",
                    BASE + "/reservierungen", BASE + "/termine/a/ics#fragment"]:
            with self.subTest(url=url), self.assertRaises(SourceError):
                _safe_url(url)


class FetchTests(unittest.TestCase):
    def test_fetch_all_preserves_filters_and_deduplicates_discovery(self):
        client = SourceClient(delay=0)
        query = urllib.parse.urlencode({"page": "2", "search_form[term]": "Klagenfurt",
                                       "search_form[radius]": "0", "search_form[state_id]": "AT-2"})
        next_url = BASE + "/weitere-termine?" + query
        responses = [page(card("a", "Klagenfurt", "Kärnten", "9020"), next_url),
                     page(card("a", "Klagenfurt", "Kärnten", "9020") +
                          card("b", "Klagenfurt am Wörthersee", "Kärnten", "9020")),
                     '<a href="/termine/a/ics">Export</a>', "calendar-a",
                     '<a href="/termine/b/ics">Export</a>', "calendar-b",
                     page(empty=True)]
        client._get = Mock(side_effect=responses)
        with patch("blutspenden.source.parse_calendar", side_effect=[[{"id": "a"}], [{"id": "b"}]]):
            self.assertEqual(client.fetch_all(), [{"id": "a"}, {"id": "b"}])
        self.assertEqual(client._get.call_count, 7)
        self.assertEqual(client._get.call_args_list[1].args, (next_url, "text/html"))

    def test_no_partial_results_when_second_city_fails(self):
        client = SourceClient(delay=0)
        client._get = Mock(side_effect=[
            page(card("a", "Klagenfurt", "Kärnten", "9020")),
            '<a href="/termine/a/ics">Export</a>', "calendar-a", SourceError("network")])
        with patch("blutspenden.source.parse_calendar", return_value=[{"id": "a"}]), self.assertRaises(SourceError):
            client.fetch_all()

    def test_pagination_lost_filters_limit_and_cycle_fail(self):
        query = urllib.parse.urlencode({"page": "2", "search_form[term]": "Klagenfurt",
                                       "search_form[radius]": "0", "search_form[state_id]": "AT-2"})
        next_url = BASE + "/weitere-termine?" + query
        for following, max_pages in [(BASE + "/weitere-termine?page=2", 100),
                                     (next_url, 1), (next_url, 100)]:
            with self.subTest(following=following, max_pages=max_pages):
                client = SourceClient(delay=0, max_pages=max_pages)
                client._get = Mock(return_value=page(card("a", "Klagenfurt", "Kärnten", "9020"), following))
                with self.assertRaises(SourceError):
                    client.fetch_all()

    def test_invalid_calendar_fails(self):
        client = SourceClient(delay=0)
        client._get = Mock(side_effect=[page(card("a", "Klagenfurt", "Kärnten", "9020")),
                                      '<a href="/termine/a/ics">Export</a>', "bad"])
        with patch("blutspenden.source.parse_calendar", side_effect=ValueError("bad ICS")), self.assertRaises(SourceError):
            client.fetch_all()

    def response(self, text="<html></html>", content_type="text/html"):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.geturl.return_value = BASE + "/termine"
        response.headers.get_content_type.return_value = content_type
        response.read.return_value = text.encode()
        return response

    @patch("blutspenden.source.time.sleep")
    def test_network_timeout_retry_is_bounded(self, sleep):
        client = SourceClient(delay=0, retries=2)
        client._opener = Mock()
        client._opener.open.side_effect = [TimeoutError(), TimeoutError(), self.response()]
        self.assertEqual(client._get(BASE + "/termine", "text/html"), "<html></html>")
        self.assertEqual(client._opener.open.call_count, 3)
        self.assertTrue(any(call.args == (2,) for call in sleep.call_args_list))

    @patch("blutspenden.source.time.sleep")
    def test_incomplete_http_body_is_retried_and_reported(self, sleep):
        client = SourceClient(delay=0, retries=1)
        response = self.response()
        response.read.side_effect = http.client.IncompleteRead(b"partial", 100)
        client._opener = Mock()
        client._opener.open.return_value = response
        with self.assertRaisesRegex(SourceError, "nicht erreichbar"):
            client._get(BASE + "/termine", "text/html")
        self.assertEqual(client._opener.open.call_count, 2)

    @patch("blutspenden.source.time.sleep")
    def test_404_is_not_retried(self, sleep):
        client = SourceClient(delay=0)
        client._opener = Mock()
        client._opener.open.side_effect = urllib.error.HTTPError(BASE + "/termine", 404, "Not Found", {}, io.BytesIO())
        with self.assertRaisesRegex(SourceError, "HTTP 404"):
            client._get(BASE + "/termine", "text/html")
        self.assertEqual(client._opener.open.call_count, 1)

    @patch("blutspenden.source.time.sleep")
    def test_retry_after_honored_or_long_wait_stops_run(self, sleep):
        client = SourceClient(delay=0)
        client._opener = Mock()
        client._opener.open.side_effect = [
            urllib.error.HTTPError(BASE + "/termine", 429, "slow", {"Retry-After": "5"}, io.BytesIO()),
            self.response()]
        client._get(BASE + "/termine", "text/html")
        self.assertTrue(any(call.args == (5,) for call in sleep.call_args_list))
        with self.assertRaises(SourceError):
            client._backoff(0, "120")

    def test_wrong_response_type_and_oversize_fail(self):
        for response in [self.response("{}", "application/json"), self.response("x" * (2 * 1024 * 1024 + 1))]:
            client = SourceClient(delay=0)
            client._opener = Mock()
            client._opener.open.return_value = response
            with self.assertRaises(SourceError):
                client._get(BASE + "/termine", "text/html")


if __name__ == "__main__":
    unittest.main()
