// API client for the Flask backends. Two apps share this client: the Dynasty+
// companion (served by its Flask on /api) and the Simulator (its own Flask).
// In production each app is served by its own backend so a relative /api works;
// in dev the Simulator entry sets window.__API_BASE__ = '/sim-api' and Vite
// proxies that to the Simulator's port (see vite.config.js).
//
// Read the base LAZILY on every call: the entry sets window.__API_BASE__ after
// its (hoisted) imports run, so capturing it once at module load would miss it
// and send the Simulator's calls to the wrong backend.
const u = (path) => ((typeof window !== 'undefined' && window.__API_BASE__) || '') + path;

async function getJSON(url) {
  const res = await fetch(u(url));
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).error || ''; } catch { /* ignore */ }
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function sendJSON(method, url, body) {
  const res = await fetch(u(url), {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).error || ''; } catch { /* ignore */ }
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

const postJSON = (url, body) => sendJSON('POST', url, body);
const putJSON = (url, body) => sendJSON('PUT', url, body);

function qs(year, week, regenerate) {
  const parts = [];
  if (year != null) parts.push(`year=${year}`);
  if (week != null) parts.push(`week=${week}`);
  if (regenerate) parts.push('regenerate=1');
  return parts.length ? `?${parts.join('&')}` : '';
}

export const api = {
  config: () => getJSON('/api/config'),

  // LLM connection (the setup wizard). The key is never returned by the backend.
  llm: () => getJSON('/api/llm'),
  saveLLM: (body) => putJSON('/api/llm', body),
  testLLM: (body) => postJSON('/api/llm/test', body),

  teams: () => getJSON('/api/teams'),
  state: () => getJSON('/api/state'),

  // Dynasty library + the explicit Scan handoff (companion side).
  dynasties: () => getJSON('/api/dynasties'),
  scan: () => postJSON('/api/scan'),
  selectDynasty: (id) => postJSON('/api/dynasty/select', { id }),
  status: () => getJSON('/api/status'),
  dynasty: (year, week) => getJSON(`/api/dynasty${qs(year, week)}`),
  module: (key, { year, week, regenerate } = {}) =>
    getJSON(`/api/module/${key}${qs(year, week, regenerate)}`),
  generate: ({ year, week, regenerate } = {}) => postJSON(`/api/generate${qs(year, week)}`, { regenerate: !!regenerate }),
  advance: (body) => postJSON('/api/advance', body),
  article: (article, { year, week } = {}) => postJSON('/api/article', { article, year, week }),
  phoneMessage: (contactId, message, action) =>
    postJSON('/api/phone/message', { contact_id: contactId, message, action }),
  phoneThreads: ({ year, week } = {}) => getJSON(`/api/phone/threads${qs(year, week)}`),
  // Resolve any hovered person (name + optional kind hint) into a textable contact.
  phoneOpen: ({ name, kind, role, team } = {}) =>
    postJSON('/api/phone/open', { name, kind, role, team }),
  // Mark a conversation read once the coach opens it (clears unread inbound texts).
  phoneRead: (contactId) => postJSON('/api/phone/read', { contact_id: contactId }),
  // Persist the latest reply as unread (it arrived while the coach was elsewhere).
  phoneMarkUnread: (contactId) => postJSON('/api/phone/unread', { contact_id: contactId }),

  // Social feed. The timeline itself rides the generic module endpoint
  // (api.module('feed', ...)); these own only the coach's like + seen state.
  feedState: ({ year, week } = {}) => getJSON(`/api/feed/state${qs(year, week)}`),
  feedLike: (postId) => postJSON('/api/feed/like', { post_id: postId }),
  feedSeen: (week) => postJSON('/api/feed/seen', { week }),

  // Post-game press conference (the interactive interview after the user's game).
  interviewPending: ({ year, week } = {}) => getJSON(`/api/interview/pending${qs(year, week)}`),
  interviewStart: ({ year, week } = {}) => postJSON(`/api/interview/start${qs(year, week)}`, {}),
  interviewAnswer: (gameKey, answer, { year, week } = {}) =>
    postJSON(`/api/interview/answer${qs(year, week)}`, { game_key: gameKey, answer }),
  interviewSkip: (gameKey, { year, week } = {}) =>
    postJSON(`/api/interview/skip${qs(year, week)}`, { game_key: gameKey }),
  interviewState: (gameKey, { year, week } = {}) =>
    getJSON(`/api/interview/state${qs(year, week)}&game_key=${encodeURIComponent(gameKey)}`),

  // Customization (the Customize flow)
  customization: () => getJSON('/api/customization'),
  saveCustomization: (section, value) => putJSON(`/api/customization/${section}`, { value }),
  resetCustomization: (section) => postJSON(`/api/customization/${section}/reset`),
  resetAllCustomization: () => postJSON('/api/customization/reset'),
  generatePerson: (section, seed) => postJSON(`/api/customization/${section}/generate-person`, { seed }),
  uploadImage: (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(u('/api/upload'), { method: 'POST', body: form }).then(async (res) => {
      if (!res.ok) {
        let detail = '';
        try { detail = (await res.json()).error || ''; } catch { /* ignore */ }
        throw new Error(detail || `Upload failed: ${res.status}`);
      }
      return res.json();
    });
  },

  // Simulation / Debug mode
  simState: (year) => getJSON(`/api/sim/state${year != null ? `?year=${year}` : ''}`),
  // FBS team picker: list the universe + the user's current program; set it.
  simFbsTeams: () => getJSON('/api/sim/fbs-teams'),
  simSetTeam: (name) => postJSON('/api/sim/set-team', { name }),
  simNew: ({ year, seed } = {}) => postJSON('/api/sim/new', { year, seed }),
  simScoreboard: ({ year, week } = {}) => getJSON(`/api/sim/scoreboard${qs(year, week)}`),
  // Play the current week's games but stay on the week (for the post-game presser).
  simSimulateGame: ({ year, override } = {}) => postJSON('/api/sim/simulate-game', { year, override }),
  simAdvance: ({ year, override } = {}) => postJSON('/api/sim/advance', { year, override }),
  simReset: ({ year } = {}) => postJSON('/api/sim/reset', { year }),
  // Full clean slate: wipe every season, all generated content, and customization.
  simDelete: () => postJSON('/api/sim/delete', {}),
  simRecruits: (year) => getJSON(`/api/sim/recruits${year != null ? `?year=${year}` : ''}`),

  // NIL / Dynasty Points budget. The Simulator owns the store (these mutate it);
  // Dynasty+ exposes only the read (GET /api/budget) and queues writes to the inbox.
  budget: ({ year, week } = {}) => getJSON(`/api/budget${qs(year, week)}`),
  allocateBudget: (allocations, { year, week } = {}) =>
    postJSON(`/api/budget/allocate${qs(year, week)}`, { allocations }),
  nilOffer: ({ entity_id, kind, amount }, { year, week } = {}) =>
    postJSON(`/api/budget/nil-offer${qs(year, week)}`, { entity_id, kind, amount }),
  recruitingAction: ({ entity_id, action_key }, { year, week } = {}) =>
    postJSON(`/api/budget/recruiting-action${qs(year, week)}`, { entity_id, action_key }),

  // Companion inbox: the write-back channel. Dynasty+ queues coach actions here;
  // the Simulator drains + applies them. `applyInbox` is the Simulator-side drain.
  inbox: ({ year } = {}) => getJSON(`/api/inbox${year != null ? `?year=${year}` : ''}`),
  queueNilOffer: ({ entity_id, kind, amount }, { year, week } = {}) =>
    postJSON(`/api/inbox/nil-offer${qs(year, week)}`, { entity_id, kind, amount }),
  queueRecruitingAction: ({ entity_id, action_key }, { year, week } = {}) =>
    postJSON(`/api/inbox/recruiting-action${qs(year, week)}`, { entity_id, action_key }),
  queueAllocate: (allocations, { year, week } = {}) =>
    postJSON(`/api/inbox/allocate${qs(year, week)}`, { allocations }),
  applyInbox: ({ year } = {}) => postJSON('/api/inbox/apply', { year }),
};
