import { useState } from 'react';
import PasswordInput from './PasswordInput.jsx';

export default {
  title: 'UI/PasswordInput',
  component: PasswordInput,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => {
    const [v, setV] = useState('example-key-not-real');
    return <div style={{ maxWidth: 360 }}><PasswordInput value={v} onValueChange={setV} placeholder="sk-ant-..." /></div>;
  },
};

export const Empty = {
  render: () => {
    const [v, setV] = useState('');
    return <div style={{ maxWidth: 360 }}><PasswordInput value={v} onValueChange={setV} placeholder="sk-ant-..." /></div>;
  },
};
