import EmptyState from '../ui/EmptyState.jsx';
import RecruitRow from './RecruitRow.jsx';

// Sortable national recruit table. The parent owns filtering + sorting and
// passes the already-prepared `recruits`; clicking a column header calls onSort.
const COLUMNS = [
  { key: 'national_rank', label: '#' },
  { key: 'name', label: 'Player' },
  { key: 'stars', label: 'Stars' },
  { key: 'ovr', label: 'OVR' },
  { key: 'expected_nil', label: 'NIL' },
  { key: 'status', label: 'Commit' },
];

export default function RecruitBoard({ recruits = [], sort = { key: 'national_rank', dir: 1 }, onSort, onSelect }) {
  return (
    <div className="recruit-board">
      <div className="rb-head">
        {COLUMNS.map((c) => (
          <button
            key={c.key}
            className={`rb-th${sort.key === c.key ? ' active' : ''}`}
            onClick={() => onSort?.(c.key)}
          >
            {c.label}{sort.key === c.key ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}
          </button>
        ))}
      </div>
      {recruits.length === 0 ? (
        <EmptyState>No recruits match these filters.</EmptyState>
      ) : (
        <div className="rb-body">
          {recruits.map((r) => <RecruitRow key={r.id} recruit={r} onSelect={onSelect} />)}
        </div>
      )}
    </div>
  );
}
