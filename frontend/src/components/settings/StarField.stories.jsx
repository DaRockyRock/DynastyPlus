import { useState } from 'react';
import StarField from './StarField.jsx';

export default {
  title: 'Settings/StarField',
  component: StarField,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState(4);
    return <StarField value={v} onChange={setV} />;
  },
};

export const Empty = {
  render: () => {
    const [v, setV] = useState(0);
    return <StarField value={v} onChange={setV} />;
  },
};
