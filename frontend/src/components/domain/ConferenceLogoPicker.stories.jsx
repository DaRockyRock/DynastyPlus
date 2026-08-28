import { useState } from 'react';
import ConferenceLogoPicker from './ConferenceLogoPicker.jsx';
import { historicConferenceLogos } from '../fixtures.js';

export default {
  title: 'Domain/ConferenceLogoPicker',
  component: ConferenceLogoPicker,
  parameters: { layout: 'padded' },
};

const logos = historicConferenceLogos.SEC;

export const Default = {
  render: () => {
    const [value, setValue] = useState('');
    return (
      <div style={{ width: 560 }}>
        <ConferenceLogoPicker logos={logos} value={value} onSelect={setValue} />
      </div>
    );
  },
};

export const WithSelection = {
  render: () => {
    const [value, setValue] = useState(logos[4].url);
    return (
      <div style={{ width: 560 }}>
        <ConferenceLogoPicker logos={logos} value={value} onSelect={setValue} />
      </div>
    );
  },
};
