async function getJSON(url) {
  const response = await fetch(url);
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

function qs(year, week) {
  const parts = [];
  if (year != null) parts.push(`year=${year}`);
  if (week != null) parts.push(`week=${week}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export const api = {
  config: () => getJSON('/api/config'),
  teams: () => getJSON('/api/teams'),

  customization: () => getJSON('/api/customization'),
  saveCustomization: (section, value) => putJSON(`/api/customization/${section}`, { value }),
  resetCustomization: (section) => postJSON(`/api/customization/${section}/reset`),
  generatePerson: (section, seed) => postJSON(`/api/customization/${section}/generate-person`, { seed }),
  uploadImage: (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetch('/api/upload', { method: 'POST', body: form }).then(async (response) => {
      if (!response.ok) {
        let detail = '';
        try { detail = (await response.json()).error || ''; } catch { /* ignore */ }
        throw new Error(detail || `Upload failed: ${response.status}`);
      }
      return response.json();
    });
  },

  simState: (year) => getJSON(`/api/sim/state${year != null ? `?year=${year}` : ''}`),
  simFbsTeams: () => getJSON('/api/sim/fbs-teams'),
  simSetTeam: (name) => postJSON('/api/sim/set-team', { name }),
  simNew: ({ year, seed } = {}) => postJSON('/api/sim/new', { year, seed }),
  simScoreboard: ({ year, week } = {}) => getJSON(`/api/sim/scoreboard${qs(year, week)}`),
  simSimulateGame: ({ year, override } = {}) => postJSON('/api/sim/simulate-game', { year, override }),
  simAdvance: ({ year, override } = {}) => postJSON('/api/sim/advance', { year, override }),
  simReset: ({ year } = {}) => postJSON('/api/sim/reset', { year }),
  simDelete: () => postJSON('/api/sim/delete', {}),
  simRecruits: (year) => getJSON(`/api/sim/recruits${year != null ? `?year=${year}` : ''}`),

  budget: ({ year, week } = {}) => getJSON(`/api/budget${qs(year, week)}`),
  allocateBudget: (allocations, { year, week } = {}) =>
    postJSON(`/api/budget/allocate${qs(year, week)}`, { allocations }),
  nilOffer: ({ entity_id, kind, amount }, { year, week } = {}) =>
    postJSON(`/api/budget/nil-offer${qs(year, week)}`, { entity_id, kind, amount }),
  recruitingAction: ({ entity_id, action_key }, { year, week } = {}) =>
    postJSON(`/api/budget/recruiting-action${qs(year, week)}`, { entity_id, action_key }),
};
