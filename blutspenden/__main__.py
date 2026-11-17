"""Manueller Import: python3 -m blutspenden --output-dir data."""

import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from .source import SourceClient
from .storage import atomic_write_json, load_dataset, update_dataset


VIENNA = ZoneInfo("Europe/Vienna")
CITIES = ("Klagenfurt am Wörthersee", "Tamsweg")


def diagnostic(error):
    # SourceClient exposes sanitized explanations, never response headers/bodies.
    return " ".join(str(error).split())[:500] or type(error).__name__


@contextmanager
def update_lock(directory):
    """Advisory process lock, released by the OS even when a run crashes."""
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".update.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Ein anderer Import läuft bereits.") from error
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run_update(output_dir, client=None, now=None):
    """Return 0 for a fully validated update, 1 on failure. No partial imports."""
    directory = Path(output_dir)
    now = now or datetime.now(VIENNA)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Der Abrufzeitpunkt muss eine Zeitzone enthalten.")
    now = now.astimezone(VIENNA)
    data_path = directory / "appointments.json"
    status_path = directory / "status.json"
    with update_lock(directory):
        existing = None
        try:
            existing = load_dataset(data_path)
            incoming = (client or SourceClient()).fetch_all()
            dataset = update_dataset(existing, incoming, now)
            counts = {city: sum(record["city"] == city for record in incoming)
                      for city in CITIES}
            status = {
                "schema_version": 1,
                "last_attempt": now.isoformat(),
                "last_successful_fetch": dataset["last_successful_fetch"],
                "state": "ok" if incoming else "empty",
                "fetched_counts": counts,
                "error": None,
            }
            atomic_write_json(data_path, dataset)
        except (OSError, ValueError, RuntimeError) as error:
            # Public status contains no transport internals, tokens or responses.
            # A corrupt archive is never silently replaced with an empty dataset.
            status = {
                "schema_version": 1,
                "last_attempt": now.isoformat(),
                "last_successful_fetch": (
                    existing["last_successful_fetch"] if existing else None
                ),
                "state": "error",
                "fetched_counts": None,
                "error": "Abruf oder Validierung fehlgeschlagen; letzter gültiger Bestand bleibt erhalten.",
                "error_type": type(error).__name__,
            }
            atomic_write_json(status_path, status)
            print("Import fehlgeschlagen: {}. Siehe status.json; vorhandene Termine wurden nicht ersetzt."
                  .format(diagnostic(error)), file=sys.stderr)
            return 1
        # If this write fails, data remains independently valid and dated. Do not
        # claim failure occurred before the already committed dataset update.
        atomic_write_json(status_path, status)
        print("Import erfolgreich: {} abgerufene Zeitfenster, {} gespeicherte Einträge."
              .format(len(incoming), len(dataset["appointments"])))
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Blutspendetermine abrufen und lokal archivieren.")
    parser.add_argument("--output-dir", type=Path, default=Path("data"),
                        help="Verzeichnis für appointments.json und status.json (Standard: data)")
    args = parser.parse_args(argv)
    try:
        return run_update(args.output_dir)
    except (OSError, ValueError, RuntimeError) as error:
        print("Import konnte nicht abgeschlossen werden: {}."
              .format(diagnostic(error)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
