import { useState } from 'react';
import FieldGrid from './FieldGrid.jsx';
import { settingsObjectSection, settingsObjectValue } from '../fixtures.js';

export default {
  title: 'Settings/FieldGrid',
  component: FieldGrid,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState(settingsObjectValue);
    return <div style={{ maxWidth: 720 }}><FieldGrid fields={settingsObjectSection.fields} value={v} onChange={setV} /></div>;
  },
};
