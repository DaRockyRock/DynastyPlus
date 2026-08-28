import RankCard from './RankCard.jsx';
import EmptyState from '../ui/EmptyState.jsx';

// The rankings hub's card grid. `entries` is a full poll ordering; `max`
// trims the visible head (the caller owns the top-25 / full-field toggle).
// The user's program is highlighted and `comparedRows` marks the teams pinned
// for comparison.
export default function RankCardGrid({
  entries = [], userTeam, max, comparedRows = [], onOpen, onCompare,
}) {
  const rows = max ? entries.slice(0, max) : entries;
  if (!rows.length) {
    return <EmptyState>No ranked teams yet. Scan a dynasty first.</EmptyState>;
  }
  return (
    <div className="rank-card-grid">
      {rows.map((e) => (
        <RankCard
          key={`${e.row}-${e.rank}`}
          entry={e}
          isUser={e.team === userTeam}
          compared={comparedRows.includes(e.row)}
          onOpen={onOpen}
          onCompare={onCompare}
        />
      ))}
    </div>
  );
}
