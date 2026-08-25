// Small formatting helpers shared across Dynasty+ Tools.

export function initials(name, max = 2) {
  return String(name || '')
    .split(/\s+/)
    .map((word) => word[0])
    .filter(Boolean)
    .slice(0, max)
    .join('')
    .toUpperCase();
}

export function logoUrl(espnId) {
  if (espnId == null || espnId === '') return null;
  return `https://a.espncdn.com/i/teamlogos/ncaa/500/${espnId}.png`;
}

export function hexColor(value, fallback = '#243044') {
  if (!value) return fallback;
  return `#${String(value).replace('#', '')}`;
}

export function luminance(hex) {
  const color = String(hex || '').replace('#', '');
  if (color.length < 6) return 1;
  const channel = (index) => {
    const value = parseInt(color.slice(index, index + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(0) + 0.7152 * channel(2) + 0.0722 * channel(4);
}

// Pick a team accent that remains visible against the dark app background.
export function readableAccent(primary, alt, fallback = '#e41c38') {
  const primaryColor = hexColor(primary, '');
  const alternateColor = hexColor(alt, '');
  if (primaryColor && luminance(primaryColor) >= 0.045) return primaryColor;
  if (alternateColor && luminance(alternateColor) >= 0.045) return alternateColor;
  return fallback;
}

export function clamp(value, low = 0, high = 100) {
  return Math.max(low, Math.min(high, value ?? 0));
}

export function formatMoney(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '$0';
  const sign = number < 0 ? '-' : '';
  const absolute = Math.abs(number);
  if (absolute >= 1_000_000) return `${sign}$${(absolute / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (absolute >= 1_000) return `${sign}$${Math.round(absolute / 1_000)}K`;
  return `${sign}$${absolute}`;
}

export function formatPoints(value) {
  return Number(value || 0).toLocaleString('en-US');
}
