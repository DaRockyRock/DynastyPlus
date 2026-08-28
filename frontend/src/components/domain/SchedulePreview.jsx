import { useState } from 'react';
import PanelCard from '../ui/PanelCard.jsx';
import TeamLogo from '../ui/TeamLogo.jsx';

// Week-by-week preview of a generated season (the plan /api/schedule/generate
// returns). One week renders at a time, picked from a tab rail of week
// numbers (a gold dot marks the user's game weeks, a lock glyph the weeks
// the engine already owns). The user's games are highlighted, protected
// games are tagged, and changed matchups are flagged against the save's
// current schedule.
const TAG_LABEL = {
  rivalry: 'Protected',
  rival: 'Rival',
  division: 'Division',
  fcs: 'FCS',
  locked: 'Locked',
};

function GameRow({ game }) {
  return (
    <div className={`sr-prev-game${game.user ? ' user' : ''}`}>
      <span className="sr-prev-side">
        <TeamLogo espnId={game.away.espn_id} abbr={game.away.abbr} name={game.away.school} size={20} />
        {game.away.school}
      </span>
      <span className="sr-prev-at">AT</span>
      <span className="sr-prev-side">
        <TeamLogo espnId={game.home.espn_id} abbr={game.home.abbr} name={game.home.school} size={20} />
        {game.home.school}
      </span>
      <span className="sr-prev-tags">
        {TAG_LABEL[game.tag] && <span className={`sr-prev-tag ${game.tag}`}>{TAG_LABEL[game.tag]}</span>}
        {game.changed && <span className="sr-prev-tag changed">New</span>}
      </span>
    </div>
  );
}

export default function SchedulePreview({ preview, userTeam = null, defaultWeek = null }) {
  const weeks = preview?.weeks || [];
  const firstUserWeek = weeks.find((w) => w.games.some((g) => g.user))?.week;
  const [picked, setPicked] = useState(defaultWeek ?? firstUserWeek ?? weeks[0]?.week ?? null);
  if (!preview) return null;
  const shown = weeks.find((w) => w.week === picked) || weeks[0];
  return (
    <PanelCard title="Generated Season" right={`${preview.changed} of ${preview.total} games changed`}>
      {userTeam && (
        <div className="sr-prev-stats">
          <span className="sr-prev-stat">Your games are highlighted and always stay on <b>{userTeam.school}</b>'s own calendar weeks.</span>
        </div>
      )}
      <div className="sr-wk-tabs" role="tablist" aria-label="Season weeks">
        {weeks.map((w) => (
          <button
            key={w.week}
            type="button"
            className={`sr-wk-tab${shown && w.week === shown.week ? ' active' : ''}`}
            title={`Week ${w.week}: ${w.games.length} game${w.games.length === 1 ? '' : 's'}${w.locked ? ' (locked)' : ''}`}
            onClick={() => setPicked(w.week)}
          >
            {w.week}
            {w.games.some((g) => g.user) && <span className="sr-wk-dot" aria-label="your game" />}
          </button>
        ))}
      </div>
      {shown && (
        <>
          <div className="sr-wk-head">
            <span className="sr-wk-title">Week {shown.week}</span>
            {shown.locked && <span className="sr-prev-tag locked">Locked</span>}
            <span className="sr-prev-count">{shown.games.length} games</span>
          </div>
          {shown.games.map((g, i) => <GameRow key={i} game={g} />)}
        </>
      )}
    </PanelCard>
  );
}
