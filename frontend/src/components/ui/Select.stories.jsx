import { useState } from 'react';
import Select from './Select.jsx';

const SEASONS = [
  { value: '2026', label: '2026 season' },
  { value: '2027', label: '2027 season' },
  { value: '2028', label: '2028 season' },
];

export default {
  title: 'UI/Select',
  component: Select,
  parameters: { layout: 'padded' },
};

export const Seasons = {
  render: () => {
    const [v, setV] = useState('2026');
    return <div style={{ maxWidth: 360 }}><Select options={SEASONS} value={v} onValueChange={setV} /></div>;
  },
};
