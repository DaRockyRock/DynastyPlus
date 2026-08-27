import ConferenceLogo from './ConferenceLogo.jsx';

// A team stat with its national rank (badge, top-right) and conference rank
// (with the conference logo, below). `label` is the full stat name; `unit`
// (ppg/ypg) stays abbreviated.
export default function StatCard({ label, value, unit, nationalRank, confRank, conference }) {
  return (
    <div className="stat-card">
      <div className="sc-top">
        <span className="sc-label">{label}</span>
        {nationalRank != null && (
          <span className="sc-natrank">
            <span className="srk">#{nationalRank}</span>
            <span className="srk-tag">National</span>
          </span>
        )}
      </div>
      <div className="sc-value">{value}{unit && <small>{unit}</small>}</div>
      {confRank != null && (
        <div className="sc-confrank">
          <ConferenceLogo name={conference} size={15} title={conference} />
          <span>#{confRank}{conference ? ` in the ${conference}` : ''}</span>
        </div>
      )}
    </div>
  );
}
