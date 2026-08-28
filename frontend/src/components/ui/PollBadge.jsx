import { useId } from 'react';

// The poll brand marks: a designed shield for the CFP committee ranking and
// the classic white-plate wire mark for the AP Top 25. These replace the
// generic trophy/gem glyphs everywhere a poll is named (the rankings hub
// switcher, the top-bar HUD chips, resume rank chips). Drawn in-house as SVG
// so they ship with the app; sized by `size` (height in px) and optionally
// rendered as a `lockup` with the poll's display name beside the mark.
const LABELS = {
  cfp: 'CFP Committee Rankings',
  ap: 'AP Top 25',
};

// The committee mark, after the real CFP lockup: a gold football formed by
// two facing crescents, white laces stacked in the seam, and blocky white
// CFP letters underneath, all on black.
function CfpMark({ size, uid }) {
  const w = size * (44 / 48);
  return (
    <svg width={w} height={size} viewBox="0 0 44 48" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${uid}-gold`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f0d27a" />
          <stop offset="0.5" stopColor="#d4a93f" />
          <stop offset="1" stopColor="#9a742a" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="42" height="46" rx="5" fill="#0b0b0c" stroke="rgba(255,255,255,.16)" />
      {/* the two gold crescents forming the football, open at the seam */}
      <path
        d="M19.6 4.5 C12.8 9.5 9.8 17 12.6 25.5 C13.7 28.7 15.8 31.3 19 33.2 C18 31.2 17.2 29 16.8 26.6 C15.5 19.2 16.6 11 19.6 4.5 Z"
        fill={`url(#${uid}-gold)`}
      />
      <path
        d="M24.4 4.5 C31.2 9.5 34.2 17 31.4 25.5 C30.3 28.7 28.2 31.3 25 33.2 C26 31.2 26.8 29 27.2 26.6 C28.5 19.2 27.4 11 24.4 4.5 Z"
        fill={`url(#${uid}-gold)`}
      />
      {/* inner accent lines echoing the crescents */}
      <path d="M20.4 8 C18.6 13.5 18.3 21 19.9 27.5" stroke={`url(#${uid}-gold)`} strokeWidth="0.9" fill="none" />
      <path d="M23.6 8 C25.4 13.5 25.7 21 24.1 27.5" stroke={`url(#${uid}-gold)`} strokeWidth="0.9" fill="none" />
      {/* the laces */}
      <rect x="19.1" y="10.6" width="5.8" height="2.1" rx="0.5" fill="#fff" />
      <rect x="19.1" y="14.3" width="5.8" height="2.1" rx="0.5" fill="#fff" />
      <rect x="19.1" y="18" width="5.8" height="2.1" rx="0.5" fill="#fff" />
      <rect x="19.1" y="21.7" width="5.8" height="2.1" rx="0.5" fill="#fff" />
      <text
        x="22" y="44" textAnchor="middle"
        style={{ fontFamily: 'var(--font-hero)', fontWeight: 900 }}
        fontSize="13" fill="#f4f6f6" letterSpacing="0.8"
      >
        CFP
      </text>
    </svg>
  );
}

function ApMark({ size }) {
  const w = size * (44 / 48);
  return (
    <svg width={w} height={size} viewBox="0 0 44 48" aria-hidden="true" focusable="false">
      <rect x="2" y="2" width="40" height="44" rx="5" fill="#f6f5f0" stroke="rgba(0,0,0,.35)" />
      <text
        x="22" y="27.5" textAnchor="middle"
        style={{ fontFamily: 'var(--font-hero)', fontWeight: 900 }}
        fontSize="21" fill="#141414" letterSpacing="0.5"
      >
        AP
      </text>
      <path d="M2 33h40v8a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5Z" fill="#d0021b" />
      <text
        x="22" y="42.5" textAnchor="middle"
        style={{ fontFamily: 'var(--font-display)', fontWeight: 700 }}
        fontSize="7.5" fill="#fff" letterSpacing="2.2"
      >
        TOP 25
      </text>
    </svg>
  );
}

export default function PollBadge({ poll = 'cfp', size = 28, lockup = false, label }) {
  const uid = useId();
  const mark = poll === 'ap' ? <ApMark size={size} /> : <CfpMark size={size} uid={uid} />;
  const text = label || LABELS[poll] || poll.toUpperCase();
  if (!lockup) {
    return <span className="poll-badge" title={text}>{mark}</span>;
  }
  return (
    <span className="poll-badge poll-badge-lockup" title={text}>
      {mark}
      <span className="poll-badge-label">{text}</span>
    </span>
  );
}
