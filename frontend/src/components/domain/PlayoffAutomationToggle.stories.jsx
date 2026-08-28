import { useState } from 'react';
import PlayoffAutomationToggle from './PlayoffAutomationToggle.jsx';

export default {
  title: 'Domain/PlayoffAutomationToggle',
  component: PlayoffAutomationToggle,
};

export const Off = {
  args: { enabled: false },
};

export const On = {
  args: { enabled: true },
};

export const Interactive = {
  render: () => {
    const [enabled, setEnabled] = useState(false);
    return <PlayoffAutomationToggle enabled={enabled} onChange={setEnabled} />;
  },
};
