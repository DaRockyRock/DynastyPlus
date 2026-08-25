import { useState } from 'react';
import SettingsNav from './SettingsNav.jsx';
import { settingsSchema } from '../fixtures.js';

export default {
  title: 'Settings/SettingsNav',
  component: SettingsNav,
  parameters: { layout: 'fullscreen' },
};

export const Default = {
  render: () => {
    const [active, setActive] = useState('head_coach');
    return (
      <div style={{ width: 280, height: 520, background: 'var(--field-0)' }}>
        <SettingsNav
          schema={settingsSchema}
          active={active}
          onSelect={setActive}
          counts={{ players: 8, reporters: 6, cfp_committee: 12 }}
          modified={new Set(['head_coach', 'reporters'])}
        />
      </div>
    );
  },
};
