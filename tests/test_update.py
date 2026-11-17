import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from blutspenden.__main__ import run_update, update_lock


NOW = datetime(2026, 11, 17, 10, tzinfo=ZoneInfo("Europe/Vienna"))


def example():
    """Synthetic test data; never included in the live dataset."""
    return {
        "id": "rotes-kreuz:test-1", "uid": "test-1",
        "source_url": "https://termine.blut.at/termine/test",
        "calendar_url": "https://termine.blut.at/termine/test/ics",
        "source_event_id": "test", "city": "Tamsweg",
        "venue": "Testort", "address": "Teststraße 1",
        "postal_code": "5580", "locality": "Tamsweg",
        "starts_at": "2026-11-20T15:00:00+01:00",
        "ends_at": "2026-11-20T20:00:00+01:00", "status": "confirmed",
    }


class Client:
    def __init__(self, records=None, error=None):
        self.records = records if records is not None else []
        self.error = error

    def fetch_all(self):
        if self.error:
            raise self.error
        return self.records


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.output = io.StringIO()

    def update(self, client):
        with contextlib.redirect_stdout(self.output), contextlib.redirect_stderr(self.output):
            return run_update(self.directory, client, NOW)

    def read(self, name):
        return json.loads((self.directory / name).read_text(encoding="utf-8"))

    def test_failure_preserves_valid_dataset_byte_for_byte(self):
        self.assertEqual(self.update(Client([example()])), 0)
        before = (self.directory / "appointments.json").read_bytes()
        self.assertEqual(self.update(Client(error=RuntimeError("network"))), 1)
        self.assertEqual((self.directory / "appointments.json").read_bytes(), before)
        status = self.read("status.json")
        self.assertEqual(status["state"], "error")
        self.assertEqual(status["last_successful_fetch"], NOW.isoformat())

    def test_initial_failure_does_not_create_fake_empty_dataset(self):
        self.assertEqual(self.update(Client(error=ValueError("invalid response"))), 1)
        self.assertFalse((self.directory / "appointments.json").exists())
        self.assertIsNone(self.read("status.json")["last_successful_fetch"])

    def test_successful_empty_is_distinct_from_failure_and_retains_archive(self):
        self.assertEqual(self.update(Client([example()])), 0)
        self.assertEqual(self.update(Client([])), 0)
        self.assertEqual(self.read("status.json")["state"], "empty")
        event = self.read("appointments.json")["appointments"][0]
        self.assertEqual(event["availability"], "not_listed")
        self.assertEqual(event["status"], "confirmed")

    def test_invalid_incoming_does_not_replace_dataset(self):
        self.assertEqual(self.update(Client([example()])), 0)
        before = (self.directory / "appointments.json").read_bytes()
        bad = example()
        bad["ends_at"] = "2026-11-20T10:00:00+01:00"
        self.assertEqual(self.update(Client([bad])), 1)
        self.assertEqual((self.directory / "appointments.json").read_bytes(), before)

    def test_corrupt_existing_dataset_is_not_discarded(self):
        path = self.directory / "appointments.json"
        path.write_bytes(b"broken")
        self.assertEqual(self.update(Client([example()])), 1)
        self.assertEqual(path.read_bytes(), b"broken")
        self.assertEqual(self.read("status.json")["state"], "error")

    def test_concurrent_update_rejected(self):
        with update_lock(self.directory):
            with self.assertRaises(RuntimeError):
                self.update(Client([]))
        self.assertFalse((self.directory / "appointments.json").exists())


if __name__ == "__main__":
    unittest.main()
