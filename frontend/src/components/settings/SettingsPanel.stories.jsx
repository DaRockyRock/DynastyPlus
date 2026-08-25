import { useState } from 'react';
import SettingsPanel from './SettingsPanel.jsx';
import ObjectForm from './ObjectForm.jsx';
import { settingsObjectSection, settingsObjectValue } from '../fixtures.js';

export default {
  title: 'Settings/SettingsPanel',
  component: SettingsPanel,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState(settingsObjectValue);
    const [dirty, setDirty] = useState(false);
    return (
      <SettingsPanel
        section={settingsObjectSection}
        dirty={dirty}
        saving={false}
        onSave={() => setDirty(false)}
        onReset={() => setDirty(false)}
      >
        <ObjectForm section={settingsObjectSection} value={v} onChange={(nv) => { setV(nv); setDirty(true); }} />
      </SettingsPanel>
    );
  },
};
