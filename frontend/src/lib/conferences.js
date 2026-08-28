// Conference logo helpers. Mirrors backend/conferences.py so components can
// render an affiliation logo from a conference name or ESPN group id without an
// async dependency. The authoritative list is also served at /api/conferences.
//
// On top of the static maps sits a runtime registry (registerConferences) fed
// by the Conference Setup editor, so renamed conferences and brand-new custom
// (companion-only) conferences still resolve an id and a logo everywhere.

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

// Runtime registry: id / name / abbr (lowercased) -> { id, logo, abbr }.
// Populated by registerConferences when the Conference Setup state loads.
const RUNTIME = new Map();

// A companion logo OVERRIDE: a user upload or one of the game's own classic
// (historic) marks the user chose. Only these replace a stock conference mark;
// a stock conference whose `logo` is just its game asset is not an override
// (so its white-knockout variant is preserved).
function isCustomLogo(url) {
  return typeof url === 'string'
    && (url.startsWith('/uploads/') || url.startsWith('/game-assets/conferences/historic/'));
}

// Register the editor's conference list so custom and renamed conferences
// resolve logos and ids through the fallbacks below. Entries carry the stable
// editor id, the display logo (game asset or an override), the abbr, and
// whether the logo is a companion override. Also keyed by the stock ESPN group
// id (resolved from the name) so an override resolves when a component asks by
// id, e.g. <ConferenceLogo id={4} />.
export function registerConferences(list) {
  (list || []).forEach((c) => {
    if (!c) return;
    const entry = {
      id: c.id ?? null, logo: c.logo || null, abbr: c.abbr || '',
      override: isCustomLogo(c.logo),
    };
    const keys = [c.id, c.name, c.abbr];
    const espnId = c.name ? CONFERENCES[ALIASES[c.name] || c.name] : null;
    if (espnId != null) keys.push(espnId);
    keys.forEach((key) => {
      if (key != null && key !== '') RUNTIME.set(String(key).toLowerCase(), entry);
    });
  });
}

function runtimeEntry(key) {
  if (key == null || key === '') return null;
  return RUNTIME.get(String(key).toLowerCase()) || null;
}

export function confId(nameOrId) {
  if (typeof nameOrId === 'number') return nameOrId;
  if (!nameOrId) return null;
  const key = ALIASES[nameOrId] || nameOrId;
  if (CONFERENCES[key] != null) return CONFERENCES[key];
  // Runtime-registered (custom or renamed) conference: resolve to its stable
  // editor id so confLogoUrl can serve its registered logo.
  const entry = runtimeEntry(nameOrId);
  return entry ? (entry.id ?? nameOrId) : null;
}

// ESPN group id -> extracted CFB 27 conference mark slug (frontend/public/game-assets).
const CONF_ASSET_SLUGS = {
  8: 'sec',
  5: 'bigten',
  4: 'big12',
  1: 'acc',
  9: 'pac12',
  17: 'mwc',
  151: 'american',
  12: 'cusa',
  15: 'mac',
  37: 'sunbelt',
  18: 'fbs',
};

export function confLogoUrl(id, variant = '') {
  const entry = runtimeEntry(id);
  // A companion override (uploaded or classic mark) replaces the stock mark
  // everywhere. It has no white knockout variant, so the same file serves both.
  if (entry && entry.override && entry.logo) return entry.logo;
  const slug = CONF_ASSET_SLUGS[id];
  if (slug) return `/game-assets/conferences/${slug}${variant === 'white' ? '-white' : ''}.png`;
  // Runtime-registered conference with no stock mark (custom or renamed).
  return entry ? entry.logo : null;
}
