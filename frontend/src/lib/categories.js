// Accent colors for labels used by the Tools editors.
export const CATEGORY_COLORS = {
  'CFP watch': '#3b82f6',
  Recruiting: '#22c55e',
  Schedule: '#f59e0b',
  Playoff: '#eec84f',
  Rankings: '#64748b',
};

export const DEFAULT_ACCENT = '#64748b';

export function accentFor(category) {
  return CATEGORY_COLORS[category] || DEFAULT_ACCENT;
}
