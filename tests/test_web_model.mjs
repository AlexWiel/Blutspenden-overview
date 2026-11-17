import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateDataset, validateStatus, selectAppointments, dateKey, formatDate, formatTime, getNotices } from '../assets/model.mjs';

const NOW = new Date('2026-11-17T12:00:00+01:00');
const FETCH = '2026-11-17T10:00:00+01:00';
function event(id, changes = {}) {
  const city = changes.city ?? 'Klagenfurt am Wörthersee';
  const kla = city === 'Klagenfurt am Wörthersee';
  const url = `https://termine.blut.at/termine/${id}`;
  const result = {
    id: `rotes-kreuz:${id}`, uid: id, source_event_id: id, city,
    source_url: url, calendar_url: `${url}/ics`, venue: 'Synthetischer Testort',
    address: 'Teststraße 1', postal_code: kla ? '9020' : '5580', locality: kla ? 'Klagenfurt' : 'Tamsweg',
    starts_at: '2026-11-18T09:00:00+01:00', ends_at: '2026-11-18T13:00:00+01:00',
    status: 'confirmed', availability: 'listed', verification_status: 'gelistet',
    verification_url: url,
    verification_search_url: `https://termine.blut.at/termine?${new URLSearchParams({
      'search_form[term]': kla ? 'Klagenfurt' : 'Tamsweg', 'search_form[radius]': '0',
      'search_form[state_id]': kla ? 'AT-2' : 'AT-5',
    })}`,
    first_seen_at: FETCH, last_seen_at: FETCH, last_changed_at: FETCH,
    ...changes,
  };
  return result;
}
function dataset(appointments = [], changes = {}) {
  return { schema_version: 1, source: 'https://termine.blut.at', last_successful_fetch: FETCH,
    archive_started_at: FETCH, history_start: '2026-10-17T00:00:00+02:00', appointments, ...changes };
}
function status(changes = {}) {
  return { schema_version: 1, state: 'ok', last_attempt: FETCH, last_successful_fetch: FETCH,
    fetched_counts: { 'Klagenfurt am Wörthersee': 1, Tamsweg: 0 }, error: null, ...changes };
}
function select(appointments, city = 'all', now = NOW) {
  return selectAppointments(dataset(appointments), city, now);
}

test('actual versioned dataset and update status validate', () => {
  const raw = JSON.parse(readFileSync(new URL('../data/appointments.json', import.meta.url)));
  assert.equal(validateDataset(raw), raw);
  const rawStatus = JSON.parse(readFileSync(new URL('../data/status.json', import.meta.url)));
  assert.equal(validateStatus(rawStatus), rawStatus);
});
test('empty dataset is valid and produces genuine empty lists', () => {
  const data = dataset();
  validateDataset(data);
  assert.deepEqual(selectAppointments(data, 'all', NOW).upcoming, []);
  assert.equal(selectAppointments(data, 'all', NOW).next, null);
});
test('filters both canonical cities and chronologically sorts without mutating input', () => {
  const late = event('late', { starts_at: '2026-11-20T09:00:00+01:00', ends_at: '2026-11-20T12:00:00+01:00' });
  const early = event('early', { city: 'Tamsweg' });
  const items = [late, early];
  assert.deepEqual(select(items).upcoming.map(x => x.uid), ['early', 'late']);
  assert.deepEqual(items.map(x => x.uid), ['late', 'early']);
  assert.deepEqual(select(items, 'tamsweg').upcoming.map(x => x.uid), ['early']);
  assert.deepEqual(select(items, 'klagenfurt').upcoming.map(x => x.uid), ['late']);
  assert.throws(() => select(items, 'graz'));
});
test('running event is upcoming, exact end switches it to past', () => {
  const running = event('running', { starts_at: '2026-11-17T11:00:00+01:00', ends_at: '2026-11-17T13:00:00+01:00' });
  assert.equal(select([running]).next, running);
  const result = select([running], 'all', new Date(running.ends_at));
  assert.equal(result.upcoming.length, 0);
  assert.equal(result.past[0], running);
});
test('unclear, cancelled and tentative events are visible but not next highlighted', () => {
  const items = [
    event('unclear', { availability: 'not_listed', verification_status: 'unklar' }),
    event('cancelled', { status: 'cancelled', verification_status: 'abgesagt' }),
    event('tentative', { status: 'tentative' }),
  ];
  assert.equal(select(items).upcoming.length, 3);
  assert.equal(select(items).next, null);
});
test('past events are newest first, outside rolling month is excluded', () => {
  const items = [
    event('old', { starts_at: '2026-10-15T09:00:00+02:00', ends_at: '2026-10-15T13:00:00+02:00' }),
    event('recent', { starts_at: '2026-11-16T09:00:00+01:00', ends_at: '2026-11-16T13:00:00+01:00' }),
    event('boundary', { starts_at: '2026-10-16T23:00:00+02:00', ends_at: '2026-10-17T00:00:00+02:00' }),
  ];
  assert.deepEqual(select(items).past.map(x => x.uid), ['recent', 'boundary']);
});
test('previous month cutoff clamps leap years, month ends and year transition', () => {
  for (const [now, expected] of [
    ['2028-03-31T12:00:00+02:00', '2028-02-29'],
    ['2027-03-31T12:00:00+02:00', '2027-02-28'],
    ['2026-01-31T12:00:00+01:00', '2025-12-31'],
  ]) assert.equal(select([], 'all', new Date(now)).historyStart, expected);
});
test('Vienna local date, not browser or UTC date, determines cutoff', () => {
  const result = select([], 'all', new Date('2026-04-01T22:30:00Z'));
  assert.equal(result.historyEnd, '2026-04-02');
  assert.equal(result.historyStart, '2026-03-02');
  assert.equal(dateKey('2026-11-17T23:30:00Z'), '2026-11-18');
});
test('unknown end stays upcoming for its Vienna day and past next local day', () => {
  const unknown = event('unknown', { starts_at: '2026-11-17T09:00:00+01:00', ends_at: null });
  assert.equal(select([unknown]).upcoming[0], unknown);
  assert.equal(select([unknown], 'all', new Date('2026-11-17T23:00:00Z')).past[0], unknown);
});
test('unknown end pruning matches conservative next-midnight archive bound', () => {
  const unknown = event('unknown', { starts_at: '2026-10-16T09:00:00+02:00', ends_at: null });
  assert.equal(select([unknown]).past.length, 1);
  assert.equal(select([unknown], 'all', new Date('2026-11-18T12:00:00+01:00')).past.length, 0);
});
test('chronological ordering uses real instants during autumn DST fold', () => {
  const later = event('later', { starts_at: '2026-10-25T02:10:00+01:00', ends_at: '2026-10-25T03:00:00+01:00' });
  const earlier = event('earlier', { starts_at: '2026-10-25T02:30:00+02:00', ends_at: '2026-10-25T02:50:00+02:00' });
  assert.deepEqual(select([later, earlier], 'all', new Date('2026-10-24T12:00:00Z')).upcoming.map(x => x.uid), ['earlier', 'later']);
});
test('formatter consistently renders Vienna winter and summer hours', () => {
  assert.equal(formatTime('2026-11-17T12:00:00Z'), '13:00');
  assert.equal(formatTime('2026-07-17T12:00:00Z'), '14:00');
  assert.match(formatDate('2026-11-17T12:00:00Z'), /17\. November 2026/u);
});
test('archive coverage is not inferred from requested history boundary alone', () => {
  assert.equal(selectAppointments(dataset(), 'all', NOW).archiveIncomplete, true);
  assert.equal(selectAppointments(dataset([], { archive_started_at: '2026-10-16T00:00:00+02:00' }), 'all', NOW).archiveIncomplete, false);
});
test('invalid records, duplicates, impossible dates, naive times and contradictions fail', () => {
  for (const change of [
    { starts_at: '2026-02-30T09:00:00+01:00' }, { starts_at: '2026-11-18T09:00:00' },
    { ends_at: '2026-11-18T08:00:00+01:00' }, { venue: '' }, { city: 'Graz' },
    { postal_code: '9999' }, { verification_status: 'abgesagt' }, { last_seen_at: '2026-11-20T10:00:00+01:00' },
  ]) assert.throws(() => validateDataset(dataset([event('test', change)])), JSON.stringify(change));
  assert.throws(() => validateDataset(dataset([event('same'), event('same')])));
  assert.throws(() => validateDataset({ appointments: [] }));
});
test('untrusted destination links, mixed filters and duplicated search keys fail', () => {
  for (const change of [
    { source_url: 'javascript:alert(1)' }, { verification_url: 'https://evil.example/' },
    { verification_search_url: 'https://termine.blut.at.evil.example/termine' },
    { calendar_url: 'https://evil.example/a.ics' },
    { verification_search_url: event('test', { city: 'Tamsweg' }).verification_search_url },
    { verification_search_url: `${event('test').verification_search_url}&search_form%5Bterm%5D=Klagenfurt` },
  ]) assert.throws(() => validateDataset(dataset([event('test', change)])));
});
test('status success, real empty and source failure are distinct', () => {
  assert.equal(validateStatus(status()).state, 'ok');
  assert.equal(validateStatus(status({ state: 'empty', fetched_counts: { 'Klagenfurt am Wörthersee': 0, Tamsweg: 0 } })).state, 'empty');
  assert.equal(validateStatus(status({ state: 'error', fetched_counts: null, error: 'Abruf fehlgeschlagen', last_successful_fetch: null })).state, 'error');
  assert.throws(() => validateStatus(status({ state: 'empty' })));
  assert.throws(() => validateStatus(status({ state: 'error' })));
  assert.throws(() => validateStatus(status({ last_attempt: 'not-a-date' })));
});
test('status failures never discard cached appointments or expose raw error text', () => {
  const data = dataset([event('test')]);
  const notices = getNotices(data, status({ state: 'error', fetched_counts: null, error: '<secret response>' }), NOW);
  assert.ok(notices.some(n => /fehlgeschlagen/u.test(n.text)));
  assert.ok(notices.every(n => !n.text.includes('secret')));
  assert.equal(selectAppointments(data, 'all', NOW).upcoming.length, 1);
});
test('missing status, stale data and mismatched snapshots produce warnings', () => {
  assert.ok(getNotices(dataset(), null, NOW).some(n => /nicht geladen/u.test(n.text)));
  assert.ok(getNotices(dataset(), status(), new Date('2026-11-19T12:00:00+01:00')).some(n => /36 Stunden/u.test(n.text)));
  assert.ok(getNotices(dataset(), status({ last_attempt: '2026-11-16T10:00:00+01:00', last_successful_fetch: '2026-11-16T10:00:00+01:00' }), NOW).some(n => /zeitlich/u.test(n.text)));
  assert.equal(getNotices(dataset(), status(), NOW).length, 0);
});
test('empty fetch notice explicitly allows retained archive entries', () => {
  const notices = getNotices(dataset(), status({ state: 'empty' }), NOW);
  assert.ok(notices.some(n => n.kind === 'info' && /Archiveinträge/u.test(n.text)));
});
