import { useState } from 'react';
import ConnectionForm from './ConnectionForm.jsx';

const MODELS = [
  { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5 - fastest, cheapest' },
  { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 - balanced' },
  { id: 'claude-opus-4-8', label: 'Claude Opus 4.8 - most capable' },
];

export default {
  title: 'Onboarding/ConnectionForm',
  parameters: { layout: 'padded' },
};

export const Anthropic = {
  render: () => {
    const [v, setV] = useState({ model: 'claude-haiku-4-5', apiKey: '', baseUrl: '' });
    return (
      <div style={{ maxWidth: 760 }}>
        <ConnectionForm provider="anthropic" value={v} models={MODELS}
          onField={(k, val) => setV((s) => ({ ...s, [k]: val }))} />
      </div>
    );
  },
};

export const Local = {
  render: () => {
    const [v, setV] = useState({ model: 'llama3.1', apiKey: '', baseUrl: 'http://localhost:11434/v1' });
    return (
      <div style={{ maxWidth: 760 }}>
        <ConnectionForm provider="local" value={v}
          onField={(k, val) => setV((s) => ({ ...s, [k]: val }))} />
      </div>
    );
  },
};
