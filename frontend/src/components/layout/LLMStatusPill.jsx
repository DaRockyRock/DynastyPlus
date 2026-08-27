import StatusDot from '../ui/StatusDot.jsx';

// Compact broadcast readout of the active model connection, shown in the top bar.
// Click to reopen the setup wizard. Green when generating live, amber when on
// mock content.
//
//   status - the /api/llm payload ({ ready, provider, model, ... })
const SHORT = {
  'claude-haiku-4-5': 'Claude Haiku',
  'claude-sonnet-4-6': 'Claude Sonnet',
  'claude-opus-4-8': 'Claude Opus',
};

function label(status) {
  if (!status || !status.ready) return 'Mock content';
  const model = status.model || '';
  const name = SHORT[model] || model || 'Connected';
  return status.provider === 'local' ? `Local - ${name}` : name;
}

export default function LLMStatusPill({ status, onClick }) {
  const ready = !!status?.ready;
  return (
    <button
      type="button"
      className={`llm-pill${ready ? ' live' : ''}`}
      onClick={onClick}
      title={ready ? 'AI connected - click to change' : 'Connect an AI model'}
    >
      <StatusDot tone={ready ? 'live' : 'idle'} pulse={ready} />
      <span className="llm-pill-label">{label(status)}</span>
    </button>
  );
}
