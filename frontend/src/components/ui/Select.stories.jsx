import { useState } from 'react';
import Select from './Select.jsx';

const CONFERENCES = [
  { value: 'big-ten', label: 'Big Ten' },
  { value: 'big-12', label: 'Big 12' },
  { value: 'sec', label: 'SEC' },
];

export default {
  title: 'UI/Select',
  component: Select,
  parameters: { layout: 'padded' },
};

export const Conferences = {
  render: () => {
    const [v, setV] = useState('big-ten');
    return <div style={{ maxWidth: 360 }}><Select options={CONFERENCES} value={v} onValueChange={setV} /></div>;
  },
};
