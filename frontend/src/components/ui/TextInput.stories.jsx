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
    return <div style={{ maxWidth: 360 }}><TextInput placeholder="Search recruits" value={v} onValueChange={setV} /></div>;
  },
};
