"""Synthetic calendar fixtures; no network access or real appointments."""

import unittest

from blutspenden.calendar import parse_calendar


SOURCE = "https://termine.blut.at/termine/synthetic-test"


def event(uid="sample-1", start="20261118T090000", end="20261118T130000",
          location=r"Testort\, Teststraße 1\, 9020 Klagenfurt", status="CONFIRMED",
          extra=""):
    lines = ["BEGIN:VEVENT", "UID:" + uid, "DTSTART:" + start]
    if end is not None:
        lines.append("DTEND:" + end)
    if location is not None:
        lines.append("LOCATION:" + location)
    if status is not None:
        lines.append("STATUS:" + status)
    if extra:
        lines.append(extra)
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def calendar(*events, timezone=""):
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "X-WR-TIMEZONE:Europe/Vienna",
        timezone, *events, "END:VCALENDAR", "",
    ])


class CalendarTests(unittest.TestCase):
    def parse(self, text, city="Klagenfurt"):
        return parse_calendar(text, SOURCE, city)

    def test_normalizes_floating_source_time_and_address(self):
        record, = self.parse(calendar(event()))
        self.assertEqual(record["id"], "rotes-kreuz:sample-1")
        self.assertEqual(record["city"], "Klagenfurt am Wörthersee")
        self.assertEqual(record["locality"], "Klagenfurt")
        self.assertEqual(record["venue"], "Testort")
        self.assertEqual(record["address"], "Teststraße 1")
        self.assertEqual(record["postal_code"], "9020")
        self.assertEqual(record["starts_at"], "2026-11-18T09:00:00+01:00")
        self.assertEqual(record["ends_at"], "2026-11-18T13:00:00+01:00")
        self.assertEqual(record["status"], "confirmed")
        self.assertEqual(record["source_event_id"], "synthetic-test")
        self.assertEqual(record["calendar_url"], SOURCE + "/ics")

    def test_normalizes_tamsweg_and_city_aliases(self):
        record, = self.parse(calendar(event(
            location=r"Testschule\, Weg 2\, 5580 Tamsweg")), "Tamsweg")
        self.assertEqual(record["city"], "Tamsweg")
        record, = self.parse(calendar(event(location=
            r"Testort\, Weg 2\, 9020 Klagenfurt am Wörthersee")))
        self.assertEqual(record["city"], "Klagenfurt am Wörthersee")

    def test_checks_locality_and_postal_code_together(self):
        for location in [r"Ort\, Weg 2\, 5580 Klagenfurt",
                         r"Ort\, Weg 2\, 9020 Villach",
                         r"Ort\, Weg 2\, 5580 Tamsweg"]:
            with self.subTest(location=location), self.assertRaises(ValueError):
                self.parse(calendar(event(location=location)))

    def test_folding_and_escaped_text_are_decoded(self):
        record, = self.parse(calendar(event(location=
            "Saal\\, Haus\\; A\\\\B\\, Teststra\r\n ße 1\\, 9020 Klagenfurt")))
        self.assertEqual(record["venue"], "Saal, Haus; A\\B")
        self.assertEqual(record["address"], "Teststraße 1")

    def test_multievent_exports_keep_separate_windows_and_ignore_timezone_fields(self):
        timezone = ("BEGIN:VTIMEZONE\r\nTZID:Europe/Vienna\r\nBEGIN:STANDARD\r\n"
                    "DTSTART:20261025T020000\r\nEND:STANDARD\r\nEND:VTIMEZONE")
        records = self.parse(calendar(
            event(uid="window-2", start="20261118T140000", end="20261118T180000"),
            event(uid="window-1"), timezone=timezone))
        self.assertEqual([r["uid"] for r in records], ["window-1", "window-2"])

    def test_missing_end_stays_unknown(self):
        record, = self.parse(calendar(event(end=None)))
        self.assertIsNone(record["ends_at"])

    def test_explicit_source_status_is_kept(self):
        for raw, expected in [("CANCELLED", "cancelled"), ("TENTATIVE", "tentative")]:
            with self.subTest(raw=raw):
                record, = self.parse(calendar(event(status=raw)))
                self.assertEqual(record["status"], expected)

    def test_absent_or_unknown_status_is_not_invented(self):
        for status in [None, "UNKNOWN"]:
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.parse(calendar(event(status=status)))

    def test_utc_is_converted_to_vienna(self):
        record, = self.parse(calendar(event(
            start="20261118T080000Z", end="20261118T120000Z")))
        self.assertEqual(record["starts_at"], "2026-11-18T09:00:00+01:00")

    def test_explicit_tzid_and_summer_offset(self):
        text = calendar(event(start="20260718T090000", end="20260718T130000"))
        text = text.replace("DTSTART:", "DTSTART;TZID=Europe/Vienna:")
        text = text.replace("DTEND:", "DTEND;TZID=Europe/Vienna:")
        record, = self.parse(text)
        self.assertEqual(record["starts_at"], "2026-07-18T09:00:00+02:00")

    def test_dst_gap_and_fold_are_not_guessed(self):
        for start in ["20260329T023000", "20261025T023000"]:
            with self.subTest(start=start), self.assertRaises(ValueError):
                self.parse(calendar(event(start=start, end=None)))

    def test_dst_transition_can_be_resolved_with_utc(self):
        record, = self.parse(calendar(event(
            start="20261025T003000Z", end="20261025T023000Z")))
        self.assertEqual(record["starts_at"], "2026-10-25T02:30:00+02:00")
        self.assertEqual(record["ends_at"], "2026-10-25T03:30:00+01:00")

    def test_backwards_wall_clock_still_preserves_real_order(self):
        records = self.parse(calendar(
            event(uid="later", start="20261025T011000Z", end="20261025T020000Z"),
            event(uid="earlier", start="20261025T003000Z", end="20261025T011000Z")))
        self.assertEqual([record["uid"] for record in records], ["earlier", "later"])
        self.assertEqual(records[0]["starts_at"], "2026-10-25T02:30:00+02:00")
        self.assertEqual(records[0]["ends_at"], "2026-10-25T02:10:00+01:00")

    def test_bad_date_timezone_and_all_day_fail(self):
        texts = [
            calendar(event(start="20260230T090000")),
            calendar(event()).replace("DTSTART:", "DTSTART;TZID=Mars/Unknown:"),
            calendar(event()).replace("DTSTART:", "DTSTART;VALUE=DATE:"),
            calendar(event(start="20261118T090000Z")).replace(
                "DTSTART:", "DTSTART;TZID=Europe/Vienna:"),
        ]
        for text in texts:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)

    def test_ends_must_follow_starts(self):
        for end in ["20261118T090000", "20261118T080000"]:
            with self.subTest(end=end), self.assertRaises(ValueError):
                self.parse(calendar(event(end=end)))

    def test_recurrences_and_duration_are_not_silently_dropped(self):
        for extra in ["RRULE:FREQ=DAILY", "RECURRENCE-ID:20261118T090000",
                      "RDATE:20261119T090000", "EXDATE:20261118T090000",
                      "DURATION:PT4H"]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.parse(calendar(event(extra=extra)))

    def test_identical_events_collapse_but_conflicting_uid_fails(self):
        self.assertEqual(len(self.parse(calendar(event(), event()))), 1)
        with self.assertRaises(ValueError):
            self.parse(calendar(event(), event(end="20261118T140000")))

    def test_required_fields_and_unique_properties(self):
        texts = [calendar(event(uid="")), calendar(event(location=None)),
                 calendar(event()).replace("UID:sample-1\r\n", ""),
                 calendar(event(extra="UID:second")),
                 calendar(event(location="Incomplete"))]
        for text in texts:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)

    def test_malformed_containers_and_content_fail(self):
        texts = ["", "<html>Not a calendar</html>", "BEGIN:VCALENDAR\nEND:VCALENDAR",
                 calendar(event()).replace("END:VEVENT", "END:VTODO"),
                 calendar(event()).replace("END:VCALENDAR", ""),
                 calendar(event()) + "UID:outside\n",
                 calendar(event(extra="MALFORMED")),
                 calendar(event()).replace("UID:", "BAD NAME:")]
        for text in texts:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)

    def test_source_url_must_be_an_official_detail_page(self):
        for url in ["http://termine.blut.at/termine/test", "https://example.org/termine/test",
                    SOURCE + "/ics", SOURCE + "?fake=1", SOURCE + "#fragment"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_calendar(calendar(event()), url, "Klagenfurt")


if __name__ == "__main__":
    unittest.main()
