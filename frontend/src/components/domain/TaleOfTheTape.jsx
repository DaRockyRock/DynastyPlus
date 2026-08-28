import TeamLogo from '../ui/TeamLogo.jsx';
import PollBadge from '../ui/PollBadge.jsx';
import SectionTitle from '../ui/SectionTitle.jsx';
import ResumeGameRow from './ResumeGameRow.jsx';
import { hexColor } from '../../lib/format.js';

// The playoff-decision comparison: two resumes side by side, stat by stat,
// with the leading side lit in its team color, and each team's signature
// wins underneath. `a` and `b` are /api/rankings/resume payloads.
const pct = (rec) => {
  const [w, l] = String(rec || '0-0').split('-').map(Number);
  return (w + l) ? w / (w + l) : -1;
};

// Each row: label, reader, and a comparator that returns 'a' | 'b' | null.
const ROWS = [
  { label: 'Record', get: (r) => r.team.record, cmp: (x, y) => pct(x) - pct(y) },
  { label: 'vs CFP Top 25', get: (r) => r.summary.vs_top25, cmp: (x, y) => pct(x) - pct(y) },
  { label: 'Conference', get: (r) => r.team.conf_record, cmp: (x, y) => pct(x) - pct(y) },
  { label: 'Points per game', get: (r) => r.summary.ppg, cmp: (x, y) => x - y },
  { label: 'Points allowed', get: (r) => r.summary.papg, cmp: (x, y) => y - x },
  {
    label: 'Average margin',
    get: (r) => (r.summary.avg_margin > 0 ? `+${r.summary.avg_margin}` : r.summary.avg_margin),
    cmp: (x, y) => parseFloat(x) - parseFloat(y),
  },
  { label: 'Away', get: (r) => r.summary.away, cmp: (x, y) => pct(x) - pct(y) },
  { label: 'Streak', get: (r) => r.summary.streak || 'None', cmp: () => 0 },
];

function TeamHead({ resume, side }) {
  const t = resume.team;
  return (
    <div className={`tott-team tott-${side}`} style={{ '--tt-team': hexColor(t.color, 'var(--team)') }}>
      <TeamLogo espnId={t.espn_id} logo={t.logo} abbr={t.abbr} name={t.school} size={54} />
      <div className="tott-team-id">
        <span className="tott-school">{t.school}</span>
        <span className="tott-ranks">
          <span className="tr-poll-chip"><PollBadge poll="cfp" size={16} />{t.cfp_rank ? `#${t.cfp_rank}` : 'NR'}</span>
          <span className="tr-poll-chip"><PollBadge poll="ap" size={16} />{t.ap_rank ? `#${t.ap_rank}` : 'NR'}</span>
        </span>
      </div>
    </div>
  );
}

export default function TaleOfTheTape({ a, b }) {
  if (!a?.available || !b?.available) return null;
  return (
    <div className="tale-of-the-tape">
      <div className="tott-heads">
        <TeamHead resume={a} side="a" />
        <span className="tott-vs">VS</span>
        <TeamHead resume={b} side="b" />
      </div>
      <div className="tott-rows"
           style={{ '--tt-a': hexColor(a.team.color, 'var(--team)'), '--tt-b': hexColor(b.team.color, 'var(--team)') }}>
        {ROWS.map((row) => {
          const va = row.get(a);
          const vb = row.get(b);
          const d = row.cmp(va, vb);
          return (
            <div key={row.label} className="tott-row">
              <span className={['tott-val', 'side-a', d > 0 ? 'lead' : ''].filter(Boolean).join(' ')}>{va}</span>
              <span className="tott-label">{row.label}</span>
              <span className={['tott-val', 'side-b', d < 0 ? 'lead' : ''].filter(Boolean).join(' ')}>{vb}</span>
            </div>
          );
        })}
      </div>
      <div className="tott-wins">
        <div className="tott-wins-col">
          <SectionTitle>Signature Wins</SectionTitle>
          {a.best_wins?.length
            ? a.best_wins.map((g, i) => <ResumeGameRow key={`a-${i}`} game={g} compact />)
            : <p className="tr-none">No wins yet.</p>}
        </div>
        <div className="tott-wins-col">
          <SectionTitle>Signature Wins</SectionTitle>
          {b.best_wins?.length
            ? b.best_wins.map((g, i) => <ResumeGameRow key={`b-${i}`} game={g} compact />)
            : <p className="tr-none">No wins yet.</p>}
        </div>
      </div>
      <div className="tott-wins">
        <div className="tott-wins-col">
          <SectionTitle>Losses</SectionTitle>
          {a.worst_losses?.length
            ? a.worst_losses.map((g, i) => <ResumeGameRow key={`al-${i}`} game={g} compact />)
            : <p className="tr-none">Undefeated.</p>}
        </div>
        <div className="tott-wins-col">
          <SectionTitle>Losses</SectionTitle>
          {b.worst_losses?.length
            ? b.worst_losses.map((g, i) => <ResumeGameRow key={`bl-${i}`} game={g} compact />)
            : <p className="tr-none">Undefeated.</p>}
        </div>
      </div>
    </div>
  );
}
