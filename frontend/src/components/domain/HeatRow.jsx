import TeamLogo from '../ui/TeamLogo.jsx';
import Avatar from '../ui/Avatar.jsx';
import HeatBar from '../ui/HeatBar.jsx';
import PersonName from '../people/PersonName.jsx';
import { noEmDash } from '../../lib/format.js';

// One coach on the hot-seat index. Shows the coach photo when set, otherwise
// the team mark.
export default function HeatRow({ coach }) {
  const c = coach;
  return (
    <div className={`heat-row${c.is_user ? ' is-user' : ''}`}>
      {c.image
        ? <Avatar src={c.image} name={c.coach} size={30} />
        : <TeamLogo espnId={c.espn_id} abbr={c.abbr} name={c.team} size={30} />}
      <div className="heat-info">
        <div className="h-coach">
          {c.is_user ? c.coach : <PersonName name={c.coach} kind="opp_coach" team={c.team} />}
          {c.is_user && <span style={{ color: 'var(--team)', fontSize: 11 }}> (you)</span>}
        </div>
        <div className="h-team">{c.team} - {c.record || ''}</div>
        <div className="h-note">{noEmDash(c.note || '')}</div>
      </div>
      <HeatBar value={c.heat} />
    </div>
  );
}
