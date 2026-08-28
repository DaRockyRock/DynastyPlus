// The resume's season-summary tiles: scoring, margin, and the split records
// the committee argues about. `summary` is /api/rankings/resume `summary`.
function Tile({ label, value, tone }) {
  return (
    <div className={['resume-tile', tone ? `tone-${tone}` : ''].filter(Boolean).join(' ')}>
      <span className="rt-value">{value}</span>
      <span className="rt-label">{label}</span>
    </div>
  );
}

export default function ResumeSummaryGrid({ summary = {} }) {
  const margin = summary.avg_margin;
  const marginTone = margin > 0 ? 'win' : (margin < 0 ? 'loss' : null);
  return (
    <div className="resume-summary-grid">
      <Tile label="Points per game" value={summary.ppg ?? '0.0'} />
      <Tile label="Points allowed" value={summary.papg ?? '0.0'} />
      <Tile
        label="Average margin"
        value={margin > 0 ? `+${margin}` : `${margin ?? '0.0'}`}
        tone={marginTone}
      />
      <Tile label="vs CFP Top 25" value={summary.vs_top25 || '0-0'} />
      <Tile label="Home" value={summary.home || '0-0'} />
      <Tile label="Away" value={summary.away || '0-0'} />
    </div>
  );
}
