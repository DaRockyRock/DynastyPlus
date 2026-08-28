import TeamLogo from '../ui/TeamLogo.jsx';
import PollBadge from '../ui/PollBadge.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import EmptyState from '../ui/EmptyState.jsx';
import ResumeGameRow from './ResumeGameRow.jsx';
import ResumeSummaryGrid from './ResumeSummaryGrid.jsx';
import { hexColor } from '../../lib/format.js';

// A team's full playoff resume: identity header over the team's color field,
// the season-summary tiles, signature wins and losses, the complete game log
// (opponents with their current ranks and records), and the games still to
// play. `resume` is the /api/rankings/resume payload.
export default function TeamResumePanel({ resume }) {
  if (!resume?.available) {
    return <EmptyState>{resume?.reason || 'No resume is available for this team yet.'}</EmptyState>;
  }
  const t = resume.team;
  const s = resume.summary || {};
  const games = resume.games || [];
  const streakTone = s.streak?.startsWith('W') ? 'win' : (s.streak?.startsWith('L') ? 'loss' : null);
  return (
    <div className="team-resume" style={{ '--tr-team': hexColor(t.color, 'var(--team)') }}>
      <header className="tr-head">
        <TeamLogo espnId={t.espn_id} logo={t.logo} abbr={t.abbr} name={t.school} size={72} />
        <div className="tr-title">
          <h2 className="tr-school">{t.school}</h2>
          <span className="tr-nick">
            {t.team && t.school && t.team.startsWith(t.school) ? t.team.slice(t.school.length).trim() : t.team}
            {t.conference ? `, ${t.conference}` : ''}
          </span>
        </div>
        <div className="tr-badges">
          <span className="tr-poll-chip">
            <PollBadge poll="cfp" size={22} />
            <span>{t.cfp_rank ? `#${t.cfp_rank}` : 'NR'}</span>
          </span>
          <span className="tr-poll-chip">
            <PollBadge poll="ap" size={22} />
            <span>{t.ap_rank ? `#${t.ap_rank}` : 'NR'}</span>
          </span>
          <span className="tr-record">{t.record}</span>
          {t.conf_record && t.conf_record !== '0-0' && <span className="tr-confrec">{t.conf_record} conf</span>}
          {s.streak && <span className={`tr-streak tone-${streakTone}`}>{s.streak}</span>}
        </div>
      </header>

      <ResumeSummaryGrid summary={s} />

      <div className="tr-quality">
        <div className="tr-quality-col">
          <SectionTitle>Signature Wins</SectionTitle>
          {resume.best_wins?.length
            ? resume.best_wins.map((g, i) => <ResumeGameRow key={`bw-${i}`} game={g} compact />)
            : <p className="tr-none">No wins yet.</p>}
        </div>
        <div className="tr-quality-col">
          <SectionTitle>Losses</SectionTitle>
          {resume.worst_losses?.length
            ? resume.worst_losses.map((g, i) => <ResumeGameRow key={`wl-${i}`} game={g} compact />)
            : <p className="tr-none">Undefeated.</p>}
        </div>
      </div>

      <div className="tr-log">
        <SectionTitle>Season Results<span className="sb-count">{games.length}</span></SectionTitle>
        {games.length
          ? games.map((g) => <ResumeGameRow key={`g-${g.n}`} game={g} />)
          : <p className="tr-none">No official results yet this season.</p>}
      </div>

      {resume.upcoming?.length > 0 && (
        <div className="tr-upcoming">
          <SectionTitle>Still To Play<span className="sb-count">{resume.upcoming.length}</span></SectionTitle>
          <div className="tr-upcoming-list">
            {resume.upcoming.map((g, i) => <ResumeGameRow key={`u-${i}`} game={g} />)}
          </div>
        </div>
      )}
    </div>
  );
}
