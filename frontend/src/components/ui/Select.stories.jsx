import { useState } from 'react';
import Select from './Select.jsx';

const CONFERENCES = [
  { value: 'big-ten', label: 'Big Ten' },
  { value: 'sec', label: 'SEC' },
  { value: 'big-12', label: 'Big 12' },
];

export default {
  title: 'UI/Select',
  component: Select,
  parameters: { layout: 'padded' },
};

export const Conferences = {
  render: () => {
    const [value, setValue] = useState('big-ten');
    return <div style={{ maxWidth: 360 }}><Select options={CONFERENCES} value={value} onValueChange={setValue} /></div>;
  },
};
