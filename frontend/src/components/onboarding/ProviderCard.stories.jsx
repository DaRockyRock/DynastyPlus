import { useState } from 'react';
import ProviderCard from './ProviderCard.jsx';
import { CloudIcon, ServerIcon } from '../ui/icons.jsx';

export default {
  title: 'Onboarding/ProviderCard',
  component: ProviderCard,
  parameters: { layout: 'padded' },
};

export const Pair = {
  render: () => {
    const [sel, setSel] = useState('anthropic');
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, maxWidth: 720 }}>
        <ProviderCard
          icon={CloudIcon}
          title="Anthropic (Claude)"
          tagline="Use Claude's hosted API. Best quality, ready in a minute."
          bullets={['Paste an API key', 'Haiku, Sonnet, or Opus', 'Nothing to install']}
          badge="Recommended"
          selected={sel === 'anthropic'}
          onSelect={() => setSel('anthropic')}
        />
        <ProviderCard
          icon={ServerIcon}
          title="Local model"
          tagline="Run any model on your own machine - Ollama, LM Studio, and more."
          bullets={['Use any local model', 'Runs offline, no per-token cost', 'You run the server']}
          selected={sel === 'local'}
          onSelect={() => setSel('local')}
        />
      </div>
    );
  },
};
