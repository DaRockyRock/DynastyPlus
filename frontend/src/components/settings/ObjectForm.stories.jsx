import { useState } from 'react';
import ObjectForm from './ObjectForm.jsx';
import { settingsObjectSection, settingsObjectValue } from '../fixtures.js';

export default {
  title: 'Settings/ObjectForm',
  component: ObjectForm,
  parameters: { layout: 'padded' },
};

export const HeadCoach = {
  render: () => {
    const [v, setV] = useState(settingsObjectValue);
    return <div style={{ maxWidth: 760 }}><ObjectForm section={settingsObjectSection} value={v} onChange={setV} /></div>;
  },
};
