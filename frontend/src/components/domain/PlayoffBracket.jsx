import TeamLogo from '../ui/TeamLogo.jsx';

export function SeedRow({ seed, bye = false }) {
  return (
    <div className={`seed-row${bye ? ' bye' : ''}`}>
      <span className="seed-num">{seed.seed}</span>
      <TeamLogo espnId={seed.espn_id} abbr={seed.abbr} name={seed.team} size={24} />
      <span style={{ fontWeight: 700, fontSize: 13.5, flex: 1 }}>{seed.team}</span>
      <span className="rank-rec">{seed.record || ''}</span>
    </div>
  );
}

function MatchupLine({ seed }) {
  return (
    <div className="m-line">
      <span className="seed-num">{seed.seed}</span>
      <TeamLogo espnId={seed.espn_id} abbr={seed.abbr} name={seed.team} size={22} />
      <span style={{ fontWeight: 700, fontSize: 13, flex: 1 }}>{seed.team}</span>
    </div>
  );
}

export function MatchupCard({ matchup }) {
  return (
    <div className="matchup">
      <MatchupLine seed={matchup.home} />
      <div style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-3)', fontWeight: 800 }}>vs</div>
      <MatchupLine seed={matchup.away} />
    </div>
  );
}

// 12-team playoff bracket: top-4 byes plus 5-12 first-round matchups.
export default function PlayoffBracket({ bracket }) {
  if (!bracket) return null;
  return (
    <div className="bracket">
      <div>
        <div className="rank-abbr" style={{ marginBottom: 8 }}>FIRST-ROUND BYES (TOP 4)</div>
        {(bracket.byes || []).map((s) => <SeedRow key={s.seed} seed={s} bye />)}
      </div>
      <div>
        <div className="rank-abbr" style={{ marginBottom: 8 }}>FIRST ROUND (5-12)</div>
        {(bracket.first_round || []).map((m, i) => <MatchupCard key={i} matchup={m} />)}
      </div>
    </div>
  );
}
