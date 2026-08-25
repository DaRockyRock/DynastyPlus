// Recruitment funnel stage pill. Color ramps from cool (Open) to team-hot
// (Hard Commit) so the board reads at a glance.
const SLUG = {
  'Open': 'open',
  'Top 5': 'top5',
  'Top 3': 'top3',
  'Verbal': 'verbal',
  'Hard Commit': 'commit',
};

export default function StageTag({ stage }) {
  const slug = SLUG[stage] || 'open';
  return <span className={`stage-tag ${slug}`}>{stage || 'Open'}</span>;
}
