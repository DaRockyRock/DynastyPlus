import { useState } from 'react';
import ProviderPicker from './ProviderPicker.jsx';

export default {
  title: 'Onboarding/ProviderPicker',
  component: ProviderPicker,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState('anthropic');
    return <div style={{ maxWidth: 760 }}><ProviderPicker value={v} onChange={setV} /></div>;
  },
};
