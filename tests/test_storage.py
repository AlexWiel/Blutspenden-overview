"""Offline archive/transaction tests with explicitly synthetic events."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from blutspenden.storage import (
    atomic_write_json, history_cutoff, load_dataset, update_dataset, validate_dataset,
)


VIENNA = ZoneInfo("Europe/Vienna")
NOW = datetime(2026, 11, 17, 10, tzinfo=VIENNA)


def appointment(uid="test-a", source_id=None, start="2026-11-18T09:00:00+01:00",
                end="2026-11-18T13:00:00+01:00", **changes):
    source_id = source_id or uid
    source_url = "https://termine.blut.at/termine/" + source_id
    record = {
        "id": "rotes-kreuz:" + uid,
        "uid": uid,
        "source_url": source_url,
        "calendar_url": source_url + "/ics",
        "source_event_id": source_id,
        "city": "Klagenfurt am Wörthersee",
        "venue": "Synthetischer Testort",
        "address": "Teststraße 1",
        "postal_code": "9020",
        "locality": "Klagenfurt",
        "starts_at": start,
        "ends_at": end,
        "status": "confirmed",
    }
    record.update(changes)
    return record


class ArchiveTests(unittest.TestCase):
    def test_initial_data_contains_schema_and_tracking(self):
        dataset = update_dataset(None, [appointment()], NOW)
        self.assertEqual(dataset["schema_version"], 1)
        self.assertEqual(dataset["history_start"], "2026-10-17T00:00:00+02:00")
        self.assertEqual(dataset["archive_started_at"], NOW.isoformat())
        record = dataset["appointments"][0]
        for key in ("first_seen_at", "last_seen_at", "last_changed_at"):
            self.assertEqual(record[key], NOW.isoformat())
        self.assertEqual(record["availability"], "listed")
        validate_dataset(dataset)

    def test_exact_duplicates_are_deduplicated_without_mutating_input(self):
        record = appointment()
        incoming = [record, copy.deepcopy(record)]
        untouched = copy.deepcopy(incoming)
        data = update_dataset(None, incoming, NOW)
        self.assertEqual(len(data["appointments"]), 1)
        self.assertEqual(incoming, untouched)

    def test_conflicting_uid_or_slot_fails_whole_batch(self):
        conflicts = [appointment(venue="Anderer Ort"),
                     appointment("test-b", source_id="test-a")]
        for conflict in conflicts:
            with self.subTest(conflict=conflict), self.assertRaises(ValueError):
                update_dataset(None, [appointment(), conflict], NOW)

    def test_repeated_fetch_updates_seen_not_changed(self):
        old = update_dataset(None, [appointment()], NOW)
        original = copy.deepcopy(old)
        later = NOW + timedelta(days=1)
        incoming = appointment(DTSTAMP="ignored-transport-value")
        new = update_dataset(old, [incoming], later)
        record = new["appointments"][0]
        self.assertEqual(old, original)
        self.assertEqual(record["first_seen_at"], NOW.isoformat())
        self.assertEqual(record["last_changed_at"], NOW.isoformat())
        self.assertEqual(record["last_seen_at"], later.isoformat())
        self.assertNotIn("DTSTAMP", record)

    def test_content_update_and_explicit_cancellation_replace_same_id(self):
        old = update_dataset(None, [appointment()], NOW)
        later = NOW + timedelta(days=1)
        data = update_dataset(old, [appointment(status="cancelled", venue="Neuer Ort")], later)
        self.assertEqual(len(data["appointments"]), 1)
        record = data["appointments"][0]
        self.assertEqual(record["status"], "cancelled")
        self.assertEqual(record["venue"], "Neuer Ort")
        self.assertEqual(record["last_changed_at"], later.isoformat())

    def test_missing_future_event_not_inferred_cancelled(self):
        old = update_dataset(None, [appointment()], NOW)
        new = update_dataset(old, [], NOW + timedelta(hours=1))
        record = new["appointments"][0]
        self.assertEqual(record["availability"], "not_listed")
        self.assertEqual(record["status"], "confirmed")
        self.assertEqual(record["verification_status"], "unklar")
        self.assertEqual(record["verification_url"], record["source_url"])
        self.assertEqual(record["last_seen_at"], NOW.isoformat())
        self.assertEqual(record["last_changed_at"], NOW.isoformat())

    def test_missing_cancelled_event_stays_cancelled(self):
        old = update_dataset(None, [appointment(status="cancelled")], NOW)
        new = update_dataset(old, [], NOW + timedelta(days=1))
        self.assertEqual(new["appointments"][0]["status"], "cancelled")
        self.assertEqual(new["appointments"][0]["verification_status"], "abgesagt")

    def test_reappearing_event_clears_uncertainty_without_source_change(self):
        old = update_dataset(None, [appointment()], NOW)
        missing = update_dataset(old, [], NOW + timedelta(hours=1))
        new = update_dataset(missing, [appointment()], NOW + timedelta(hours=2))
        record = new["appointments"][0]
        self.assertEqual(record["verification_status"], "gelistet")
        self.assertEqual(record["last_changed_at"], NOW.isoformat())

    def test_verification_links_use_original_detail_and_matching_city_search(self):
        cases = [appointment(), appointment(city="Tamsweg", locality="Tamsweg", postal_code="5580")]
        for event, term, state in zip(cases, ["Klagenfurt", "Tamsweg"], ["AT-2", "AT-5"]):
            with self.subTest(city=term):
                data = update_dataset(None, [event], NOW)
                record = update_dataset(data, [], NOW)["appointments"][0]
                self.assertEqual(record["verification_url"], event["source_url"])
                url = urlsplit(record["verification_search_url"])
                self.assertEqual((url.scheme, url.netloc, url.path),
                                 ("https", "termine.blut.at", "/termine"))
                self.assertEqual(parse_qs(url.query), {
                    "search_form[term]": [term], "search_form[radius]": ["0"],
                    "search_form[state_id]": [state],
                })

    def test_misleading_verification_fields_are_rejected(self):
        data = update_dataset(update_dataset(None, [appointment()], NOW), [], NOW)
        for key, wrong in [("verification_status", "gelistet"),
                           ("verification_url", "https://example.org/"),
                           ("verification_search_url", "https://termine.blut.at/")]:
            with self.subTest(field=key):
                broken = copy.deepcopy(data)
                broken["appointments"][0][key] = wrong
                with self.assertRaises(ValueError):
                    validate_dataset(broken)

    def test_uid_change_reconciles_unique_source_slot(self):
        old = update_dataset(None, [appointment()], NOW)
        later = NOW + timedelta(days=1)
        new = update_dataset(old, [appointment("new-uid", source_id="test-a")], later)
        self.assertEqual(len(new["appointments"]), 1)
        record = new["appointments"][0]
        self.assertEqual(record["id"], "rotes-kreuz:new-uid")
        self.assertEqual(record["first_seen_at"], NOW.isoformat())
        self.assertEqual(record["last_changed_at"], later.isoformat())

    def test_distinct_windows_from_same_source_remain_separate(self):
        first = appointment("window-1", source_id="shared-source")
        second = appointment("window-2", source_id="shared-source",
                             start="2026-11-18T15:00:00+01:00",
                             end="2026-11-18T19:00:00+01:00")
        data = update_dataset(None, [second, first], NOW)
        self.assertEqual([item["uid"] for item in data["appointments"]],
                         ["window-1", "window-2"])

    def test_finished_events_retained_until_month_boundary(self):
        old = update_dataset(None, [appointment()], NOW)
        retained = update_dataset(old, [], datetime(2026, 12, 18, 10, tzinfo=VIENNA))
        self.assertEqual(len(retained["appointments"]), 1)
        pruned = update_dataset(retained, [], datetime(2026, 12, 19, 10, tzinfo=VIENNA))
        self.assertEqual(pruned["appointments"], [])

    def test_end_exactly_on_cutoff_is_retained(self):
        event = appointment(start="2026-10-16T23:00:00+02:00",
                            end="2026-10-17T00:00:00+02:00")
        data = update_dataset(None, [event], NOW)
        self.assertEqual(len(data["appointments"]), 1)

    def test_missing_end_retained_conservatively_through_local_day(self):
        event = appointment(start="2026-10-16T10:00:00+02:00", end=None)
        self.assertEqual(len(update_dataset(None, [event], NOW)["appointments"]), 1)
        later = NOW + timedelta(days=1)
        self.assertEqual(update_dataset(None, [event], later)["appointments"], [])

    def test_cutoff_clamps_month_ends_and_crosses_year(self):
        cases = [(datetime(2024, 3, 31, tzinfo=VIENNA), "2024-02-29T00:00:00+01:00"),
                 (datetime(2025, 3, 31, tzinfo=VIENNA), "2025-02-28T00:00:00+01:00"),
                 (datetime(2026, 1, 31, tzinfo=VIENNA), "2025-12-31T00:00:00+01:00"),
                 (datetime(2026, 4, 29, tzinfo=VIENNA), "2026-03-29T00:00:00+01:00")]
        for now, expected in cases:
            with self.subTest(now=now):
                self.assertEqual(history_cutoff(now).isoformat(), expected)

    def test_invalid_record_batch_does_not_mutate_existing(self):
        old = update_dataset(None, [appointment()], NOW)
        original = copy.deepcopy(old)
        invalid = appointment(ends_at="2026-11-18T08:00:00+01:00")
        with self.assertRaises(ValueError):
            update_dataset(old, [invalid], NOW)
        self.assertEqual(old, original)

    def test_record_validation_rejects_bad_identity_city_url_and_time(self):
        cases = [dict(id="wrong"), dict(city="Graz"), dict(locality="Maria Saal"),
                 dict(postal_code="9999"), dict(source_event_id="wrong"),
                 dict(source_url="http://termine.blut.at/termine/test-a"),
                 dict(calendar_url="https://other.example/a.ics"),
                 dict(starts_at="2026-11-18T09:00:00"),
                 dict(starts_at="2026-11-18T09:00:00+02:00"),
                 dict(venue=""), dict(status="disappeared")]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                update_dataset(None, [appointment(**changes)], NOW)

    def test_naive_or_backward_clock_rejected(self):
        with self.assertRaises(ValueError):
            update_dataset(None, [], datetime(2026, 11, 17))
        old = update_dataset(None, [appointment()], NOW)
        with self.assertRaises(ValueError):
            update_dataset(old, [], NOW - timedelta(seconds=1))

    def test_duplicate_and_corrupt_archive_metadata_rejected(self):
        valid = update_dataset(None, [appointment()], NOW)
        duplicate = copy.deepcopy(valid)
        duplicate["appointments"].append(copy.deepcopy(duplicate["appointments"][0]))
        invalids = [duplicate]
        for key, value in [("schema_version", True), ("source", "https://other.example"),
                           ("history_start", "2026-10-18T00:00:00+02:00")]:
            broken = copy.deepcopy(valid)
            broken[key] = value
            invalids.append(broken)
        for broken in invalids:
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                validate_dataset(broken)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "appointments.json"

    def test_missing_is_none_but_corrupt_file_is_not_reset(self):
        self.assertIsNone(load_dataset(self.path))
        self.path.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_dataset(self.path)
        self.assertEqual(self.path.read_text(), "{not-json")

    def test_duplicate_json_keys_are_rejected(self):
        self.path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Doppelter JSON"):
            load_dataset(self.path)

    def test_initial_v1_archive_is_enriched_without_changing_history(self):
        data = update_dataset(update_dataset(None, [appointment()], NOW), [], NOW)
        old = copy.deepcopy(data)
        for record in old["appointments"]:
            for key in ("verification_status", "verification_url", "verification_search_url"):
                del record[key]
        self.path.write_text(json.dumps(old), encoding="utf-8")
        before = self.path.read_bytes()
        self.assertEqual(load_dataset(self.path), data)
        self.assertEqual(self.path.read_bytes(), before)

    def test_partial_verification_metadata_is_not_silently_repaired(self):
        data = update_dataset(None, [appointment()], NOW)
        del data["appointments"][0]["verification_url"]
        self.path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_dataset(self.path)

    def test_round_trip_and_invalid_data_does_not_replace_valid_bytes(self):
        valid = update_dataset(None, [appointment()], NOW)
        atomic_write_json(self.path, valid)
        self.assertEqual(load_dataset(self.path), valid)
        original = self.path.read_bytes()
        broken = copy.deepcopy(valid)
        broken["appointments"][0]["status"] = "wrong"
        with self.assertRaises(ValueError):
            atomic_write_json(self.path, broken)
        self.assertEqual(self.path.read_bytes(), original)
        missing = copy.deepcopy(valid)
        del missing["appointments"]
        with self.assertRaises(ValueError):
            atomic_write_json(self.path, missing)
        self.assertEqual(self.path.read_bytes(), original)

    def test_failed_replace_preserves_old_file_and_cleans_temporary(self):
        data = update_dataset(None, [appointment()], NOW)
        atomic_write_json(self.path, data)
        old = self.path.read_bytes()
        with patch("blutspenden.storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                atomic_write_json(self.path, data)
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_separate_status_json_can_be_written(self):
        status = {"state": "error", "message": "Abruf fehlgeschlagen"}
        atomic_write_json(self.path, status)
        self.assertEqual(json.loads(self.path.read_text()), status)


if __name__ == "__main__":
    unittest.main()
