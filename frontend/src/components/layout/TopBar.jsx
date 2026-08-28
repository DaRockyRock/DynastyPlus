import TeamLogo from '../ui/TeamLogo.jsx';
import ConferenceLogo from '../ui/ConferenceLogo.jsx';
import Badge from '../ui/Badge.jsx';
import Button from '../ui/Button.jsx';
import HudChip from '../ui/HudChip.jsx';
import WeekNav from './WeekNav.jsx';
import LiveStatus from './LiveStatus.jsx';
import AutoSyncToggle from './AutoSyncToggle.jsx';
import PollBadge from '../ui/PollBadge.jsx';
import { PlayIcon, RefreshIcon } from '../ui/icons.jsx';
import { hexColor, teamAsset } from '../../lib/format.js';

// App top bar, styled as the game's frame header: the team's white mark and
// "TEAM (record)" wordmark at left, HUD chips (week, rankings) beside it, and
// the app actions at right.
//
// The week control depends on `mode`:
//   live (default) - passive LiveStatus readout; the watcher advances on its own.
//   demo           - manual WeekNav stepper + Advance Week button (UI testing).
export default function TopBar({
  team, season, week, mode = 'live', watcherActive = false,
  onPrevWeek, onAdvance, onSync, onScan, scanning = false, onExit,
  autosyncEnabled = true, onAutosyncChange, autosyncBusy = false,
}) {
  // The save ranks the ENTIRE field (a "rank" of 64 just means unranked); only
  // a true top-25 spot is a rank worth showing, everything else is NR.
  const asRank = (n) => (n && n >= 1 && n <= 25 ? `#${n}` : 'NR');
  const cfp = asRank(team.rankings?.cfp);
  const ap = asRank(team.rankings?.ap);
  const record = team.record?.overall;
  const coach = team.head_coach?.name;
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-logo">
          <TeamLogo
            espnId={team.espn_id}
            logo={team.logo_white || teamAsset(team.espn_id, 'logo-white') || team.logo}
            abbr={team.abbreviation}
            name={team.name}
            color={hexColor(team.color)}
            size={50}
            plate={false}
          />
        </span>
        <div className="topbar-team">
          {/* the game header shows the school, not the full team name */}
          <span className="name">{team.school || team.name}{record ? ` (${record})` : ''}</span>
          <span className="meta">
            {team.record?.conference && <>{team.record.conference}{' '}</>}
            {team.conference && (
              <>
                <ConferenceLogo name={team.conference} size={15} title={team.conference} variant="white" />
                {team.conference}
              </>
            )}
            {coach && <>{team.conference || team.record?.conference ? ', ' : ''}{coach}</>}
          </span>
        </div>
      </div>
      <div className="topbar-badges">
        <Badge variant="week">{season.week_label} {season.year}</Badge>
        <HudChip icon={<PollBadge poll="cfp" size={16} />} label="CFP" value={cfp} accent="var(--cfp)" />
        <HudChip icon={<PollBadge poll="ap" size={16} />} label="AP" value={ap} accent="var(--accent-gold)" />
      </div>
      <div className="topbar-spacer" />
      <div className="topbar-actions">
        {onAutosyncChange && (
          <AutoSyncToggle
            enabled={autosyncEnabled}
            onChange={onAutosyncChange}
            busy={autosyncBusy}
          />
        )}
        {mode === 'demo' ? (
          <>
            <WeekNav week={week} onPrev={onPrevWeek} onNext={onAdvance} />
            <Button variant="action" icon={<PlayIcon />} onClick={onAdvance}>Advance Week</Button>
          </>
        ) : onScan ? (
          <>
            <Button variant="action" icon={<RefreshIcon />} onClick={onScan} spinning={scanning} disabled={scanning}>
              {scanning ? 'Scanning...' : 'Scan'}
            </Button>
            {onExit && <Button variant="action" onClick={onExit}>Library</Button>}
          </>
        ) : (
          <LiveStatus active={watcherActive} onSync={onSync} />
        )}
      </div>
    </header>
  );
}
