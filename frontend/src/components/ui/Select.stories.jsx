import { useState } from 'react';
import Select from './Select.jsx';

const MODELS = [
  { value: 'claude-haiku-4-5', label: 'Claude Haiku 4.5 - fastest, cheapest' },
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 - balanced' },
  { value: 'claude-opus-4-8', label: 'Claude Opus 4.8 - most capable' },
];

export default {
  title: 'UI/Select',
  component: Select,
  parameters: { layout: 'padded' },
};

export const Models = {
  render: () => {
    const [v, setV] = useState('claude-haiku-4-5');
    return <div style={{ maxWidth: 360 }}><Select options={MODELS} value={v} onValueChange={setV} /></div>;
  },
};
