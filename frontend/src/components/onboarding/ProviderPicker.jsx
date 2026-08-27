import ProviderCard from './ProviderCard.jsx';
import { CloudIcon, ServerIcon } from '../ui/icons.jsx';

// The connection-type chooser: external Anthropic vs a local Anthropic-compatible
// server. `value` is 'anthropic' | 'local'; `onChange` receives the new value.
export default function ProviderPicker({ value = 'anthropic', onChange }) {
  return (
    <div className="provider-picker">
      <ProviderCard
        icon={CloudIcon}
        title="Anthropic (Claude)"
        tagline="Use Claude's hosted API. Best quality, ready in about a minute."
        bullets={['Paste an API key', 'Haiku, Sonnet, or Opus', 'Nothing to install']}
        badge="Recommended"
        selected={value === 'anthropic'}
        onSelect={() => onChange?.('anthropic')}
      />
      <ProviderCard
        icon={ServerIcon}
        title="Local model"
        tagline="Run any model on your own machine - Ollama, LM Studio, and more."
        bullets={['Use any local model', 'Runs offline, no per-token cost', 'You run the server']}
        selected={value === 'local'}
        onSelect={() => onChange?.('local')}
      />
    </div>
  );
}
