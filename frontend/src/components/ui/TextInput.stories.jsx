import { useState } from 'react';
import TextInput from './TextInput.jsx';

export default {
  title: 'UI/TextInput',
  component: TextInput,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState('');
    return <div style={{ maxWidth: 360 }}><TextInput placeholder="http://127.0.0.1:8787" value={v} onValueChange={setV} /></div>;
  },
};
