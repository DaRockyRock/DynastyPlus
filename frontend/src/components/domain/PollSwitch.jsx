import PollBadge from '../ui/PollBadge.jsx';

// The rankings hub's poll selector: one branded tab per poll the save
// carries, using the real poll marks instead of generic icons.
export default function PollSwitch({ value, onChange, polls = ['cfp', 'ap'], labels = {} }) {
  return (
    <div className="poll-switch" role="tablist">
      {polls.map((p) => (
        <button
          key={p}
          type="button"
          role="tab"
          aria-selected={value === p}
          className={['poll-switch-tab', value === p ? 'active' : ''].filter(Boolean).join(' ')}
          onClick={() => onChange?.(p)}
        >
          <PollBadge poll={p} size={30} />
          <span className="poll-switch-label">{labels[p] || p.toUpperCase()}</span>
        </button>
      ))}
    </div>
  );
}
