import StarRating from '../ui/StarRating.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';
import PersonName from '../people/PersonName.jsx';

// One prospect line in the national recruit board. Grid columns align with the
// RecruitBoard header. `recruit` is a /api/sim/recruits row.
function nil(n) {
  if (!n) return '—';
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1).replace('.0', '')}M`;
  if (n >= 1_000) return `$${Math.round(n / 1_000)}K`;
  return `$${n}`;
}

export default function RecruitRow({ recruit: r, onSelect }) {
  const committed = !!r.committed_to;
  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div className="rb-row" role={onSelect ? 'button' : undefined} tabIndex={onSelect ? 0 : undefined} onClick={onSelect ? () => onSelect(r) : undefined}>
      <span className="rb-rank">{r.national_rank}</span>
      <div className="rb-player">
        <PersonName name={r.name} kind="recruit"><span className="rb-name">{r.name}</span></PersonName>
        <span className="rb-sub">{r.position}{r.position_rank ? ` ${r.position_rank}` : ''} · {r.hometown}</span>
      </div>
      <span className="rb-stars"><StarRating value={r.stars} /></span>
      <span className="rb-ovr">{r.ovr}</span>
      <span className="rb-nil">{nil(r.expected_nil)}</span>
      <span className={`rb-status ${committed ? 'is-committed' : 'is-open'}`}>
        {committed ? (
          <>
            <TeamLogo espnId={r.committed_espn_id} abbr={r.committed_abbr} name={r.committed_to} size={20} plate={false} />
            <span className="rb-commit-abbr">{r.committed_abbr || r.committed_to}</span>
            {r.status === 'Signed' && <span className="rb-signed">Signed</span>}
          </>
        ) : (
          <span className="rb-open-label">Open{r.leader_abbr ? ` · ${r.leader_abbr}` : ''}</span>
        )}
      </span>
    </div>
  );
}
