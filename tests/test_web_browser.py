"""Optional headless UI checks; no requests to the public donation service.

Run: python3 -m unittest discover -s tests -p 'test_web_browser.py' -v
Requires Python Playwright and a local Chromium executable. Missing optional
dependencies are reported as skipped tests, never as successful browser checks.
"""

import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import threading
import unittest
from urllib.parse import urlsplit

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    expect = sync_playwright = None


ROOT = Path(__file__).resolve().parents[1]
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser")
FIXED_TIME = "2026-11-17T10:00:00Z"  # 11:00 in Europe/Vienna.


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@unittest.skipUnless(sync_playwright and CHROMIUM,
                     "Optional: Python Playwright und Chromium erforderlich")
class WebsiteBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(QuietHandler, directory=str(ROOT.parent))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=CHROMIUM, headless=True, args=["--no-sandbox"])
        cls.url = "http://127.0.0.1:{}/{}/".format(
            cls.server.server_port, ROOT.name)
        cls.original = json.loads((ROOT / "tests/fixtures/web-appointments.json").read_text(encoding="utf-8"))
        cls.original_status = json.loads((ROOT / "tests/fixtures/web-status.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 900}, locale="de-AT",
            timezone_id="America/Los_Angeles")
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.add_init_script("""
            const RealDate = Date;
            const fixed = RealDate.parse(%s);
            window.Date = class extends RealDate {
                constructor(...args) { super(...(args.length ? args : [fixed])); }
                static now() { return fixed; }
            };
        """ % json.dumps(FIXED_TIME))

    def fixtures(self):
        return copy.deepcopy(self.original), copy.deepcopy(self.original_status)

    def route_data(self, data, status, *, malformed=False, status_missing=False,
                   initial_network_failure=False):
        requests = {"appointments": 0}

        def appointments(route):
            requests["appointments"] += 1
            if initial_network_failure and requests["appointments"] == 1:
                route.abort("failed")
            else:
                route.fulfill(status=200, content_type="application/json",
                              body="{invalid" if malformed else json.dumps(data))

        def update_status(route):
            if status_missing:
                route.fulfill(status=404, body="Not found")
            else:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(status))

        self.page.route("**/data/appointments.json*", appointments)
        self.page.route("**/data/status.json*", update_status)
        return requests

    def open(self, data=None, status=None, **options):
        if data is None:
            data, default_status = self.fixtures()
            status = status if status is not None else default_status
        self.route_data(data, status, **options)
        self.page.goto(self.url, wait_until="networkidle")

    def assert_ready(self):
        expect(self.page.locator("#content")).to_be_visible()
        expect(self.page.locator("#loading-state")).to_be_hidden()
        expect(self.page.locator("#error-state")).to_be_hidden()
        self.assertEqual(self.errors, [])

    def test_project_subpath_renders_real_snapshot_and_city_filters(self):
        self.open()
        self.assert_ready()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(6)
        expect(self.page.locator("#next-appointment")).to_contain_text("PÄDAG Klagenfurt")
        expect(self.page.locator("#next-appointment")).to_contain_text("09:00")
        expect(self.page.locator("#update-summary time")).to_have_attribute(
            "datetime", self.original["last_successful_fetch"])
        expect(self.page.locator("#update-summary")).to_contain_text("November 2026")
        self.page.locator('input[name="city"][value="tamsweg"]').check()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(1)
        expect(self.page.locator("#upcoming-list")).to_contain_text("Mittelschule")
        self.page.locator('input[name="city"][value="klagenfurt"]').check()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(5)
        urls = self.page.evaluate("performance.getEntriesByType('resource').map(e => e.name)")
        app_resources = [urlsplit(url).path for url in urls if "/assets/" in url]
        self.assertTrue(app_resources)
        self.assertTrue(all(path.startswith("/" + ROOT.name + "/assets/")
                            for path in app_resources))

    def test_keyboard_skip_link_and_native_radio_navigation(self):
        self.open()
        self.assert_ready()
        self.page.keyboard.press("Tab")
        skip = self.page.locator("a[href='#main-content']")
        expect(skip).to_be_focused()
        self.page.keyboard.press("Enter")
        expect(self.page.locator("#main-content")).to_be_focused()
        all_cities = self.page.locator('input[name="city"][value="all"]')
        all_cities.focus()
        self.page.keyboard.press("ArrowRight")
        expect(self.page.locator('input[name="city"][value="klagenfurt"]')).to_be_checked()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(5)
        self.assertEqual(self.page.locator("#results-summary").get_attribute("aria-live"), "polite")

    def test_requirements_link_is_visible_external_keyboard_and_mobile_accessible(self):
        self.open()
        self.assert_ready()
        link = self.page.locator("#donation-requirements")
        expect(link).to_have_attribute("href", "https://www.roteskreuz.at/blut/faq")
        expect(link).to_contain_text("Voraussetzungen für eine Blutspende")
        expect(link).to_contain_text("externer Link")
        expect(self.page.locator(".hero #donation-requirements")).to_be_visible()
        link.focus()
        expect(link).to_be_focused()
        self.assertEqual(link.evaluate("node => getComputedStyle(node).outlineStyle"), "solid")
        for width in (320, 390, 768):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 844})
                expect(link).to_be_visible()
                self.assertGreaterEqual(link.bounding_box()["height"], 44)
                self.assertTrue(self.page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"))

    def test_mobile_sizes_have_no_horizontal_overflow_and_filters_work(self):
        self.open()
        for width in (320, 390, 768):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 844})
                self.assertTrue(self.page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"))
                self.page.locator('input[name="city"][value="tamsweg"]').check()
                expect(self.page.locator("#upcoming-list > li")).to_have_count(1)
                self.page.locator('input[name="city"][value="all"]').check()

    def test_unclear_and_cancelled_have_check_links_and_are_not_featured(self):
        data, status = self.fixtures()
        unclear, cancelled = data["appointments"][0], data["appointments"][1]
        unclear.update(availability="not_listed", verification_status="unklar")
        cancelled.update(status="cancelled", verification_status="abgesagt")
        self.open(data, status)
        self.assert_ready()
        cards = self.page.locator("#upcoming-list > li")
        unknown_card = cards.filter(has_text=unclear["venue"])
        expect(unknown_card).to_contain_text("Unklar", ignore_case=True)
        expect(unknown_card.locator("a[href=%s]" % json.dumps(unclear["verification_url"]))).to_have_count(1)
        expect(unknown_card.locator("a[href=%s]" % json.dumps(unclear["verification_search_url"]))).to_have_count(1)
        expect(cards.filter(has_text=cancelled["venue"])).to_contain_text("abgesagt", ignore_case=True)
        expect(self.page.locator("#next-appointment")).not_to_contain_text(unclear["venue"])
        expect(self.page.locator("#next-appointment")).not_to_contain_text(cancelled["venue"])

    def test_past_is_separate_and_archive_coverage_is_explained(self):
        data, status = self.fixtures()
        record = data["appointments"][0]
        record.update(starts_at="2026-11-10T09:00:00+01:00",
                      ends_at="2026-11-10T13:00:00+01:00",
                      availability="not_listed", verification_status="unklar")
        self.open(data, status)
        self.assert_ready()
        expect(self.page.locator("#past-list > li")).to_have_count(1)
        expect(self.page.locator("#past-list")).to_contain_text(record["venue"])
        expect(self.page.locator("#upcoming-list > li")).to_have_count(5)
        expect(self.page.locator("#history-note")).not_to_be_empty()

    def test_valid_empty_results_do_not_look_like_load_errors(self):
        data, status = self.fixtures()
        data["appointments"] = []
        status.update(state="empty", fetched_counts={"Klagenfurt am Wörthersee": 0, "Tamsweg": 0})
        self.open(data, status)
        self.assert_ready()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(0)
        expect(self.page.locator("#upcoming-empty")).to_be_visible()
        expect(self.page.locator("#past-empty")).to_be_visible()

    def test_source_error_keeps_cached_appointments_with_warning(self):
        data, status = self.fixtures()
        status.update(state="error", fetched_counts=None, error="SECRET_MUST_NOT_RENDER")
        self.open(data, status)
        self.assert_ready()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(6)
        expect(self.page.locator("#notices")).not_to_be_empty()
        expect(self.page.locator("body")).not_to_contain_text("SECRET_MUST_NOT_RENDER")

    def test_missing_status_keeps_data_and_warns(self):
        self.open(status_missing=True)
        self.assert_ready()
        expect(self.page.locator("#upcoming-list > li")).to_have_count(6)
        expect(self.page.locator("#notices")).not_to_be_empty()

    def test_stale_dataset_has_warning(self):
        data, status = self.fixtures()
        stamp = "2026-11-15T08:00:00+01:00"
        data.update(last_successful_fetch=stamp, archive_started_at=stamp,
                    history_start="2026-10-15T00:00:00+02:00")
        for record in data["appointments"]:
            record.update(first_seen_at=stamp, last_seen_at=stamp, last_changed_at=stamp)
        status.update(last_attempt=stamp, last_successful_fetch=stamp)
        self.open(data, status)
        self.assert_ready()
        expect(self.page.locator("#notices")).to_contain_text("36 Stunden")

    def test_network_failure_offers_retry_and_successfully_recovers(self):
        data, status = self.fixtures()
        requests = self.route_data(data, status, initial_network_failure=True)
        self.page.goto(self.url, wait_until="networkidle")
        expect(self.page.locator("#error-state")).to_be_visible()
        expect(self.page.locator("#content")).to_be_hidden()
        self.page.locator("#retry-button").click()
        self.assert_ready()
        self.assertGreaterEqual(requests["appointments"], 2)

    def test_malformed_json_shows_error_instead_of_zero_appointments(self):
        self.open(malformed=True)
        expect(self.page.locator("#error-state")).to_be_visible()
        expect(self.page.locator("#content")).to_be_hidden()
        expect(self.page.locator("#loading-state")).to_be_hidden()


if __name__ == "__main__":
    unittest.main()
