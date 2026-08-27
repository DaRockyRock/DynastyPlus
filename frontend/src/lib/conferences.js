// Conference logo helpers. Mirrors backend/conferences.py so components can
// render an affiliation logo from a conference name or ESPN group id without an
// async dependency. The authoritative list is also served at /api/conferences.

export const CONFERENCES = {
  SEC: 8,
  'Big Ten': 5,
  'Big 12': 4,
  ACC: 1,
  'Pac-12': 9,
  'Mountain West': 17,
  American: 151,
  'Conference USA': 12,
  MAC: 15,
  'Sun Belt': 37,
  'FBS Independents': 18,
};

const ALIASES = {
  AAC: 'American',
  'American Athletic': 'American',
  'C-USA': 'Conference USA',
  CUSA: 'Conference USA',
  'Mid-American': 'MAC',
  Independent: 'FBS Independents',
  Independents: 'FBS Independents',
  'Pac 12': 'Pac-12',
  B1G: 'Big Ten',
};

export function confId(nameOrId) {
  if (typeof nameOrId === 'number') return nameOrId;
  if (!nameOrId) return null;
  const key = ALIASES[nameOrId] || nameOrId;
  return CONFERENCES[key] ?? null;
}

export function confLogoUrl(id) {
  return id ? `https://a.espncdn.com/i/teamlogos/ncaa_conf/500/${id}.png` : null;
}
