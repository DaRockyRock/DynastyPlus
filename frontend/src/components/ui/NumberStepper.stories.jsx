import { useState } from 'react';
import NumberStepper from './NumberStepper.jsx';

export default {
  title: 'UI/NumberStepper',
  component: NumberStepper,
};

function Demo({ initial = 12, ...props }) {
  const [value, setValue] = useState(initial);
  return <NumberStepper value={value} onChange={setValue} {...props} />;
}

export const Default = { render: () => <Demo min={1} max={128} /> };
export const WithSuffix = { render: () => <Demo initial={4} min={0} max={64} suffix="teams" /> };
export const AtMinimum = { render: () => <Demo initial={1} min={1} max={128} /> };
