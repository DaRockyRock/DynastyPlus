import { useState } from 'react';
import TeamField from './TeamField.jsx';

export default {
  title: 'Settings/TeamField',
  component: TeamField,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState('Nebraska Cornhuskers');
    return <div style={{ maxWidth: 360 }}><TeamField value={v} onChange={setV} /></div>;
  },
};
