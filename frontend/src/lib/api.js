// API client for the local Dynasty+ Tools backend.
async function getJSON(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    let detail = '';
    try { detail = (await response.json()).error || ''; } catch { /* ignore */ }
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function sendJSON(method, url, body) {
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!response.ok) {
    let detail = '';
    try { detail = (await response.json()).error || ''; } catch { /* ignore */ }
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

const postJSON = (url, body) => sendJSON('POST', url, body);
const putJSON = (url, body) => sendJSON('PUT', url, body);
const deleteJSON = (url) => sendJSON('DELETE', url);

function pointerQuery(year, week) {
  const params = new URLSearchParams();
  if (year != null) params.set('year', year);
  if (week != null) params.set('week', week);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export const api = {
  config: () => getJSON('/api/config'),
  setAutosync: (enabled) => postJSON('/api/autosync', { enabled }),
  teams: () => getJSON('/api/teams'),
  conferences: () => getJSON('/api/conferences'),
  state: () => getJSON('/api/state'),

  setupStatus: () => getJSON('/api/setup/status'),
  setupDetect: () => getJSON('/api/setup/detect'),
  setupPaths: (body) => postJSON('/api/setup/paths', body),
  setupExtract: (body) => postJSON('/api/setup/extract', body || {}),
  setupExtractStatus: () => getJSON('/api/setup/extract/status'),

  dynasties: () => getJSON('/api/dynasties'),
  scan: () => postJSON('/api/scan'),
  selectDynasty: (id) => postJSON('/api/dynasty/select', { id }),
  removeDynasty: (id) => deleteJSON(`/api/dynasty/${encodeURIComponent(id)}`),
  browseSaves: () => getJSON('/api/saves/browse'),
  saveTeams: (path) => getJSON(`/api/saves/teams?path=${encodeURIComponent(path)}`),
  importDynasty: (savePath, school) => postJSON('/api/dynasty/import', {
    save_path: savePath,
    school,
  }),
  dynasty: (year, week) => getJSON(`/api/dynasty${pointerQuery(year, week)}`),

  recruitingTool: () => getJSON('/api/recruiting/tool'),
  saveRecruitingTool: (body) => putJSON('/api/recruiting/tool', body),
  applyRecruiting: () => postJSON('/api/recruiting/apply'),
  recruitingReloadComplete: () => postJSON('/api/recruiting/reload-complete'),

  conferenceSetup: () => getJSON('/api/conferences/setup'),
  saveConferenceSetup: (conferences) => putJSON('/api/conferences/setup', { conferences }),
  resetConferenceSetup: () => postJSON('/api/conferences/setup/reset'),
  historicConfLogos: () => getJSON('/api/conferences/historic-logos'),
  modToolsStatus: () => getJSON('/api/modtools/status'),
  setModToolsPath: (path) => postJSON('/api/modtools/path', { path }),
  openModManager: () => postJSON('/api/modtools/open'),
  exportConferenceMod: () => postJSON('/api/conferences/mod/export'),

  scheduleSetup: () => getJSON('/api/schedule/setup'),
  saveScheduleSetup: (rules) => putJSON('/api/schedule/setup', rules),
  resetScheduleSetup: () => postJSON('/api/schedule/setup/reset'),
  generateSchedule: ({ shuffle } = {}) => postJSON('/api/schedule/generate', {
    shuffle: !!shuffle,
  }),
  applySchedule: () => postJSON('/api/schedule/apply'),

  playoffFormat: () => getJSON('/api/playoff/format'),
  savePlayoffFormat: (format) => putJSON('/api/playoff/format', { format }),
  resetPlayoffFormat: () => postJSON('/api/playoff/format/reset'),
  setPlayoffConfig: (body) => postJSON('/api/playoff/config', body),
  playoffPreview: (format, { year, week } = {}) => postJSON(
    `/api/playoff/preview${pointerQuery(year, week)}`,
    { format },
  ),
  playoffStadiums: () => getJSON('/api/playoff/stadiums'),
  playoffLive: () => getJSON('/api/playoff/live'),
  playoffApply: () => postJSON('/api/playoff/apply'),
  bowlGames: () => getJSON('/api/bowls'),
  applyBowlGames: ({ assignments, auto = false } = {}) => postJSON('/api/bowls/apply', {
    assignments,
    auto,
  }),

  polls: () => getJSON('/api/polls'),
  teamResume: (row) => getJSON(`/api/rankings/resume/${row}`),
  rankingsScoreboard: () => getJSON('/api/rankings/scoreboard'),
  savePollsConfig: (body) => putJSON('/api/polls/config', body),
  applyPolls: (force) => postJSON('/api/polls/apply', force ? { force: true } : {}),
  pollPreview: (algorithm, poll) => postJSON('/api/polls/preview', { algorithm, poll }),
};
