import TeamLogo from '../ui/TeamLogo.jsx';
import ConferenceLogo from '../ui/ConferenceLogo.jsx';
import Badge from '../ui/Badge.jsx';
import Button from '../ui/Button.jsx';
import WeekNav from './WeekNav.jsx';
import LiveStatus from './LiveStatus.jsx';
import LLMStatusPill from './LLMStatusPill.jsx';
import SimStatusBadge from './SimStatusBadge.jsx';
import PendingActionsBadge from './PendingActionsBadge.jsx';
import PhoneButton from './PhoneButton.jsx';
import { PlayIcon, RefreshIcon } from '../ui/icons.jsx';
import { hexColor } from '../../lib/format.js';

// App top bar: team logo, record, week/season/ranking badges, the week control,
// and the phone action.
//
// The week control depends on `mode`:
//   live (default) - passive LiveStatus readout; the watcher advances on its own.
//   demo           - manual WeekNav stepper + Advance Week button (UI testing).
export default function TopBar({
  team, season, week, mode = 'live', watcherActive = false, sim = null, onSimClick,
  onPrevWeek, onAdvance, onSync, onPhone, phoneUnread = 0, llm, onLLMClick,
  pending = 0, onPendingClick, onScan, scanning = false, onExit,
}) {
  const cfp = team.rankings?.cfp ? `#${team.rankings.cfp}` : 'NR';
  const ap = team.rankings?.ap ? `#${team.rankings.ap}` : 'NR';
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-logo">
          <TeamLogo espnId={team.espn_id} logo={team.logo} abbr={team.abbreviation} name={team.name} color={hexColor(team.color)} size={50} plate={false} />
        </span>
        <div className="topbar-team">
          <span className="name">{team.name}</span>
          <span className="meta">
            <span className="topbar-record">{team.record.overall}</span> ({team.record.conference}{' '}
            <ConferenceLogo name={team.conference} size={15} title={team.conference} />{team.conference}) - {team.head_coach.name}
          </span>
        </div>
      </div>
      <div className="topbar-badges">
        <Badge variant="week">{season.week_label}</Badge>
        <Badge label={String(season.year)} />
        <Badge variant="rank-cfp" label="CFP" value={cfp} />
        <Badge variant="rank-ap" label="AP" value={ap} />
      </div>
      <div className="topbar-spacer" />
      <div className="topbar-actions">
        {sim?.active && <SimStatusBadge week={sim.week} onClick={onSimClick} />}
        {onLLMClick && <LLMStatusPill status={llm} onClick={onLLMClick} />}
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
        <PendingActionsBadge count={pending} onClick={onPendingClick} />
        <PhoneButton count={phoneUnread} onClick={onPhone} />
      </div>
    </header>
  );
}
