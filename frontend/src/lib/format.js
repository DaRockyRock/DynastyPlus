// Small formatting helpers shared across the component library.

// Project rule: no dashes used as punctuation. Em/en dashes and spaced hyphens
// become commas; hyphens inside words and scores (top-15, 28-24) are kept.
// Normalizes defensively on the client too (mirrors backend modules.base.sanitize).
export function noEmDash(s) {
  return String(s ?? '')
    .replace(/\s*[—–]+\s*/g, ', ')   // em / en dashes
    .replace(/\s+--+\s*/g, ', ')     // word -- word
    .replace(/ +-+ +/g, ', ')        // word - word
    .replace(/\s+-+\s*$/g, '')       // trailing " -"
    .replace(/([.!?;:])[ \t]*,/g, '$1')
    .replace(/,[ \t]*,+/g, ',')
    .replace(/^[ \t]*,[ \t]*/, '')
    .replace(/[ \t]+([,.!?;:])/g, '$1');
}

// Lowercase, drop punctuation, collapse whitespace. Used to compare a pull
// quote against body sentences without dashes/commas/case getting in the way.
function normalizeForMatch(s) {
  return String(s ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// True when a body sentence is effectively the same line as the pull quote
// (exact match, or one substantially contains the other). The length floor
// keeps short fragments from matching by coincidence.
function quoteEchoesSentence(qNorm, sNorm) {
  if (!qNorm || !sNorm) return false;
  if (qNorm === sNorm) return true;
  const [shortS, longS] = qNorm.length <= sNorm.length ? [qNorm, sNorm] : [sNorm, qNorm];
  if (shortS.length < 24) return false;
  return longS.includes(shortS) && shortS.length >= longS.length * 0.6;
}

// Pull quotes are lifted verbatim from the body, so the same sentence would
// otherwise render twice: once as the bold callout and once in a paragraph
// right beside it. Strip the echoed sentence from the body so the quote reads
// as a true callout, not a repeat. Operates at sentence granularity and drops
// any paragraph left empty.
export function stripQuoteFromSections(sections, quote) {
  const list = Array.isArray(sections) ? sections : [];
  const qNorm = normalizeForMatch(quote);
  if (!qNorm || qNorm.length < 16) return list;
  const out = [];
  for (const section of list) {
    const sentences = String(section ?? '').split(/(?<=[.!?])\s+/);
    const kept = sentences.filter((s) => s.trim() && !quoteEchoesSentence(qNorm, normalizeForMatch(s)));
    const joined = kept.join(' ').trim();
    if (joined) out.push(joined);
  }
  return out;
}

export function initials(name, max = 2) {
  return String(name || '')
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, max)
    .join('')
    .toUpperCase();
}

// ESPN logo CDN. The single source of truth for team marks.
export function logoUrl(espnId) {
  if (espnId == null || espnId === '') return null;
  return `https://a.espncdn.com/i/teamlogos/ncaa/500/${espnId}.png`;
}

export function hexColor(value, fallback = '#243044') {
  if (!value) return fallback;
  const c = String(value).replace('#', '');
  return `#${c}`;
}

// Relative luminance (0..1, WCAG) of a #rrggbb color. Returns 1 (treat as light)
// for anything we cannot parse, so an unknown color is never mistaken for black.
export function luminance(hex) {
  const c = String(hex || '').replace('#', '');
  if (c.length < 6) return 1;
  const ch = (i) => {
    const v = parseInt(c.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * ch(0) + 0.7152 * ch(2) + 0.0722 * ch(4);
}

// A team accent that is actually visible on the app's dark field. The UI paints a
// lot of elements with the team's primary color, but some teams (e.g. UCF) are
// black or near-black, which disappears against the background. In that case fall
// back to the secondary color, then to a neutral accent if that is dark too.
const NEAR_BLACK = 0.045; // luminance below this reads as black on the dark field
export function readableAccent(primary, alt, fallback = '#e41c38') {
  const p = hexColor(primary, '');
  const a = hexColor(alt, '');
  if (p && luminance(p) >= NEAR_BLACK) return p;
  if (a && luminance(a) >= NEAR_BLACK) return a;
  return fallback;
}

export function clamp(n, lo = 0, hi = 100) {
  return Math.max(lo, Math.min(hi, n ?? 0));
}

// Class year code (FR/SO/JR/SR/GR) -> display label (Fr/So/Jr/Sr/Gr). Returns ''
// for an unknown/empty value so the caller can omit it.
export function classYearLabel(year) {
  const code = String(year ?? '').trim().toUpperCase();
  if (!code) return '';
  const map = { FR: 'Fr', SO: 'So', JR: 'Jr', SR: 'Sr', GR: 'Gr' };
  return map[code] || (code.charAt(0) + code.slice(1).toLowerCase());
}

// Depth chart slot + position -> compact role tag like "#1 RB". The slot is free
// text ("Starting Running Back", "Backup Running Back"), so read its rank word and
// pair it with the position abbreviation. Falls back to the raw slot, then the
// bare position, when no rank can be read.
export function depthRoleLabel(slot, position) {
  const pos = String(position ?? '').trim().toUpperCase();
  const s = String(slot ?? '').trim().toLowerCase();
  let rank = null;
  if (/\b(start|starting|starter|first|1st)\b/.test(s) || /^1\b/.test(s)) rank = 1;
  else if (/\b(backup|second|2nd)\b/.test(s) || /^2\b/.test(s)) rank = 2;
  else if (/\b(third|3rd)\b/.test(s) || /^3\b/.test(s)) rank = 3;
  if (rank && pos) return `#${rank} ${pos}`;
  return String(slot ?? '').trim() || pos || '';
}

// NIL dollars -> compact label: $9.5M, $250K, $0. Negative-safe.
export function formatMoney(n) {
  const v = Number(n);
  if (!Number.isFinite(v)) return '$0';
  const sign = v < 0 ? '-' : '';
  const a = Math.abs(v);
  if (a >= 1_000_000) return `${sign}$${(a / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (a >= 1_000) return `${sign}$${Math.round(a / 1_000)}K`;
  return `${sign}$${a}`;
}

// Dynasty Points -> comma-grouped string (no unit). e.g. 12000 -> "12,000".
export function formatPoints(n) {
  return Number(n || 0).toLocaleString('en-US');
}

// Engagement counts -> compact social-style label: 1.2K, 14K, 2.3M. e.g. like
// and repost counts on a feed post. Returns '' for zero so the count can hide.
export function compactCount(n) {
  const v = Number(n || 0);
  if (v <= 0) return '';
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
  return String(v);
}

// The outgoing text the coach auto-sends to a recruit/player when an NIL offer
// is made or changed. Coach voice, no dashes, no emojis.
export function offerText(amount, prevAmount = 0, kind = 'recruit') {
  const m = formatMoney(amount);
  if (kind === 'player') {
    if (amount === 0) return 'Going to have to pause your NIL for now. Let us talk it through.';
    if (amount > prevAmount) return `Bumping your NIL up to ${m}/yr. You earned it, let us keep this rolling.`;
    if (amount < prevAmount) return `Need to adjust your NIL to ${m}/yr for now. Want to talk it through with you.`;
    return `Keeping your NIL locked in at ${m}/yr. Glad to have you.`;
  }
  if (amount === 0) return 'Going to have to pull the NIL offer for now. Let us stay in touch.';
  if (prevAmount === 0) return `Want to get this done. Putting ${m}/yr in NIL on the table for you.`;
  if (amount > prevAmount) return `Stepping up for you. Bumping the NIL offer to ${m}/yr and ready to make it happen.`;
  if (amount < prevAmount) return `Adjusting your NIL offer to ${m}/yr for now. Still want you here.`;
  return `Reaffirming your NIL offer at ${m}/yr. The door is wide open.`;
}
