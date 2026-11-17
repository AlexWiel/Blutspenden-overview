"""Validated, atomic JSON snapshots and a rolling local-calendar-month archive.

Only complete successful source batches belong in ``update_dataset``. A failed
fetch must not be passed as an empty list. Fetch status is stored separately by
the caller, so a failure never rewrites the last successful appointment file.
"""

import calendar
import copy
import json
import os
import re
import tempfile
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo


VIENNA = ZoneInfo("Europe/Vienna")
SOURCE = "https://termine.blut.at"
SCHEMA_VERSION = 1
CITIES = {"Klagenfurt am Wörthersee", "Tamsweg"}
CONTENT_FIELDS = (
    "id", "uid", "source_url", "calendar_url", "source_event_id", "city",
    "venue", "address", "postal_code", "locality", "starts_at", "ends_at",
    "status",
)
TRACKING_FIELDS = ("first_seen_at", "last_seen_at", "last_changed_at", "availability")
VERIFICATION_FIELDS = ("verification_status", "verification_url", "verification_search_url")
DATASET_FIELDS = {
    "schema_version", "source", "last_successful_fetch", "archive_started_at",
    "history_start", "appointments",
}


def _datetime(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field}: ISO-Zeitstempel erwartet")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field}: ungültiger ISO-Zeitstempel") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}: Zeitzonenoffset fehlt")
    return result


def _aware_now(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now muss ein zeitzonenbewusster datetime sein")
    return now.astimezone(VIENNA)


def history_cutoff(now):
    """Previous calendar month's clamped day at local midnight, inclusive."""
    local = _aware_now(now)
    year, month = local.year, local.month - 1
    if month == 0:
        year, month = year - 1, 12
    day = min(local.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day, tzinfo=VIENNA)


def _source_path(url, field):
    if not isinstance(url, str):
        raise ValueError(f"{field}: Quellen-URL erwartet")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "termine.blut.at"
            or parsed.query or parsed.fragment):
        raise ValueError(f"{field}: ungültige Quellen-URL")
    return parsed.path


def _validate_content(record):
    if not isinstance(record, dict):
        raise ValueError("Termin muss ein Objekt sein")
    missing = set(CONTENT_FIELDS) - set(record)
    if missing:
        raise ValueError("Termin: fehlende Felder " + ", ".join(sorted(missing)))
    for field in CONTENT_FIELDS:
        if field == "ends_at":
            continue
        value = record[field]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{field}: nichtleerer getrimmter Text erwartet")
        if any(ord(character) < 32 for character in value):
            raise ValueError(f"{field}: Steuerzeichen nicht erlaubt")
    if record["id"] != "rotes-kreuz:" + record["uid"]:
        raise ValueError("id stimmt nicht mit uid überein")
    if record["city"] not in CITIES:
        raise ValueError("city: nicht unterstützte Stadt")
    aliases = ({"klagenfurt", "klagenfurt am wörthersee"}
               if record["city"] == "Klagenfurt am Wörthersee" else {"tamsweg"})
    if " ".join(record["locality"].casefold().split()) not in aliases:
        raise ValueError("locality stimmt nicht mit city überein")
    if not re.fullmatch(r"\d{4}", record["postal_code"]):
        raise ValueError("postal_code: vierstellige Postleitzahl erwartet")
    allowed_codes = ({"9020", "9061", "9073"}
                     if record["city"] == "Klagenfurt am Wörthersee" else {"5580"})
    if record["postal_code"] not in allowed_codes:
        raise ValueError("postal_code stimmt nicht mit city überein")
    path = _source_path(record["source_url"], "source_url")
    if not re.fullmatch(r"/termine/[A-Za-z0-9_-]+", path):
        raise ValueError("source_url: Termindetailpfad erwartet")
    if record["source_event_id"] != path.rsplit("/", 1)[1]:
        raise ValueError("source_event_id stimmt nicht mit source_url überein")
    if record["calendar_url"] != record["source_url"] + "/ics":
        raise ValueError("calendar_url stimmt nicht mit source_url überein")
    if record["status"] not in {"confirmed", "cancelled", "tentative"}:
        raise ValueError("status: ungültiger Terminstatus")
    start = _datetime(record["starts_at"], "starts_at")
    end = (_datetime(record["ends_at"], "ends_at")
           if record["ends_at"] is not None else None)
    for field, moment in (("starts_at", start), ("ends_at", end)):
        if moment is not None and moment.utcoffset() != moment.astimezone(VIENNA).utcoffset():
            raise ValueError(f"{field}: Europe/Vienna-Offset erwartet")
    if end is not None and end <= start:
        raise ValueError("ends_at muss nach starts_at liegen")


def _content(record):
    _validate_content(record)
    # Deliberately drop transport fields such as DTSTAMP; they are not changes.
    return {field: copy.deepcopy(record[field]) for field in CONTENT_FIELDS}


def _slot(record):
    return record["source_url"], _datetime(record["starts_at"], "starts_at")


def _retained(record, cutoff):
    if record["ends_at"] is not None:
        finish = _datetime(record["ends_at"], "ends_at")
    else:
        start_date = _datetime(record["starts_at"], "starts_at").astimezone(VIENNA).date()
        # Do not guess an event end; this is only a conservative pruning bound.
        finish = datetime.combine(start_date + timedelta(days=1), time.min, VIENNA)
    return finish >= cutoff


def verification_fields(record):
    """Derive a display status without overwriting the last observed source status."""
    if record["status"] == "cancelled":
        status = "abgesagt"
    elif record["availability"] == "not_listed":
        status = "unklar"
    else:
        status = "gelistet"
    klagenfurt = record["city"] == "Klagenfurt am Wörthersee"
    search = SOURCE + "/termine?" + urlencode({
        "search_form[term]": "Klagenfurt" if klagenfurt else "Tamsweg",
        "search_form[radius]": "0",
        "search_form[state_id]": "AT-2" if klagenfurt else "AT-5",
    })
    return {
        "verification_status": status,
        "verification_url": record["source_url"],
        "verification_search_url": search,
    }


def validate_dataset(data, *, allow_legacy=False):
    """Raise ValueError on unsupported, corrupt or internally inconsistent JSON."""
    if not isinstance(data, dict) or set(data) != DATASET_FIELDS:
        raise ValueError("Ungültige Datensatzfelder")
    if type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Nicht unterstützte schema_version")
    if data["source"] != SOURCE:
        raise ValueError("Ungültige Datenquelle")
    fetched = _datetime(data["last_successful_fetch"], "last_successful_fetch")
    archive = _datetime(data["archive_started_at"], "archive_started_at")
    cutoff = _datetime(data["history_start"], "history_start")
    if archive > fetched:
        raise ValueError("Archivbeginn liegt nach dem Abruf")
    if cutoff != history_cutoff(fetched):
        raise ValueError("history_start stimmt nicht mit dem Kalendermonat überein")
    if not isinstance(data["appointments"], list):
        raise ValueError("appointments muss eine Liste sein")
    ids, slots = set(), set()
    for record in data["appointments"]:
        _validate_content(record)
        if record["id"] in ids or _slot(record) in slots:
            raise ValueError("Doppelter Termin im Datenbestand")
        ids.add(record["id"])
        slots.add(_slot(record))
        base_fields = set(CONTENT_FIELDS) | set(TRACKING_FIELDS)
        legacy = allow_legacy and set(record) == base_fields
        if not legacy and set(record) != base_fields | set(VERIFICATION_FIELDS):
            raise ValueError("Ungültige Terminfelder im Archiv")
        first = _datetime(record["first_seen_at"], "first_seen_at")
        last = _datetime(record["last_seen_at"], "last_seen_at")
        changed = _datetime(record["last_changed_at"], "last_changed_at")
        if not archive <= first <= last <= fetched or not first <= changed <= last:
            raise ValueError("Inkonsistente Archiv-Zeitstempel")
        if record["availability"] not in {"listed", "not_listed"}:
            raise ValueError("Ungültiger Verfügbarkeitsstatus")
        if record["availability"] == "listed" and last != fetched:
            raise ValueError("Gelisteter Termin wurde nicht beim letzten Abruf gesehen")
        if not legacy and any(record[key] != value
                              for key, value in verification_fields(record).items()):
            raise ValueError("Prüfstatus oder Prüfverweis stimmt nicht mit dem Termin überein")
        if not _retained(record, cutoff):
            raise ValueError("Termin liegt außerhalb des Archivzeitraums")


def update_dataset(existing: Optional[dict], incoming: list, now: datetime) -> dict:
    """Merge a complete successful source result without mutating input objects.

    Exact duplicates are harmless; contradictory IDs/slots fail the whole batch.
    A changed UID is reconciled only when source URL and start instant agree.
    Missing records remain ``not_listed`` until outside the rolling archive.
    ``last_changed_at`` tracks source content, not listing availability/DTSTAMP.
    """
    local_now = _aware_now(now)
    stamp = local_now.isoformat()
    cutoff = history_cutoff(local_now)
    if existing is not None:
        validate_dataset(existing)
        if local_now < _datetime(existing["last_successful_fetch"], "last_successful_fetch"):
            raise ValueError("Abrufzeit liegt vor dem bestehenden Datenstand")
    if not isinstance(incoming, list):
        raise ValueError("incoming muss eine vollständige Liste sein")
    fresh, fresh_slots = {}, {}
    for raw in incoming:
        record = _content(raw)
        identity = record["id"]
        slot = _slot(record)
        if identity in fresh and fresh[identity] != record:
            raise ValueError("Widersprüchliche Termine mit gleicher UID")
        if slot in fresh_slots and fresh_slots[slot] != identity:
            raise ValueError("Mehrere UIDs für denselben Quelltermin und Beginn")
        fresh[identity] = record
        fresh_slots[slot] = identity

    previous = {item["id"]: item for item in existing["appointments"]} if existing else {}
    previous_slots = {_slot(item): item for item in previous.values()}
    consumed, merged = set(), []
    for identity, record in fresh.items():
        old = previous.get(identity)
        fallback = previous_slots.get(_slot(record))
        if old is not None and fallback is not None and old["id"] != fallback["id"]:
            raise ValueError("Mehrdeutige Änderung der Terminidentität")
        old = old or fallback
        if old is not None:
            if old["id"] in consumed:
                raise ValueError("Bestehender Termin mehrfach zugeordnet")
            consumed.add(old["id"])
            record.update({
                "first_seen_at": old["first_seen_at"],
                "last_seen_at": stamp,
                "last_changed_at": (old["last_changed_at"]
                                    if _content(old) == record else stamp),
                "availability": "listed",
            })
        else:
            record.update({"first_seen_at": stamp, "last_seen_at": stamp,
                           "last_changed_at": stamp, "availability": "listed"})
        if _retained(record, cutoff):
            merged.append(record)
    for identity, old in previous.items():
        if identity not in consumed and _retained(old, cutoff):
            record = copy.deepcopy(old)
            record["availability"] = "not_listed"
            merged.append(record)
    for record in merged:
        record.update(verification_fields(record))
    merged.sort(key=lambda item: (_datetime(item["starts_at"], "starts_at"), item["id"]))
    result = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "last_successful_fetch": stamp,
        "archive_started_at": existing["archive_started_at"] if existing else stamp,
        "history_start": cutoff.isoformat(),
        "appointments": merged,
    }
    validate_dataset(result)
    return result


def load_dataset(path: Path) -> Optional[dict]:
    """Return None only when the file is absent; never reset invalid state."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Doppelter JSON-Objektschlüssel")
            result[key] = value
        return result

    path = Path(path)
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream, object_pairs_hook=unique_object)
    except FileNotFoundError:
        return None
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Ungültige JSON-Datei: {path}") from error
    # Accept the initial local v1 format only if all derived fields are absent.
    # Validate the old content first, then enrich without altering fetch history.
    validate_dataset(data, allow_legacy=True)
    for record in data["appointments"]:
        record.update(verification_fields(record))
    validate_dataset(data)
    return data


def atomic_write_json(path: Path, data: dict):
    """Write JSON atomically; callers validate the appropriate document schema.

    The helper also writes the separately structured fetch-status document.
    Appointment datasets are validated here when source or appointments is set.
    """
    if not isinstance(data, dict):
        raise ValueError("JSON-Dokument muss ein Objekt sein")
    if "source" in data or "appointments" in data:
        validate_dataset(data)
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
