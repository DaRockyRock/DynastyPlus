import { formatMoney } from '../../lib/format';

function Stars({ count, max = 5 }) {
  const n = Math.max(0, Math.min(max, count || 0));
  return (
    <span className="cs-stars" aria-label={`${n} stars`}>
      {'★'.repeat(n)}{'☆'.repeat(max - n)}
    </span>
  );
}

// Category-specific identity info displayed below the contact's name.
export default function ContactSubtitle({ contact }) {
  const { category, contact_meta: meta, role, entity } = contact;

  if (category === 'Recruits' && meta) {
    const { position, stars, national_rank, expected_nil, our_board_rank } = meta;
    const boardLabel = our_board_rank != null ? `#${our_board_rank} on list` : null;
    const nilStr = expected_nil ? `${formatMoney(expected_nil)} NIL` : null;

    return (
      <div className="c-subtitle">
        <div className="cs-row">
          {position && <span className="cs-tag">{position}</span>}
          {national_rank != null && <span className="cs-sep">·</span>}
          {national_rank != null && <span className="cs-dim">#{national_rank} Natl</span>}
          {stars > 0 && <span className="cs-sep">·</span>}
          {stars > 0 && <Stars count={stars} />}
        </div>
        <div className="cs-row">
          {boardLabel && <span className="cs-board">{boardLabel}</span>}
          {boardLabel && nilStr && <span className="cs-sep">·</span>}
          {nilStr && <span className="cs-nil">{nilStr}</span>}
        </div>
      </div>
    );
  }

  if (category === 'Players' && meta) {
    const { depth_chart_slot, position, current_nil } = meta;
    const slot = depth_chart_slot || position || '';
    const nilStr = current_nil ? `${formatMoney(current_nil)}/yr` : null;

    return (
      <div className="c-subtitle">
        <div className="cs-row">
          {slot && <span className="cs-dim">{slot}</span>}
          {slot && nilStr && <span className="cs-sep">·</span>}
          {nilStr && <span className="cs-nil">{nilStr}</span>}
        </div>
      </div>
    );
  }

  if (category === 'Staff') {
    const isAD = entity?.kind === 'budget';
    const label = isAD && meta?.school
      ? `${meta.school} Athletic Director`
      : role || '';
    return label ? (
      <div className="c-subtitle">
        <span className="cs-dim">{label}</span>
      </div>
    ) : null;
  }

  if (category === 'Media') {
    const scope = contact.media_scope || 'National';
    const type = contact.media_type || 'writer';
    const outlet = contact.outlet || '';
    const label = outlet ? `${scope} ${type} for ${outlet}` : `${scope} ${type}`;
    return (
      <div className="c-subtitle">
        <span className="cs-dim">{label}</span>
      </div>
    );
  }

  // Every other contact (an opposing coach, a carousel candidate, a recruit
  // whose board meta has not loaded) still names who they are from their role.
  if (role) {
    return (
      <div className="c-subtitle">
        <span className="cs-dim">{role}</span>
      </div>
    );
  }

  return null;
}
