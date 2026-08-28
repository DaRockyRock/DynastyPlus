import Scoreboard from './Scoreboard.jsx';
import EmptyState from '../ui/EmptyState.jsx';

// The league-wide scoreboard for the rankings hub: the current week's slate
// (the engine's own queue; finals once the week is advanced, matchups before
// that) and the latest official finals. `data` is /api/rankings/scoreboard.
const side = (s, userTeam) => ({
  name: s.school,
  abbr: s.abbr,
  espn_id: s.espn_id,
  rank: s.cfp_rank,
  is_user: !!userTeam && s.team === userTeam,
});

const toRow = (e, userTeam) => ({
  status: e.status,
  user: e.user,
  neutral: e.neutral,
  label: e.label,
  away: side(e.away, userTeam),
  home: side(e.home, userTeam),
  away_score: e.away_score,
  home_score: e.home_score,
  winner: e.status === 'final'
    ? (e.home_score > e.away_score ? e.home.school : e.away.school)
    : null,
});

export default function WeekScoreboardPanel({ data, userTeam }) {
  if (!data?.available) {
    return <EmptyState>{data?.reason || 'No CFB 27 save is readable for this dynasty.'}</EmptyState>;
  }
  const slate = (data.slate || []).map((e) => toRow(e, userTeam));
  const recent = (data.recent || []).map((e) => toRow(e, userTeam));
  return (
    <div className="week-scoreboard">
      <Scoreboard title="This Week" games={slate} />
      {recent.length > 0 && <Scoreboard title="Latest Finals" games={recent} />}
    </div>
  );
}
