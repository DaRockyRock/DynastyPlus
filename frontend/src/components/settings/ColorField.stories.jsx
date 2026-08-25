import { useState } from 'react';
import ColorField from './ColorField.jsx';

export default {
  title: 'Settings/ColorField',
  component: ColorField,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState('e41c38');
    return <div style={{ maxWidth: 280 }}><ColorField value={v} onChange={setV} /></div>;
  },
};
