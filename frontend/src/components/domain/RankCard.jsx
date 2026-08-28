import TeamLogo from '../ui/TeamLogo.jsx';
import { hexColor } from '../../lib/format.js';

// One team in the rankings hub's card grid: the comparison pin on the color
// rail, the rank in hero type, the real logo, school + nickname, and the
// season facts (record, conference). Clicking the card opens the team's
// resume; the pin adds the team to the side-by-side comparison. `entry` is
// one /api/polls poll entry.
export default function RankCard({ entry, isUser = false, compared = false, onOpen, onCompare }) {
  const nickname = entry.school && entry.team?.startsWith(entry.school)
    ? entry.team.slice(entry.school.length).trim()
    : '';
  const cls = [
    'rank-card',
    isUser ? 'is-user' : '',
    compared ? 'is-compared' : '',
    entry.rank <= 4 ? 'is-top4' : '',
  ].filter(Boolean).join(' ');
  return (
    <div className={cls} style={{ '--rc-team': hexColor(entry.color, 'var(--team)') }}>
      {onCompare && (
        <button
          type="button"
          className="rc-compare"
          title={compared ? 'Remove from comparison' : 'Add to comparison'}
          onClick={(e) => { e.stopPropagation(); onCompare(entry); }}
        >
          {compared ? '✓' : 'VS'}
        </button>
      )}
      <button type="button" className="rc-body" onClick={() => onOpen?.(entry)}>
        <span className="rc-rank">{entry.rank}</span>
        <TeamLogo espnId={entry.espn_id} logo={entry.logo} abbr={entry.abbr} name={entry.school} size={40} />
        <span className="rc-id">
          <span className="rc-school">{entry.school}</span>
          {nickname && <span className="rc-nick">{nickname}</span>}
        </span>
        <span className="rc-facts">
          <span className="rc-rec">{entry.record}</span>
          {entry.conference && <span className="rc-conf">{entry.conference}</span>}
        </span>
      </button>
      <span className="rc-open-hint">View resume</span>
    </div>
  );
}
