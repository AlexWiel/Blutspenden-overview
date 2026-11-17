"""Normalize the inspected Red Cross per-appointment iCalendar exports.

This intentionally supports a bounded, non-recurring VEVENT subset. Unsupported
or incomplete input raises ValueError rather than silently losing appointments.
Floating source times are interpreted in Europe/Vienna; missing end times remain
unknown. An absent STATUS is not taken as a confirmation.
"""

import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


VIENNA = ZoneInfo("Europe/Vienna")
CITY_ALIASES = {
    "klagenfurt": "Klagenfurt am Wörthersee",
    "klagenfurt am wörthersee": "Klagenfurt am Wörthersee",
    "tamsweg": "Tamsweg",
}
CITY_POSTAL_CODES = {
    "Klagenfurt am Wörthersee": {"9020", "9061", "9073"},
    "Tamsweg": {"5580"},
}
REQUIRED_PROPERTIES = {"UID", "DTSTART", "LOCATION", "STATUS"}
SINGLE_PROPERTIES = REQUIRED_PROPERTIES | {"DTEND", "DURATION"}
UNSUPPORTED_PROPERTIES = {"RRULE", "RDATE", "EXDATE", "RECURRENCE-ID", "DURATION"}


def _city(value):
    key = " ".join(value.split()).casefold()
    if key not in CITY_ALIASES:
        raise ValueError("Unbekannte oder nicht unterstützte Stadt: " + value)
    return CITY_ALIASES[key]


def _text(value):
    """Decode iCalendar TEXT escaping without turning arbitrary slashes into text."""
    result = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == "\\":
            index += 1
            if index == len(value):
                raise ValueError("Unvollständige iCalendar-Textkodierung")
            escaped = value[index]
            if escaped in ("n", "N"):
                result.append("\n")
            elif escaped in ("\\", ",", ";"):
                result.append(escaped)
            else:
                raise ValueError("Unbekannte iCalendar-Textkodierung")
        else:
            result.append(character)
        index += 1
    return "".join(result)


def _property(line):
    """Read the property name, simple parameters and value of one content line."""
    header, colon, value = line.partition(":")
    if not colon:
        raise ValueError("iCalendar-Zeile ohne Doppelpunkt")
    parts = header.split(";")
    name = parts[0].upper()
    if not re.fullmatch(r"[A-Z0-9-]+", name):
        raise ValueError("Ungültiger iCalendar-Eigenschaftsname")
    parameters = {}
    for part in parts[1:]:
        key, equals, parameter = part.partition("=")
        key = key.upper()
        if not equals or not key or key in parameters:
            raise ValueError("Ungültige oder doppelte iCalendar-Parameter")
        parameters[key] = parameter.strip('"')
    return name, parameters, value


def _events(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Leerer Kalender")
    physical_lines = text.lstrip("\ufeff").replace("\r\n", "\n").split("\n")
    lines = []
    for line in physical_lines:
        if line.startswith((" ", "\t")):
            if not lines:
                raise ValueError("Kalender beginnt mit einer gefalteten Zeile")
            lines[-1] += line[1:]
        elif line:
            lines.append(line)
    stack = []
    events = []
    current = None
    calendars = 0
    for line in lines:
        name, parameters, value = _property(line)
        if name == "BEGIN":
            component = value.upper()
            if component == "VCALENDAR":
                if stack or calendars:
                    raise ValueError("Mehrere oder verschachtelte Kalender")
                calendars += 1
            elif not stack:
                raise ValueError("Kalenderkomponente außerhalb VCALENDAR")
            if component == "VEVENT":
                if stack != ["VCALENDAR"]:
                    raise ValueError("Verschachteltes VEVENT")
                current = {}
            stack.append(component)
        elif name == "END":
            component = value.upper()
            if not stack or stack[-1] != component:
                raise ValueError("Nicht geschlossene Kalenderkomponente")
            if component == "VEVENT":
                events.append(current)
                current = None
            stack.pop()
        elif not stack:
            raise ValueError("Eigenschaft außerhalb VCALENDAR")
        elif stack == ["VCALENDAR", "VEVENT"]:
            if name in UNSUPPORTED_PROPERTIES:
                raise ValueError("Nicht unterstützte Kalender-Eigenschaft: " + name)
            if name in SINGLE_PROPERTIES:
                if name in current:
                    raise ValueError("Doppelte Kalender-Eigenschaft: " + name)
                current[name] = (parameters, value)
    if stack or calendars != 1 or not events:
        raise ValueError("Unvollständiger Kalender oder kein VEVENT")
    return events


def _date_time(item):
    parameters, value = item
    if set(parameters) - {"TZID", "VALUE"}:
        raise ValueError("Nicht unterstützter Datumsparameter")
    if parameters.get("VALUE", "DATE-TIME").upper() != "DATE-TIME":
        raise ValueError("Termine ohne Uhrzeit werden nicht unterstützt")
    if not re.fullmatch(r"\d{8}T\d{6}Z?", value):
        raise ValueError("Ungültige iCalendar-Uhrzeit")
    utc = value.endswith("Z")
    if utc and "TZID" in parameters:
        raise ValueError("UTC-Uhrzeit darf keine TZID tragen")
    try:
        naive = datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
    except ValueError as error:
        raise ValueError("Ungültiges Datum") from error
    if utc:
        return naive.replace(tzinfo=timezone.utc).astimezone(VIENNA)
    try:
        zone = ZoneInfo(parameters.get("TZID", "Europe/Vienna"))
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Unbekannte Kalender-Zeitzone") from error
    candidates = {}
    for fold in (0, 1):
        aware = naive.replace(tzinfo=zone, fold=fold)
        round_trip = aware.astimezone(timezone.utc).astimezone(zone)
        if round_trip.replace(tzinfo=None) == naive:
            candidates[aware.utcoffset()] = aware
    if len(candidates) != 1:
        raise ValueError("Mehrdeutige oder nicht existierende lokale Uhrzeit")
    return next(iter(candidates.values())).astimezone(VIENNA)


def _location(item, expected_city):
    parameters, value = item
    if parameters.get("VALUE", "TEXT").upper() != "TEXT":
        raise ValueError("LOCATION muss ein Text sein")
    parts = [part.strip() for part in _text(value).rsplit(",", 2)]
    if len(parts) != 3 or not all(parts):
        raise ValueError("LOCATION enthält keine vollständige Adresse")
    venue, address, postal_locality = parts
    match = re.fullmatch(r"(\d{4})\s+(.+)", postal_locality)
    if not match:
        raise ValueError("LOCATION enthält keine österreichische PLZ und Stadt")
    postal_code, locality = match.groups()
    city = _city(locality)
    if city != expected_city or postal_code not in CITY_POSTAL_CODES[city]:
        raise ValueError("Termin liegt außerhalb der angefragten Stadt")
    for part in (venue, address, locality):
        if any(ord(character) < 32 for character in part):
            raise ValueError("Adresse enthält Steuerzeichen")
    return {
        "city": city,
        "venue": venue,
        "address": address,
        "postal_code": postal_code,
        "locality": locality,
    }


def parse_calendar(text: str, source_url: str, expected_city: str) -> list[dict]:
    """Return validated appointment records from a source's per-event export.

    Repeated identical VEVENTs collapse. Conflicting copies of a UID, recurrences,
    incomplete addresses and unsupported time forms fail the entire export.
    """
    expected_city = _city(expected_city)
    parsed_url = urlsplit(source_url)
    if (parsed_url.scheme != "https" or parsed_url.netloc != "termine.blut.at"
            or parsed_url.query or parsed_url.fragment
            or not re.fullmatch(r"/termine/[A-Za-z0-9_-]+", parsed_url.path)):
        raise ValueError("Ungültige offizielle Termin-URL")
    records = {}
    for event in _events(text):
        missing = REQUIRED_PROPERTIES - event.keys()
        if missing:
            raise ValueError("Fehlende Kalenderfelder: " + ", ".join(sorted(missing)))
        uid = _text(event["UID"][1]).strip()
        if not uid or any(ord(character) < 32 for character in uid):
            raise ValueError("Ungültige Kalender-UID")
        status = event["STATUS"][1].lower()
        if status not in {"confirmed", "cancelled", "tentative"}:
            raise ValueError("Unbekannter Terminstatus")
        start = _date_time(event["DTSTART"])
        end = _date_time(event["DTEND"]) if "DTEND" in event else None
        if (end is not None
                and end.astimezone(timezone.utc) <= start.astimezone(timezone.utc)):
            raise ValueError("Terminende liegt nicht nach Beginn")
        record = {
            "id": "rotes-kreuz:" + uid,
            "uid": uid,
            "source_url": source_url,
            "calendar_url": source_url + "/ics",
            "source_event_id": parsed_url.path.rsplit("/", 1)[-1],
            **_location(event["LOCATION"], expected_city),
            "starts_at": start.isoformat(),
            "ends_at": end.isoformat() if end else None,
            "status": status,
        }
        if uid in records and records[uid] != record:
            raise ValueError("Widersprüchliche Kalenderereignisse mit gleicher UID")
        records[uid] = record
    return sorted(records.values(), key=lambda record: (
        datetime.fromisoformat(record["starts_at"]), record["id"]))
