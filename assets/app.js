import {
  validateDataset, validateStatus, selectAppointments,
  dateKey, formatDate, formatTime, getNotices,
} from './model.mjs';

const byId = (id) => document.getElementById(id);
let dataset = null;
let fetchStatus = null;
let loading = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function datedTime(value) {
  const time = element('time', '', `${formatDate(value)}, ${formatTime(value)} Uhr`);
  time.dateTime = value;
  return time;
}

function link(label, url) {
  const anchor = element('a', '', label);
  anchor.href = url;
  return anchor;
}

function statusFor(record, now) {
  if (record.status === 'cancelled') return ['Abgesagt', 'status-cancelled'];
  if (record.verification_status === 'unklar') return ['Unklar', 'status-unclear'];
  if (record.status === 'tentative') return ['Vorläufig', 'status-tentative'];
  if (new Date(record.starts_at) <= now && record.ends_at && new Date(record.ends_at) > now) {
    return ['Findet gerade statt', 'status-running'];
  }
  return ['Gelistet', 'status-listed'];
}

function appointmentCard(record, now, featured = false) {
  const card = element('article', `appointment-card${featured ? ' featured' : ''}`);
  if (featured) card.append(element('h2', 'eyebrow', 'Nächster gelisteter Termin'));
  const header = element('div', 'appointment-header');
  header.append(element('p', 'appointment-city', record.city));
  const [label, modifier] = statusFor(record, now);
  header.append(element('span', `appointment-status ${modifier}`, label));
  card.append(header);
  const date = element('time', 'appointment-date', formatDate(record.starts_at));
  date.dateTime = record.starts_at;
  card.append(date);
  let timeText = `${formatTime(record.starts_at)} Uhr`;
  if (record.ends_at) {
    timeText += dateKey(record.ends_at) === dateKey(record.starts_at)
      ? ` – ${formatTime(record.ends_at)} Uhr`
      : ` – ${formatDate(record.ends_at)}, ${formatTime(record.ends_at)} Uhr`;
  } else {
    timeText += ' · Ende nicht angegeben';
  }
  card.append(element('p', 'appointment-time', timeText));
  card.append(element('h3', 'appointment-venue', record.venue));
  card.append(element('p', 'appointment-address', `${record.address}, ${record.postal_code} ${record.locality}`));
  if (record.verification_status === 'unklar') {
    const note = element('p', 'appointment-note',
      'Nicht mehr in der aktuellen Suche gelistet. Bitte den Termin beim Roten Kreuz prüfen. Zuletzt gelistet: ');
    note.append(datedTime(record.last_seen_at));
    card.append(note);
  } else if (record.status === 'cancelled') {
    card.append(element('p', 'appointment-note', 'Vom Roten Kreuz als abgesagt gemeldet.'));
  } else if (record.status === 'tentative') {
    card.append(element('p', 'appointment-note', 'Vorläufiger Quellstatus. Bitte vor der Anreise prüfen.'));
  }
  const links = element('div', 'appointment-links');
  links.append(link('Termin beim Roten Kreuz prüfen', record.verification_url));
  links.append(link(`Terminsuche ${record.city === 'Tamsweg' ? 'Tamsweg' : 'Klagenfurt'}`,
    record.verification_search_url));
  card.append(links);
  return card;
}

function renderList(id, records, now) {
  const fragment = document.createDocumentFragment();
  for (const record of records) {
    const item = element('li', 'appointment-item');
    item.append(appointmentCard(record, now));
    fragment.append(item);
  }
  byId(id).replaceChildren(fragment);
}

function render() {
  if (!dataset) return;
  const city = document.querySelector('input[name="city"]:checked')?.value || 'all';
  const now = new Date();
  const selection = selectAppointments(dataset, city, now);
  renderList('upcoming-list', selection.upcoming, now);
  renderList('past-list', selection.past, now);
  byId('upcoming-empty').hidden = selection.upcoming.length !== 0;
  byId('past-empty').hidden = selection.past.length !== 0;
  byId('next-appointment').replaceChildren();
  byId('next-appointment').hidden = selection.next === null;
  if (selection.next) byId('next-appointment').append(appointmentCard(selection.next, now, true));
  const cityName = city === 'all' ? 'Beide Städte' : city === 'tamsweg' ? 'Tamsweg' : 'Klagenfurt';
  byId('results-summary').textContent = `${cityName}: ${selection.upcoming.length} kommende oder laufende Termine, ${selection.past.length} vergangene Termine.`;
  byId('update-summary').replaceChildren(
    document.createTextNode('Letzter erfolgreicher Abruf: '),
    datedTime(dataset.last_successful_fetch),
    document.createTextNode(' · Ortszeit Österreich'),
  );
  byId('notices').replaceChildren(...getNotices(dataset, fetchStatus, now).map((notice) =>
    element('p', `notice${notice.kind === 'warning' ? ' notice-warning' : ''}`, notice.text)));
  byId('history-range').textContent = `${formatDate(`${selection.historyStart}T12:00:00Z`)} bis heute`;
  byId('history-note').textContent = selection.archiveIncomplete
    ? `Das Archiv wächst seit ${formatDate(dataset.archive_started_at)}. Der erste Rückblickmonat ist noch nicht vollständig abgedeckt.`
    : 'Gespeicherte Termine im angezeigten Zeitraum. Unklare Einträge sind keine bestätigten Absagen.';
}

async function fetchJson(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(new URL(path, document.baseURI), {
      cache: 'no-store', credentials: 'omit', signal: controller.signal,
    });
    if (!response.ok) throw new Error('Datei nicht verfügbar');
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function load() {
  if (loading) return;
  const retryFocused = document.activeElement === byId('retry-button');
  loading = true;
  byId('loading-state').hidden = false;
  byId('error-state').hidden = true;
  byId('content').hidden = true;
  byId('retry-button').disabled = true;
  try {
    const [dataResult, statusResult] = await Promise.allSettled([
      fetchJson('./data/appointments.json'), fetchJson('./data/status.json'),
    ]);
    if (dataResult.status !== 'fulfilled') throw new Error('Termindaten fehlen');
    dataset = validateDataset(dataResult.value);
    fetchStatus = null;
    if (statusResult.status === 'fulfilled') {
      try { fetchStatus = validateStatus(statusResult.value); } catch { /* Show a status warning. */ }
    }
    render();
    byId('content').hidden = false;
    if (retryFocused) {
      byId('results-summary').tabIndex = -1;
      byId('results-summary').focus({ preventScroll: true });
    }
  } catch {
    dataset = null;
    byId('error-state').hidden = false;
  } finally {
    loading = false;
    byId('loading-state').hidden = true;
    byId('retry-button').disabled = false;
  }
}

document.querySelectorAll('input[name="city"]').forEach((radio) => {
  radio.addEventListener('change', render);
});
byId('retry-button').addEventListener('click', load);

setInterval(() => {
  // Keep time-based labels current without removing a currently focused link.
  const focusInCards = document.activeElement?.closest('#upcoming-list, #past-list, #next-appointment');
  if (!document.hidden && !focusInCards) render();
}, 60000);
load();
