import { classYearLabel, depthRoleLabel } from '../../lib/format.js';

// The identity line under a contact's name in a conversation header, so the coach
// always knows who he is texting. A roster player reads their class year and depth
// chart role from the chat marker (e.g. "So · #1 RB"); everyone else (a recruit,
// reporter, personality, staffer, opposing coach) shows their plain role from the
// contact ("5-star WR target", "Beat writer", "Head Coach, Florida"). Falls back
// to the contact role whenever the richer player line is unavailable.
export default function ConvoPeerMeta({ contact, marker }) {
  let label = '';
  if (marker && marker.kind === 'player') {
    label = [
      classYearLabel(marker.year),
      depthRoleLabel(marker.depth_chart_slot, marker.position),
    ].filter(Boolean).join(' · ');
  }
  if (!label) label = (contact && contact.role) || '';
  if (!label) return null;
  return <div className="cp-meta">{label}</div>;
}
