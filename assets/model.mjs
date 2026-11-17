/** Date selection and validation for the static schedule. No DOM or network. */
const ZONE = 'Europe/Vienna';
const SOURCE = 'https://termine.blut.at';
const CITIES = new Set(['Klagenfurt am Wörthersee', 'Tamsweg']);
const dateFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
});
const timeFormatter = new Intl.DateTimeFormat('de-AT', {
  timeZone: ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});
const longDateFormatter = new Intl.DateTimeFormat('de-AT', {
  timeZone: ZONE, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
});

function require(condition, message) {
  if (!condition) throw new Error(`Ungültige Termindaten: ${message}`);
}
function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function text(value) {
  return typeof value === 'string' && value.trim() === value && value.length > 0
    && !/[\u0000-\u001f\u007f]/u.test(value);
}
function date(value) {
  const result = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  require(Number.isFinite(result.getTime()), 'Datum nicht lesbar.');
  return result;
}
function timestamp(value) {
  require(typeof value === 'string', 'Zeitstempel fehlt.');
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/u.exec(value);
  require(match, 'Zeitstempel mit Zeitzone erwartet.');
  const [, year, month, day, hour, minute, second, offset] = match;
  const days = new Date(Date.UTC(+year, +month, 0)).getUTCDate();
  require(+year >= 1000 && +month >= 1 && +month <= 12 && +day >= 1 && +day <= days
    && +hour <= 23 && +minute <= 59 && +second <= 59, 'Unmögliches Datum.');
  if (offset !== 'Z') require(+offset.slice(1, 3) <= 23 && +offset.slice(4) <= 59, 'Ungültiger Offset.');
  return date(value).getTime();
}

export function dateKey(value) {
  const parts = Object.fromEntries(dateFormatter.formatToParts(date(value))
    .filter(part => ['year', 'month', 'day'].includes(part.type))
    .map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
export function formatDate(value) { return longDateFormatter.format(date(value)); }
export function formatTime(value) { return timeFormatter.format(date(value)); }
function previousMonthDay(value) {
  const [year, month, day] = dateKey(value).split('-').map(Number);
  const previousYear = month === 1 ? year - 1 : year;
  const previousMonth = month === 1 ? 12 : month - 1;
  const lastDay = new Date(Date.UTC(previousYear, previousMonth, 0)).getUTCDate();
  return `${previousYear}-${String(previousMonth).padStart(2, '0')}-${String(Math.min(day, lastDay)).padStart(2, '0')}`;
}
function followingDay(key) {
  const [year, month, day] = key.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
}
function searchLink(value, city) {
  require(text(value), 'Prüflink fehlt.');
  let url;
  try { url = new URL(value); } catch { require(false, 'Prüflink nicht lesbar.'); }
  const klagenfurt = city === 'Klagenfurt am Wörthersee';
  const expected = {
    'search_form[term]': klagenfurt ? 'Klagenfurt' : 'Tamsweg',
    'search_form[radius]': '0',
    'search_form[state_id]': klagenfurt ? 'AT-2' : 'AT-5',
  };
  require(url.origin === SOURCE && !url.username && !url.password && !url.hash
    && url.pathname === '/termine' && [...url.searchParams].length === 3
    && Object.entries(expected).every(([key, val]) => url.searchParams.get(key) === val),
  'Prüflink führt nicht zur passenden offiziellen Stadtsuche.');
}

export function validateDataset(data) {
  require(object(data) && data.schema_version === 1 && data.source === SOURCE,
    'Nicht unterstütztes Datenformat.');
  const fetched = timestamp(data.last_successful_fetch);
  const archive = timestamp(data.archive_started_at);
  timestamp(data.history_start);
  require(archive <= fetched, 'Archivbeginn liegt nach dem Datenstand.');
  require(dateKey(data.history_start) === previousMonthDay(data.last_successful_fetch)
    && formatTime(data.history_start) === '00:00', 'Archivgrenze stimmt nicht.');
  require(Array.isArray(data.appointments), 'Terminliste fehlt.');
  const ids = new Set();
  const slots = new Set();
  for (const event of data.appointments) {
    require(object(event), 'Termin ist kein Objekt.');
    for (const key of ['id', 'uid', 'source_event_id', 'city', 'venue', 'address', 'postal_code', 'locality']) {
      require(text(event[key]), `Feld ${key} fehlt.`);
    }
    require(CITIES.has(event.city), 'Unbekannte Stadt.');
    const klagenfurt = event.city === 'Klagenfurt am Wörthersee';
    const locality = event.locality.toLocaleLowerCase('de-AT').replace(/\s+/gu, ' ');
    require((klagenfurt ? ['klagenfurt', 'klagenfurt am wörthersee'] : ['tamsweg']).includes(locality)
      && (klagenfurt ? ['9020', '9061', '9073'] : ['5580']).includes(event.postal_code),
    'Ort oder Postleitzahl stimmt nicht mit der Stadt überein.');
    require(event.id === `rotes-kreuz:${event.uid}` && !ids.has(event.id), 'Ungültige oder doppelte ID.');
    ids.add(event.id);
    require(typeof event.source_url === 'string' && /^https:\/\/termine\.blut\.at\/termine\/[A-Za-z0-9_-]+$/u.test(event.source_url)
      && event.source_url === `${SOURCE}/termine/${event.source_event_id}`,
    'Ungültiger offizieller Terminlink.');
    require(event.calendar_url === `${event.source_url}/ics`
      && event.verification_url === event.source_url, 'Kalender- oder Prüflink stimmt nicht.');
    searchLink(event.verification_search_url, event.city);
    const start = timestamp(event.starts_at);
    const end = event.ends_at === null ? null : timestamp(event.ends_at);
    require(end === null || end > start, 'Terminende liegt vor dem Beginn.');
    const slot = `${event.source_url}|${start}`;
    require(!slots.has(slot), 'Doppeltes Zeitfenster.');
    slots.add(slot);
    require(['confirmed', 'cancelled', 'tentative'].includes(event.status)
      && ['listed', 'not_listed'].includes(event.availability), 'Unbekannter Terminstatus.');
    const verification = event.status === 'cancelled' ? 'abgesagt'
      : event.availability === 'not_listed' ? 'unklar' : 'gelistet';
    require(event.verification_status === verification, 'Prüfstatus stimmt nicht.');
    const first = timestamp(event.first_seen_at);
    const seen = timestamp(event.last_seen_at);
    const changed = timestamp(event.last_changed_at);
    require(archive <= first && first <= changed && changed <= seen && seen <= fetched,
      'Sichtungszeitpunkte widersprechen sich.');
    require(event.availability !== 'listed' || seen === fetched, 'Gelisteter Termin ist nicht aktuell gesichtet.');
  }
  return data;
}

export function validateStatus(status) {
  require(object(status) && status.schema_version === 1
    && ['ok', 'empty', 'error'].includes(status.state), 'Aktualisierungsstatus nicht lesbar.');
  const attempt = timestamp(status.last_attempt);
  const success = status.last_successful_fetch === null ? null : timestamp(status.last_successful_fetch);
  require(success === null || success <= attempt, 'Aktualisierungszeitpunkte stimmen nicht.');
  if (status.state === 'error') {
    require(status.fetched_counts === null && text(status.error), 'Fehlerstatus ist unvollständig.');
  } else {
    require(success === attempt && object(status.fetched_counts) && status.error === null,
      'Erfolgsstatus ist unvollständig.');
    const counts = [...CITIES].map(city => status.fetched_counts[city]);
    require(counts.every(count => Number.isInteger(count) && count >= 0), 'Trefferzahlen fehlen.');
    const sum = counts.reduce((a, b) => a + b, 0);
    require(status.state === 'empty' ? sum === 0 : sum > 0, 'Trefferzahl widerspricht dem Status.');
  }
  return status;
}

export function selectAppointments(dataset, city = 'all', now = new Date()) {
  require(['all', 'klagenfurt', 'tamsweg'].includes(city), 'Ungültiger Stadtfilter.');
  const instant = date(now).getTime();
  const today = dateKey(now);
  const historyStart = previousMonthDay(now);
  const selectedCity = city === 'klagenfurt' ? 'Klagenfurt am Wörthersee' : 'Tamsweg';
  const upcoming = [];
  const past = [];
  for (const event of dataset.appointments) {
    if (city !== 'all' && event.city !== selectedCity) continue;
    const finished = event.ends_at === null ? dateKey(event.starts_at) < today
      : date(event.ends_at).getTime() <= instant;
    if (!finished) upcoming.push(event);
    else {
      const boundary = event.ends_at === null ? followingDay(dateKey(event.starts_at)) : dateKey(event.ends_at);
      if (boundary >= historyStart) past.push(event);
    }
  }
  const compare = (a, b) => date(a.starts_at) - date(b.starts_at) || a.id.localeCompare(b.id);
  upcoming.sort(compare);
  past.sort((a, b) => -compare(a, b));
  const next = upcoming.find(event => event.status === 'confirmed' && event.availability === 'listed'
    && event.verification_status === 'gelistet') ?? null;
  const started = dateKey(dataset.archive_started_at);
  const archiveDate = date(dataset.archive_started_at);
  const archiveIncomplete = started > historyStart
    || (started === historyStart && (formatTime(archiveDate) !== '00:00'
      || archiveDate.getUTCSeconds() !== 0 || archiveDate.getUTCMilliseconds() !== 0));
  return { upcoming, past, next, historyStart, historyEnd: today, archiveIncomplete };
}

export function getNotices(dataset, status, now = new Date()) {
  const notices = [];
  const instant = date(now).getTime();
  const fetched = date(dataset.last_successful_fetch).getTime();
  if (instant - fetched > 36 * 60 * 60 * 1000) {
    notices.push({ kind: 'warning', text: 'Die Daten sind älter als 36 Stunden. Bitte prüfen Sie Ihren Termin beim Roten Kreuz.' });
  }
  if (status === null) {
    notices.push({ kind: 'warning', text: 'Der Aktualisierungsstatus konnte nicht geladen werden. Angezeigt wird der zuletzt gespeicherte Terminbestand.' });
    return notices;
  }
  if (status.state === 'error') {
    notices.push({ kind: 'warning', text: 'Die letzte Aktualisierung ist fehlgeschlagen. Angezeigt werden die zuletzt erfolgreich geladenen Termine.' });
  }
  if (status.last_successful_fetch === null
    || date(status.last_successful_fetch).getTime() !== fetched) {
    notices.push({ kind: 'warning', text: 'Aktualisierungsstatus und Terminbestand stimmen zeitlich nicht überein. Bitte prüfen Sie Termine bei der offiziellen Quelle.' });
  }
  if (status.state === 'empty') {
    notices.push({ kind: 'info', text: 'Der letzte Abruf lieferte keine aktuell gelisteten Termine. Gespeicherte Archiveinträge können weiterhin angezeigt werden.' });
  }
  return notices;
}
