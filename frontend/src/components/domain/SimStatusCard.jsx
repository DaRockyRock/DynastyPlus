import Card from '../ui/Card.jsx';

// At-a-glance readout of the active simulated season: year, week progress, the
// user's record, league size, and the season seed. `status` is /api/sim/state.
function Block({ k, v }) {
  return (
    <div className="ss-block">
      <span className="ss-k">{k}</span>
      <span className="ss-v">{v}</span>
    </div>
  );
}

export default function SimStatusCard({ status }) {
  const s = status || {};
  return (
    <Card className="simstatus-card">
      <Block k="Season" v={s.year} />
      <Block k="Week" v={`${s.week} / ${s.weeks_total}`} />
      <Block k={s.user_team || 'Your Team'} v={`${s.user_record || '0-0'} (${s.user_conf_record || '0-0'})`} />
      <Block k="Teams" v={s.teams_count} />
      <Block k="Seed" v={s.seed} />
    </Card>
  );
}
