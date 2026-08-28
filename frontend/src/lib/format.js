// Formatting helpers shared by the Dynasty+ Tools editors.

export function logoUrl(espnId) {
  return teamAsset(espnId, 'logo');
}

export function teamAsset(espnId, kind = 'logo') {
  if (espnId == null || espnId === '') return null;
  const ext = kind === 'hub-bg' ? 'jpg' : 'png';
  return `/game-assets/teams/${espnId}/${kind}.${ext}`;
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

export function readableAccent(primary, alt, fallback = '#e41c38') {
  const first = hexColor(primary, fallback);
  if (luminance(first) >= 0.12) return first;
  const second = hexColor(alt, fallback);
  return luminance(second) >= 0.12 ? second : fallback;
}

export function clamp(value, low = 0, high = 100) {
  return Math.max(low, Math.min(high, Number(value) || 0));
}
