import TeamLogo from '../ui/TeamLogo.jsx';
import { hexColor } from '../../lib/format.js';

// One playoff matchup in the broadcast-bracket style: two stacked team tiles
// (gold seed block on the left, the team's mark on a team-color field) with the
// game's site under the pair, exactly like the TV bracket graphics: the host
// school's city/state for campus games, the bowl name (with its logo) for bowl
// tie-ins, the venue and city for the championship.
//
// Slots come straight from the backend bracket JSON: {type:'team', seed, team,
// abbr, espn_id, color} for a decided participant, {type:'winner', label} for a
// slot still waiting on an earlier game (rendered as a crossed empty tile, so
// nothing advances until it is actually played).

function TeamTile({ slot, userTeamId, winner, score }) {
  const isTeam = slot.type === 'team';
  const decided = !!winner;
  const cls = [
    'pb-tile',
    isTeam ? '' : 'tbd',
    isTeam && userTeamId != null && slot.espn_id === userTeamId ? 'is-user' : '',
    decided && isTeam ? (slot.team === winner ? 'won' : 'lost') : '',
  ].filter(Boolean).join(' ');

  if (!isTeam) {
    return (
      <div className={cls} title={slot.label || 'To be decided'}>
        <span className="pb-tile-seed" />
        <span className="pb-tile-mark"><span className="pb-tile-tbd">{slot.label || 'TBD'}</span></span>
      </div>
    );
  }
  return (
    <div className={cls} style={{ '--tile': hexColor(slot.color, '#232a2e') }}
         title={`${slot.seed} ${slot.team}${slot.record ? ` (${slot.record})` : ''}`}>
      <span className="pb-tile-seed">{slot.seed}</span>
      <span className="pb-tile-mark">
        <TeamLogo espnId={slot.espn_id} abbr={slot.abbr} name={slot.team} size={30} plate={false} />
        <span className="pb-tile-name">{slot.short || slot.team}</span>
        {slot.record && <span className="pb-tile-rec">{slot.record}</span>}
        {score != null && <span className="pb-tile-score">{score}</span>}
      </span>
    </div>
  );
}

function SiteLabel({ site }) {
  if (!site) return null;
  // A bowl (including a bowl-hosted championship): logo + bowl name.
  if (site.bowl) {
    return (
      <div className="pb-game-label">
        <img className="pb-game-label-logo" src={`/game-assets/bowls/${site.bowl.asset}.png`} alt=""
             onError={(e) => { e.currentTarget.style.display = 'none'; }} />
        <span>{site.bowl.name}</span>
      </div>
    );
  }
  if (site.type === 'campus') {
    return <div className="pb-game-label"><span>{site.city}</span></div>;
  }
  // neutral or a neutral-site championship: venue with the city underneath
  return (
    <div className="pb-game-label stacked">
      <span>{site.venue}</span>
      {site.city && <span className="pb-game-label-sub">{site.city}</span>}
    </div>
  );
}

export default function BracketGame({ game, userTeamId, final = false }) {
  const scores = Array.isArray(game.scores) ? game.scores : [null, null];
  return (
    <div className={`pb-game${final ? ' is-final' : ''}`}>
      <div className="pb-tiles">
        {game.slots.map((slot, i) => (
          <TeamTile key={i} slot={slot} userTeamId={userTeamId} winner={game.winner} score={scores[i]} />
        ))}
      </div>
      <SiteLabel site={game.site} />
    </div>
  );
}
