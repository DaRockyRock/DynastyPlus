// Category accent colors shared by chips, articles, and the story slider.
// Mirrors backend/modules/base.CATEGORY_COLORS so server and client agree.
export const CATEGORY_COLORS = {
  'CFP watch': '#3b82f6',
  'Coaching carousel': '#f59e0b',
  Recruiting: '#22c55e',
  'Transfer portal': '#a855f7',
  'Heisman watch': '#eab308',
  Program: '#e41c38',
  National: '#64748b',
  Rivalry: '#ef4444',
  Injury: '#f97316',
};

export const DEFAULT_ACCENT = '#64748b';

export function accentFor(category) {
  return CATEGORY_COLORS[category] || DEFAULT_ACCENT;
}
