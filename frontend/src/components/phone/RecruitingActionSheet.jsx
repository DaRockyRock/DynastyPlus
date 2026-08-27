// Bottom sheet listing the weekly recruiting actions ("Send the House" and the
// rest) with their hour costs. Actions you cannot afford this week are disabled.
export default function RecruitingActionSheet({ actions = [], hoursRemaining = 0, onPick, onClose }) {
  return (
    <div className="phone-sheet">
      <div className="ps-handle" />
      <div className="ps-title">Recruiting Actions</div>
      <div className="ps-sub">{hoursRemaining} hours left this week</div>
      <div className="action-list">
        {actions.map((a) => {
          const afford = hoursRemaining >= a.hours;
          return (
            <button
              key={a.key}
              className={`action-item${afford ? '' : ' disabled'}`}
              disabled={!afford}
              onClick={() => onPick?.(a.key)}
            >
              <span className="ai-main">
                <b>{a.label}</b>
                <span className="ai-blurb">{a.blurb}</span>
              </span>
              <span className="ai-meta">
                <span className="ai-hours">{a.hours} hrs</span>
                <span className="ai-inf">+{a.influence}</span>
              </span>
            </button>
          );
        })}
      </div>
      <div className="ps-actions">
        <button className="ps-btn" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
