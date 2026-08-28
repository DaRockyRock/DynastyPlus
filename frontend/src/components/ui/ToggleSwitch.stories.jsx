import { useState } from 'react';
import ToggleSwitch from './ToggleSwitch.jsx';

export default {
  title: 'UI/ToggleSwitch',
  component: ToggleSwitch,
};

function Demo({ initial = true, label }) {
  const [checked, setChecked] = useState(initial);
  return <ToggleSwitch checked={checked} onChange={setChecked} label={label} />;
}

export const On = { render: () => <Demo initial label="Notre Dame access rule" /> };
export const Off = { render: () => <Demo initial={false} label="Rivalry week losses disqualify" /> };
export const Bare = { render: () => <Demo initial /> };
